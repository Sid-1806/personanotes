"""Generation, refinement, question answering and retrieval against Gemini.

Every entry point here is synchronous and blocking; routers call them through
``run_in_threadpool`` (or consume the streaming generators on a worker thread)
so the event loop stays free.

Retrieval always filters by ``user_id``. Scope narrowing (lecture / course /
note) is layered on top of that, never instead of it.
"""

import json
import logging
import re

import google.generativeai as genai

from app.core.config import settings
from app.services.embedding_service import model as embedding_model
from app.services.vector_db import KIND_LECTURE, build_filter
from app.services.vector_db import client as qdrant_client
from app.style.prompt_format import summarize_style_for_prompt

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

generation_model = genai.GenerativeModel(settings.GEMINI_MODEL)

NO_KEY_MESSAGE = "Error: GEMINI_API_KEY is not configured in the backend."


def describe_llm_error(exc: Exception) -> str:
    """Turn a provider exception into something the user can act on.

    An upstream quota error is the one case where "please retry" is actively
    wrong advice — retrying immediately fails again. Say what happened and,
    when the provider tells us, how long to wait.
    """
    text = str(exc)
    lowered = text.lower()

    if "quota" in lowered or "429" in text or "rate limit" in lowered:
        seconds = None
        match = re.search(r"retry in ([\d.]+)s", lowered) or re.search(
            r"seconds: (\d+)", lowered
        )
        if match:
            seconds = int(float(match.group(1)))
        wait = f" Try again in about {seconds}s." if seconds else " Try again shortly."
        if "free_tier" in lowered or "free tier" in lowered:
            return (
                "The AI provider's free-tier quota is used up for now." + wait
            )
        return "The AI provider is rate-limiting requests." + wait

    # Google retires model names and stops serving them to new keys. The text
    # varies ("not found", "no longer available", "is not supported"), so match
    # on the subject rather than one phrasing.
    if "model" in lowered and (
        "not found" in lowered
        or "no longer available" in lowered
        or "not supported" in lowered
        or "404" in text
    ):
        return (
            "The configured AI model is unavailable. Set GEMINI_MODEL in the "
            "backend environment to a current model."
        )
    if "api key" in lowered or "permission" in lowered or "401" in text:
        return "The AI provider rejected the backend's API key."

    return "The AI service failed partway through. Please retry."

# How much context each scope deserves. A whole-course question needs more
# material than a single-paragraph follow-up, so top-k scales with scope rather
# than sitting at a hardcoded 5 for everything.
TOP_K_BY_SCOPE = {
    "note": 4,
    "lecture": 6,
    "course": 10,
    "all": 12,
}

# Generation presets. A blank "what should the notes cover?" box is a cold
# start; these give the user a running jump and map onto note_type.
NOTE_TYPE_INSTRUCTIONS = {
    "full": (
        "Write complete, well-structured lecture notes covering the material in depth. "
        "Include definitions, mechanisms, worked examples and caveats."
    ),
    "summary": (
        "Write a concise summary. Lead with the three or four ideas that matter most, "
        "then support each in a few lines. Prefer brevity over completeness."
    ),
    "key_concepts": (
        "Extract the key concepts as a glossary-style list. For each: the term, a one- "
        "or two-sentence definition, and why it matters. No narrative prose."
    ),
    "practice": (
        "Write practice questions that test understanding of this material. Mix recall, "
        "application and reasoning. Put every answer in a collapsed section at the end "
        "under a '## Answers' heading, numbered to match the questions."
    ),
    "cheatsheet": (
        "Write a dense one-page cheat sheet: formulas, definitions, comparison tables "
        "and rules of thumb. Maximum signal per line. Minimal prose."
    ),
    "custom": "",
}

DEFAULT_PROMPT_BY_TYPE = {
    "full": "Write complete notes on this material.",
    "summary": "Summarise the key points of this material.",
    "key_concepts": "List and define the key concepts in this material.",
    "practice": "Write practice questions covering this material.",
    "cheatsheet": "Build a cheat sheet for this material.",
}

_BASE_INSTRUCTION = (
    "You are an expert AI tutor and note-generator. "
    "Use the provided lecture excerpts to answer the user's prompt. "
    "You MUST strictly adhere to the user's Personalization Style Profile provided below. "
    "Format the output exactly according to their stylistic preferences (headings, bullet types, tone, etc.). "
    "When a concept involves a process, flow, hierarchy, sequence, or relationship, include a "
    "diagram as a Mermaid code block (```mermaid ... ```); use diagrams more when the user's "
    "diagram_frequency preference is high, and keep the Mermaid syntax valid. "
    "Use GitHub-flavoured markdown tables for comparisons, and LaTeX ($inline$ / $$display$$) "
    "for mathematical notation. "
    "If the lecture excerpts do not contain the answer, you may use your general knowledge, "
    "but prioritize the provided context."
)


# --------------------------------------------------------------------------
# Retrieval
# --------------------------------------------------------------------------


def search_chunks(
    query: str,
    user_id: int,
    limit: int = 5,
    lecture_id: int | None = None,
    course_id: int | None = None,
    note_id: int | None = None,
    kind: str | None = None,
    raise_on_error: bool = False,
) -> list[dict]:
    """Embed the query and return the most relevant chunks for this user.

    Always filtered by ``user_id`` (tenant isolation). Optionally narrowed to a
    lecture, a course, or one note. Returns payloads plus scores so callers can
    report grounding and show real citations.

    Generation swallows failures so a vector-store outage degrades to ungrounded
    output rather than a 500. Search passes ``raise_on_error`` because it has to
    tell "nothing matched" apart from "the index is down" — reporting an empty
    result as an outage would be a lie, and vice versa.
    """
    try:
        query_vector = embedding_model.encode([query], convert_to_numpy=True).tolist()[0]

        results = qdrant_client.query_points(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query=query_vector,
            query_filter=build_filter(
                user_id=user_id,
                lecture_id=lecture_id,
                course_id=course_id,
                note_id=note_id,
                kind=kind,
            ),
            limit=limit,
        ).points

        return [
            {
                "text": hit.payload.get("text", ""),
                "lecture_id": hit.payload.get("lecture_id"),
                "note_id": hit.payload.get("note_id"),
                "course_id": hit.payload.get("course_id"),
                "page": hit.payload.get("page"),
                "kind": hit.payload.get("kind", KIND_LECTURE),
                "score": round(float(hit.score), 4) if hit.score is not None else None,
            }
            for hit in results
            if hit.payload
        ]
    except Exception as e:
        logger.error(f"Error searching the vector store: {e}")
        if raise_on_error:
            raise
        return []


# Kept so existing callers/tests that import the old name keep working.
def search_qdrant(
    query: str, user_id: int, limit: int = 5, lecture_id: int | None = None
) -> list[dict]:
    return search_chunks(query, user_id, limit=limit, lecture_id=lecture_id)


def _grounding(hits: list[dict]) -> dict:
    """Build the grounding payload persisted with a note.

    The excerpt text is kept, not discarded: without it the UI can only ever
    show "grounded in 5 sections" and never what those sections actually said.
    """
    return {
        "chunks_used": len(hits),
        "lecture_ids": sorted(
            {h["lecture_id"] for h in hits if h.get("lecture_id") is not None}
        ),
        "top_score": max((h["score"] for h in hits if h.get("score") is not None), default=None),
        "excerpts": [
            {
                "lecture_id": h.get("lecture_id"),
                "note_id": h.get("note_id"),
                "page": h.get("page"),
                "score": h.get("score"),
                "kind": h.get("kind"),
                "text": h.get("text", "")[:1200],
            }
            for h in hits
        ],
    }


def _empty_grounding() -> dict:
    return {"chunks_used": 0, "lecture_ids": [], "top_score": None, "excerpts": []}


def _context_block(hits: list[dict]) -> str:
    """Render retrieved chunks with source labels the model can cite."""
    parts = []
    for i, hit in enumerate(hits, start=1):
        label = f"[{i}]"
        if hit.get("lecture_id") is not None:
            label += f" Lecture {hit['lecture_id']}"
        if hit.get("page"):
            label += f", p.{hit['page']}"
        parts.append(f"{label}\n{hit.get('text', '')}")
    return "\n\n---\n\n".join(parts)


def _style_overrides_block(overrides: dict | None) -> str:
    """Per-generation nudges that apply once without changing the saved profile."""
    if not overrides:
        return ""
    lines = []
    mapping = {
        "length": {
            "shorter": "Make this noticeably shorter and denser than usual.",
            "longer": "Go into more depth than usual.",
        },
        "diagrams": {
            "more": "Include more Mermaid diagrams than the profile suggests.",
            "fewer": "Avoid diagrams unless genuinely necessary.",
        },
        "examples": {
            "more": "Include more concrete worked examples than usual.",
            "fewer": "Keep examples to a minimum.",
        },
    }
    for key, value in overrides.items():
        line = mapping.get(key, {}).get(value)
        if line:
            lines.append(f"- {line}")
    if not lines:
        return ""
    return "\nONE-OFF ADJUSTMENTS FOR THIS GENERATION ONLY:\n" + "\n".join(lines) + "\n"


def _build_generation_prompt(
    prompt: str,
    style_profile: dict,
    hits: list[dict],
    note_type: str = "full",
    style_overrides: dict | None = None,
) -> str:
    type_instruction = NOTE_TYPE_INSTRUCTIONS.get(note_type, "")
    style_json = summarize_style_for_prompt(style_profile)
    return f"""{_BASE_INSTRUCTION}

{type_instruction}

USER STYLE PROFILE:
{style_json}
{_style_overrides_block(style_overrides)}
LECTURE EXCERPTS:
{_context_block(hits)}

USER PROMPT:
{prompt}
"""


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------


def retrieve_for_generation(
    prompt: str,
    user_id: int,
    lecture_id: int | None = None,
    course_id: int | None = None,
) -> list[dict]:
    """Retrieval step of generation, exposed so streaming can report it early."""
    scope = "lecture" if lecture_id else ("course" if course_id else "all")
    return search_chunks(
        prompt,
        user_id,
        limit=TOP_K_BY_SCOPE[scope],
        lecture_id=lecture_id,
        course_id=course_id,
        kind=KIND_LECTURE,
    )


def generate_notes(
    prompt: str,
    style_profile: dict,
    user_id: int,
    lecture_id: int | None = None,
    course_id: int | None = None,
    note_type: str = "full",
    style_overrides: dict | None = None,
) -> tuple[str, dict]:
    """Generate notes grounded in the user's retrieved chunks + their style profile.

    Returns ``(markdown_notes, grounding)`` where grounding carries the chunk
    count, source lectures, best match score and the excerpt text itself.
    """
    if not settings.GEMINI_API_KEY:
        return NO_KEY_MESSAGE, _empty_grounding()

    hits = retrieve_for_generation(prompt, user_id, lecture_id, course_id)
    grounding = _grounding(hits)
    full_prompt = _build_generation_prompt(
        prompt, style_profile, hits, note_type, style_overrides
    )

    try:
        response = generation_model.generate_content(full_prompt)
        return response.text, grounding
    except Exception as e:
        logger.error(f"Error generating notes with Gemini: {e}")
        raise


def stream_notes(
    prompt: str,
    style_profile: dict,
    user_id: int,
    lecture_id: int | None = None,
    course_id: int | None = None,
    note_type: str = "full",
    style_overrides: dict | None = None,
):
    """Yield ``(event, payload)`` tuples for the streaming generation endpoint.

    Events: ``retrieval`` (once, before the model is called), ``delta`` (text
    fragments), ``error``. Emitting retrieval first makes the wait informative —
    the user sees which sections were found while the model is still writing.
    """
    if not settings.GEMINI_API_KEY:
        yield "error", {"message": NO_KEY_MESSAGE}
        return

    hits = retrieve_for_generation(prompt, user_id, lecture_id, course_id)
    grounding = _grounding(hits)
    yield "retrieval", grounding

    full_prompt = _build_generation_prompt(
        prompt, style_profile, hits, note_type, style_overrides
    )
    try:
        for chunk in generation_model.generate_content(full_prompt, stream=True):
            text = getattr(chunk, "text", None)
            if text:
                yield "delta", {"text": text}
    except Exception as e:
        logger.error(f"Error streaming notes with Gemini: {e}")
        yield "error", {"message": describe_llm_error(e)}


def refine_notes(
    instruction: str,
    existing_notes: str,
    style_profile: dict,
    user_id: int,
    lecture_id: int | None = None,
    course_id: int | None = None,
    selection: str | None = None,
) -> tuple[str, dict]:
    """Revise an existing note per a short instruction, staying grounded + styled.

    When ``selection`` is given only that passage is rewritten and spliced back
    into the document, so a small request doesn't regenerate — and reshuffle —
    everything the user was happy with.
    """
    if not settings.GEMINI_API_KEY:
        return NO_KEY_MESSAGE, _empty_grounding()

    query = selection or existing_notes[:2000]
    hits = search_chunks(
        query,
        user_id,
        limit=TOP_K_BY_SCOPE["lecture" if lecture_id else "all"],
        lecture_id=lecture_id,
        course_id=course_id,
        kind=KIND_LECTURE,
    )
    grounding = _grounding(hits)
    style_json = summarize_style_for_prompt(style_profile)

    if selection and selection in existing_notes:
        system_instruction = (
            "You are an expert note editor. Rewrite ONLY the passage given below, "
            "following the revision instruction. Keep it grounded in the lecture "
            "excerpts and in the user's style. Return ONLY the rewritten passage in "
            "markdown — no preamble, no surrounding document, no code fence."
        )
        full_prompt = f"""{system_instruction}

USER STYLE PROFILE:
{style_json}

LECTURE EXCERPTS:
{_context_block(hits)}

REVISION INSTRUCTION:
{instruction}

PASSAGE TO REWRITE:
{selection}
"""
        try:
            response = generation_model.generate_content(full_prompt)
            rewritten = (response.text or "").strip()
            if not rewritten:
                return existing_notes, grounding
            return existing_notes.replace(selection, rewritten, 1), grounding
        except Exception as e:
            logger.error(f"Error refining selection with Gemini: {e}")
            raise

    system_instruction = (
        "You are an expert note editor. Revise the CURRENT NOTES according to the "
        "user's revision instruction. Keep the notes grounded in the provided lecture "
        "excerpts and strictly follow the user's style profile. Where a process or "
        "relationship is clearer as a diagram, use a valid Mermaid code block "
        "(```mermaid ... ```). Return only the revised notes in markdown."
    )
    full_prompt = f"""{system_instruction}

USER STYLE PROFILE:
{style_json}

LECTURE EXCERPTS:
{_context_block(hits)}

REVISION INSTRUCTION:
{instruction}

CURRENT NOTES:
{existing_notes}
"""

    try:
        response = generation_model.generate_content(full_prompt)
        return response.text, grounding
    except Exception as e:
        logger.error(f"Error refining notes with Gemini: {e}")
        raise


# --------------------------------------------------------------------------
# Question answering (chat)
# --------------------------------------------------------------------------


def retrieve_for_question(
    question: str,
    user_id: int,
    scope: str = "all",
    lecture_id: int | None = None,
    course_id: int | None = None,
    note_id: int | None = None,
) -> list[dict]:
    """Retrieval for a chat turn, scoped to where the question was asked."""
    limit = TOP_K_BY_SCOPE.get(scope, TOP_K_BY_SCOPE["all"])
    if scope == "note" and note_id is not None:
        # A question about one note should see that note first, then the lecture
        # it came from, so the answer can go beyond what the note already says.
        hits = search_chunks(question, user_id, limit=limit, note_id=note_id)
        if lecture_id is not None:
            hits += search_chunks(
                question, user_id, limit=limit, lecture_id=lecture_id, kind=KIND_LECTURE
            )
        return hits
    if scope == "lecture":
        return search_chunks(question, user_id, limit=limit, lecture_id=lecture_id)
    if scope == "course":
        return search_chunks(question, user_id, limit=limit, course_id=course_id)
    return search_chunks(question, user_id, limit=limit)


def _answer_prompt(question: str, hits: list[dict], history: list[dict]) -> str:
    history_block = ""
    if history:
        turns = "\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in history[-6:]
        )
        history_block = f"\nCONVERSATION SO FAR:\n{turns}\n"

    grounded = bool(hits)
    instruction = (
        "You are a study assistant answering a question about the user's own course "
        "material. Answer directly and concisely in markdown. Cite the excerpts you "
        "used with their bracketed numbers, e.g. [1], inline. Use LaTeX for maths and "
        "GitHub-flavoured markdown tables where they help."
    )
    if grounded:
        instruction += (
            " Base the answer on the excerpts below. If they only partly cover the "
            "question, answer what they support and say plainly what they do not."
        )
    else:
        instruction += (
            " No relevant excerpts were found in the user's material. Say so in one "
            "short sentence first, then answer from general knowledge."
        )

    return f"""{instruction}
{history_block}
EXCERPTS FROM THE USER'S MATERIAL:
{_context_block(hits) if grounded else "(none found)"}

QUESTION:
{question}
"""


def stream_answer(
    question: str,
    user_id: int,
    scope: str = "all",
    lecture_id: int | None = None,
    course_id: int | None = None,
    note_id: int | None = None,
    history: list[dict] | None = None,
):
    """Yield ``(event, payload)`` for a streamed chat answer with citations."""
    if not settings.GEMINI_API_KEY:
        yield "error", {"message": NO_KEY_MESSAGE}
        return

    hits = retrieve_for_question(question, user_id, scope, lecture_id, course_id, note_id)
    yield "citations", {"citations": _grounding(hits)["excerpts"]}

    try:
        for chunk in generation_model.generate_content(
            _answer_prompt(question, hits, history or []), stream=True
        ):
            text = getattr(chunk, "text", None)
            if text:
                yield "delta", {"text": text}
    except Exception as e:
        logger.error(f"Error streaming answer with Gemini: {e}")
        yield "error", {"message": describe_llm_error(e)}


def answer_question(
    question: str,
    user_id: int,
    scope: str = "all",
    lecture_id: int | None = None,
    course_id: int | None = None,
    note_id: int | None = None,
    history: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    """Non-streaming answer, used as the fallback path and by tests."""
    if not settings.GEMINI_API_KEY:
        return NO_KEY_MESSAGE, []

    hits = retrieve_for_question(question, user_id, scope, lecture_id, course_id, note_id)
    try:
        response = generation_model.generate_content(
            _answer_prompt(question, hits, history or [])
        )
        return response.text, _grounding(hits)["excerpts"]
    except Exception as e:
        logger.error(f"Error answering question with Gemini: {e}")
        raise


# --------------------------------------------------------------------------
# Titles
# --------------------------------------------------------------------------


def generate_title(markdown: str, fallback: str = "Untitled note") -> str:
    """Derive a short, human title for a note.

    Prefers the document's own first heading (free, deterministic, and usually
    exactly right) and only asks the model when there isn't one.
    """
    for line in (markdown or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            candidate = stripped.lstrip("#").strip()
            if candidate:
                return candidate[:120]

    if not settings.GEMINI_API_KEY or not (markdown or "").strip():
        return fallback

    try:
        response = generation_model.generate_content(
            "Give a short title (max 8 words) for these notes. Return only the "
            "title, with no quotes or punctuation at the end.\n\n" + markdown[:2000]
        )
        title = (response.text or "").strip().strip('"').splitlines()[0]
        return title[:120] or fallback
    except Exception as e:
        logger.warning(f"Could not generate a title: {e}")
        return fallback


def suggested_questions(markdown: str, limit: int = 3) -> list[str]:
    """Seed an empty chat with questions drawn from the note's own headings."""
    headings = [
        line.strip().lstrip("#").strip()
        for line in (markdown or "").splitlines()
        if line.strip().startswith("##")
    ]
    seen, questions = set(), []
    for heading in headings:
        if not heading or heading.lower() in seen:
            continue
        seen.add(heading.lower())
        questions.append(f"Explain {heading} in more depth")
        if len(questions) >= limit:
            break
    return questions
