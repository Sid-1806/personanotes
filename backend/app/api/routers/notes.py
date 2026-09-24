"""Notes: generation, streaming, browsing, editing, versions and teaching.

Two invariants this module is built around:

1. **A user's own edit is never lost.** ``EditedNote`` rows carry ``is_current``
   and are what :func:`get_note` serves as the body. The model's output is kept
   alongside so the two can be compared.
2. **Every generation is addressable.** Refinements link to their parent, so a
   chain of revisions is a version timeline rather than a pile of near-identical
   rows.
"""

import json
import logging
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.cache import get_cache, prompt_cache_key
from app.core.config import settings
from app.core.exceptions import LLMServiceError
from app.core.ratelimit import rate_limit
from app.db.database import SessionLocal
from app.models.chat import ChatThread
from app.models.course import Course
from app.models.feedback import EditedNote, GeneratedNote, StyleFeedback
from app.models.lecture import Lecture
from app.models.style import StyleProfile
from app.models.user import User
from app.schemas.note import (
    FeedbackRequest,
    FeedbackResponse,
    GenerateNotesRequest,
    GenerateNotesResponse,
    Grounding,
    NoteDetailResponse,
    NoteDiffResponse,
    NoteListResponse,
    NoteSummary,
    NoteUpdateRequest,
    NoteVersion,
    NoteVersionsResponse,
    RefineRequest,
    SaveAnswerRequest,
)
from app.services import llm_service
from app.services.ingestion import index_note
from app.services.vector_db import delete_note_points

logger = logging.getLogger(__name__)

router = APIRouter()

GENERATE_LIMIT = Depends(
    rate_limit("generate", settings.RATE_LIMIT_GENERATE, settings.RATE_LIMIT_WINDOW_SECONDS)
)
REFINE_LIMIT = Depends(
    rate_limit("refine", settings.RATE_LIMIT_REFINE, settings.RATE_LIMIT_WINDOW_SECONDS)
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _word_count(markdown: str) -> int:
    return len((markdown or "").split())


def _excerpt(markdown: str, length: int = 180) -> str:
    """First readable prose from a note, for list rows.

    Fenced blocks are skipped wholesale, not just their delimiter lines --
    otherwise a note that opens with a code block previews as ``x = 1``.
    """
    in_fence = False
    for raw in (markdown or "").splitlines():
        line = raw.strip()
        if line.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence or not line or line.startswith(("#", "|", ">", "---", "===")):
            continue
        cleaned = line.lstrip("-*0123456789. ").strip()
        if cleaned:
            return cleaned[:length]
    return (markdown or "").strip()[:length]


async def get_owned_note(db: AsyncSession, note_id: int, user: User) -> GeneratedNote:
    result = await db.execute(
        select(GeneratedNote).where(
            GeneratedNote.id == note_id, GeneratedNote.user_id == user.id
        )
    )
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


async def _current_edit(db: AsyncSession, note_id: int) -> EditedNote | None:
    result = await db.execute(
        select(EditedNote)
        .where(EditedNote.generated_note_id == note_id, EditedNote.is_current.is_(True))
        .order_by(EditedNote.edited_at.desc())
    )
    return result.scalars().first()


async def note_body(db: AsyncSession, note: GeneratedNote) -> str:
    """The note as the user should see it: their edit if they made one."""
    edit = await _current_edit(db, note.id)
    return edit.edited_markdown if edit else note.generated_markdown


async def _replace_current_edit(
    db: AsyncSession, note_id: int, markdown: str
) -> EditedNote:
    """Make ``markdown`` the note's current revision, retiring any previous one.

    Saves to the same note are serialised on the note row. Reading the previous
    edit and flipping it in Python raced: two concurrent saves both read the
    same "previous", both inserted ``is_current=True``, and the note ended up
    with several revisions claiming to be current — so which one you got back
    depended on timing.
    """
    # Lock the parent note so concurrent saves queue rather than interleave.
    await db.execute(
        select(GeneratedNote.id).where(GeneratedNote.id == note_id).with_for_update()
    )
    # Retire every prior revision in one statement, not one object at a time.
    await db.execute(
        update(EditedNote)
        .where(
            EditedNote.generated_note_id == note_id,
            EditedNote.is_current.is_(True),
        )
        .values(is_current=False)
    )
    edit = EditedNote(
        generated_note_id=note_id, edited_markdown=markdown, is_current=True
    )
    db.add(edit)
    await db.flush()
    return edit


async def _load_style(db: AsyncSession, user: User) -> tuple[dict, int]:
    result = await db.execute(
        select(StyleProfile).where(StyleProfile.user_id == user.id)
    )
    profile = result.scalars().first()
    return (profile.profile_json if profile else {}), (profile.version if profile else 0)


async def _name_lookup(
    db: AsyncSession, lecture_ids: set[int], course_ids: set[int]
) -> tuple[dict[int, str], dict[int, str]]:
    lectures: dict[int, str] = {}
    courses: dict[int, str] = {}
    if lecture_ids:
        rows = (
            await db.execute(
                select(Lecture.id, Lecture.title, Lecture.filename).where(
                    Lecture.id.in_(lecture_ids)
                )
            )
        ).all()
        lectures = {lid: (title or filename) for lid, title, filename in rows}
    if course_ids:
        rows = (
            await db.execute(select(Course.id, Course.name).where(Course.id.in_(course_ids)))
        ).all()
        courses = {cid: name for cid, name in rows}
    return lectures, courses


async def summarize_notes(
    db: AsyncSession, notes: List[GeneratedNote]
) -> List[NoteSummary]:
    """Build list rows, resolving names and edit state in bulk."""
    if not notes:
        return []

    note_ids = [n.id for n in notes]
    edited_ids = {
        row[0]
        for row in (
            await db.execute(
                select(EditedNote.generated_note_id).where(
                    EditedNote.generated_note_id.in_(note_ids),
                    EditedNote.is_current.is_(True),
                )
            )
        ).all()
    }
    lectures, courses = await _name_lookup(
        db,
        {n.lecture_id for n in notes if n.lecture_id},
        {n.course_id for n in notes if n.course_id},
    )

    summaries = []
    for note in notes:
        body = note.generated_markdown
        summaries.append(
            NoteSummary(
                id=note.id,
                title=note.title,
                note_type=note.note_type,
                lecture_id=note.lecture_id,
                lecture_title=lectures.get(note.lecture_id),
                course_id=note.course_id,
                course_name=courses.get(note.course_id),
                parent_note_id=note.parent_note_id,
                has_edits=note.id in edited_ids,
                excerpt=_excerpt(body),
                word_count=_word_count(body),
                created_at=note.created_at,
                updated_at=note.updated_at,
            )
        )
    return summaries


def _grounding_model(raw: dict | None) -> Grounding:
    if not raw:
        return Grounding()
    try:
        return Grounding(**raw)
    except Exception:  # tolerate older rows written before the schema settled
        return Grounding(
            chunks_used=raw.get("chunks_used", 0),
            lecture_ids=raw.get("lecture_ids", []),
        )


async def _hydrate_grounding(db: AsyncSession, grounding: Grounding) -> Grounding:
    """Fill in lecture titles so citations read as documents, not ids."""
    ids = {e.lecture_id for e in grounding.excerpts if e.lecture_id} | set(
        grounding.lecture_ids
    )
    if not ids:
        return grounding
    lectures, _ = await _name_lookup(db, ids, set())
    for excerpt in grounding.excerpts:
        if excerpt.lecture_id:
            excerpt.lecture_title = lectures.get(excerpt.lecture_id)
    return grounding


async def _root_id(db: AsyncSession, note: GeneratedNote) -> int:
    """Walk up the refine chain to the original generation."""
    current, seen = note, {note.id}
    while current.parent_note_id and current.parent_note_id not in seen:
        seen.add(current.parent_note_id)
        parent = (
            await db.execute(
                select(GeneratedNote).where(GeneratedNote.id == current.parent_note_id)
            )
        ).scalars().first()
        if parent is None:
            break
        current = parent
    return current.id


async def _chain(db: AsyncSession, root_id: int, user: User) -> List[GeneratedNote]:
    """Every note descended from a root, oldest first."""
    collected: List[GeneratedNote] = []
    frontier = [root_id]
    seen: set[int] = set()
    while frontier:
        rows = (
            await db.execute(
                select(GeneratedNote).where(
                    GeneratedNote.user_id == user.id,
                    or_(
                        GeneratedNote.id.in_(frontier),
                        GeneratedNote.parent_note_id.in_(frontier),
                    ),
                )
            )
        ).scalars().all()
        frontier = []
        for row in rows:
            if row.id in seen:
                continue
            seen.add(row.id)
            collected.append(row)
            frontier.append(row.id)
    collected.sort(key=lambda n: (n.created_at, n.id))
    return collected


async def _persist_note(
    db: AsyncSession,
    user_id: int,
    markdown: str,
    grounding: dict,
    *,
    prompt: str | None = None,
    lecture_id: int | None = None,
    course_id: int | None = None,
    note_type: str = "full",
    parent_note_id: int | None = None,
    title: str | None = None,
) -> GeneratedNote:
    """Create a note row, deriving a title and resolving its course.

    Takes a plain ``user_id`` rather than a ``User`` so it can be called from a
    streaming response, which runs after the request-scoped session has closed
    and therefore needs a session of its own.
    """
    if course_id is None and lecture_id is not None:
        lecture = (
            await db.execute(select(Lecture).where(Lecture.id == lecture_id))
        ).scalars().first()
        course_id = lecture.course_id if lecture else None

    note = GeneratedNote(
        user_id=user_id,
        lecture_id=lecture_id,
        course_id=course_id,
        parent_note_id=parent_note_id,
        note_type=note_type,
        prompt=prompt,
        title=title or llm_service.generate_title(markdown, fallback=prompt or "Untitled note"),
        generated_markdown=markdown,
        grounding_json=grounding,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


def _response(note: GeneratedNote, grounding: Grounding) -> GenerateNotesResponse:
    return GenerateNotesResponse(
        id=note.id,
        title=note.title,
        notes=note.generated_markdown,
        note_type=note.note_type,
        lecture_id=note.lecture_id,
        course_id=note.course_id,
        parent_note_id=note.parent_note_id,
        chunks_used=grounding.chunks_used,
        lecture_ids=grounding.lecture_ids,
        grounding=grounding,
        created_at=note.created_at,
    )


# --------------------------------------------------------------------------
# Browsing
# --------------------------------------------------------------------------


@router.get("/", response_model=NoteListResponse)
async def list_notes(
    course_id: int | None = Query(default=None),
    lecture_id: int | None = Query(default=None),
    note_type: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Match note titles and bodies"),
    roots_only: bool = Query(
        default=False, description="Hide refinements, showing only original notes"
    ),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Browse every note the user owns.

    Without this endpoint notes were only reachable as the five most recent
    entries on the dashboard, which made everything older unreachable.
    """
    filters = [
        GeneratedNote.user_id == current_user.id,
        GeneratedNote.archived.is_(False),
    ]
    if course_id is not None:
        filters.append(GeneratedNote.course_id == course_id)
    if lecture_id is not None:
        filters.append(GeneratedNote.lecture_id == lecture_id)
    if note_type:
        filters.append(GeneratedNote.note_type == note_type)
    if roots_only:
        filters.append(GeneratedNote.parent_note_id.is_(None))
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                GeneratedNote.title.ilike(pattern),
                GeneratedNote.generated_markdown.ilike(pattern),
            )
        )

    total = (
        await db.execute(select(func.count(GeneratedNote.id)).where(*filters))
    ).scalar() or 0

    notes = (
        await db.execute(
            select(GeneratedNote)
            .where(*filters)
            .order_by(GeneratedNote.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    return NoteListResponse(
        items=await summarize_notes(db, list(notes)),
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{id}", response_model=NoteDetailResponse)
async def get_note(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Fetch a note, including the user's own saved revision when one exists."""
    note = await get_owned_note(db, id, current_user)
    edit = await _current_edit(db, note.id)

    lectures, courses = await _name_lookup(
        db,
        {note.lecture_id} if note.lecture_id else set(),
        {note.course_id} if note.course_id else set(),
    )
    grounding = await _hydrate_grounding(db, _grounding_model(note.grounding_json))
    root_id = await _root_id(db, note)
    chain = await _chain(db, root_id, current_user)

    return NoteDetailResponse(
        id=note.id,
        title=note.title,
        note_type=note.note_type,
        prompt=note.prompt,
        lecture_id=note.lecture_id,
        lecture_title=lectures.get(note.lecture_id),
        course_id=note.course_id,
        course_name=courses.get(note.course_id),
        parent_note_id=note.parent_note_id,
        root_note_id=root_id,
        original_markdown=note.generated_markdown,
        edited_markdown=edit.edited_markdown if edit else None,
        has_edits=edit is not None,
        grounding=grounding,
        version_count=len(chain),
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.get("/{id}/versions", response_model=NoteVersionsResponse)
async def get_note_versions(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """The full history of a note: generations, refinements and user edits."""
    note = await get_owned_note(db, id, current_user)
    root_id = await _root_id(db, note)
    chain = await _chain(db, root_id, current_user)

    versions: List[NoteVersion] = []
    for index, item in enumerate(chain):
        versions.append(
            NoteVersion(
                id=item.id,
                kind="generated" if item.parent_note_id is None else "refined",
                note_id=item.id,
                label="Original" if index == 0 else f"Revision {index}",
                title=item.title,
                word_count=_word_count(item.generated_markdown),
                created_at=item.created_at,
                is_current=item.id == note.id,
            )
        )

        edits = (
            await db.execute(
                select(EditedNote)
                .where(EditedNote.generated_note_id == item.id)
                .order_by(EditedNote.edited_at)
            )
        ).scalars().all()
        for edit_index, edit in enumerate(edits, start=1):
            versions.append(
                NoteVersion(
                    id=edit.id,
                    kind="edited",
                    note_id=item.id,
                    label=f"Your edit{'' if len(edits) == 1 else f' {edit_index}'}",
                    title=item.title,
                    word_count=_word_count(edit.edited_markdown),
                    created_at=edit.edited_at,
                    is_current=bool(edit.is_current) and item.id == note.id,
                )
            )

    versions.sort(key=lambda v: v.created_at)
    return NoteVersionsResponse(root_note_id=root_id, versions=versions)


@router.get("/{id}/diff", response_model=NoteDiffResponse)
async def diff_versions(
    id: int,
    against: int = Query(..., description="Note id to compare with"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Compare two versions of a note side by side."""
    from app.evaluation.engine import evaluate_generation

    left = await get_owned_note(db, against, current_user)
    right = await get_owned_note(db, id, current_user)

    left_md = await note_body(db, left)
    right_md = await note_body(db, right)

    try:
        stats = evaluate_generation(left_md, right_md)
    except Exception:  # comparison is still useful without the metrics
        stats = {}

    return NoteDiffResponse(
        from_label=left.title or f"Note {left.id}",
        to_label=right.title or f"Note {right.id}",
        from_markdown=left_md,
        to_markdown=right_md,
        stats=stats,
    )


@router.get("/{id}/export")
async def export_note(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Download a note as markdown. Notes you can't take out aren't really yours."""
    from fastapi.responses import PlainTextResponse

    note = await get_owned_note(db, id, current_user)
    body = await note_body(db, note)
    title = note.title or f"note-{note.id}"
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip() or f"note-{note.id}"
    return PlainTextResponse(
        body,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe}.md"'},
    )


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------


def _resolved_prompt(request: GenerateNotesRequest) -> str:
    prompt = (request.prompt or "").strip()
    if prompt:
        return prompt
    # Presets carry their own intent, so an empty box is valid for them.
    default = llm_service.DEFAULT_PROMPT_BY_TYPE.get(request.note_type)
    if default:
        return default
    raise HTTPException(status_code=400, detail="Tell PersonaNotes what to write about.")


@router.post("/generate", response_model=GenerateNotesResponse, dependencies=[GENERATE_LIMIT])
async def generate_user_notes(
    request: GenerateNotesRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Generate personalized notes grounded in the user's own material."""
    prompt = _resolved_prompt(request)
    style_dict, profile_version = await _load_style(db, current_user)

    cache = await get_cache()
    cache_key = (
        f"gen:{current_user.id}:{request.lecture_id}:{request.course_id}:"
        f"{request.note_type}:{profile_version}:{prompt_cache_key(prompt)}:"
        f"{prompt_cache_key(json.dumps(request.style_overrides or {}, sort_keys=True))}"
    )

    # An explicit regeneration must bypass the cache. Otherwise "Regenerate"
    # returns byte-identical text while still writing a new row — the button
    # appears to do nothing and quietly duplicates data.
    use_cache = settings.CACHE_ENABLED and not request.no_cache
    cached = await cache.get_json(cache_key) if use_cache else None

    if cached:
        notes, grounding_raw = cached["notes"], cached["grounding"]
    else:
        try:
            notes, grounding_raw = await run_in_threadpool(
                llm_service.generate_notes,
                prompt,
                style_dict,
                current_user.id,
                request.lecture_id,
                request.course_id,
                request.note_type,
                request.style_overrides,
            )
        except Exception as exc:
            logger.exception("Generation failed for user %s", current_user.id)
            raise LLMServiceError(
                f"{llm_service.describe_llm_error(exc)} Your prompt is safe."
            ) from exc

        if settings.CACHE_ENABLED:
            await cache.set_json(
                cache_key,
                {"notes": notes, "grounding": grounding_raw},
                settings.GENERATION_CACHE_TTL,
            )

    note = await _persist_note(
        db,
        current_user.id,
        notes,
        grounding_raw,
        prompt=prompt,
        lecture_id=request.lecture_id,
        course_id=request.course_id,
        note_type=request.note_type,
    )
    background_tasks.add_task(
        index_note, note.id, current_user.id, notes, note.course_id, note.lecture_id
    )

    grounding = await _hydrate_grounding(db, _grounding_model(grounding_raw))
    return _response(note, grounding)


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.post("/generate/stream", dependencies=[GENERATE_LIMIT])
async def stream_user_notes(
    request: GenerateNotesRequest,
    http_request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Stream a generation as it is written.

    Emits ``retrieval`` (which sections were found) before the first token, so
    the wait shows real progress instead of an opaque spinner, then ``delta``
    fragments, then ``done`` with the saved note id.
    """
    prompt = _resolved_prompt(request)
    style_dict, _ = await _load_style(db, current_user)
    user_id = current_user.id

    async def event_stream():
        collected: list[str] = []
        grounding_raw: dict = {}
        stream = llm_service.stream_notes(
            prompt,
            style_dict,
            user_id,
            request.lecture_id,
            request.course_id,
            request.note_type,
            request.style_overrides,
        )
        try:
            while True:
                item = await run_in_threadpool(lambda: next(stream, None))
                if item is None:
                    break
                if await http_request.is_disconnected():
                    break
                event, payload = item
                if event == "retrieval":
                    grounding_raw = payload
                elif event == "delta":
                    collected.append(payload["text"])
                yield _sse(event, payload)

            markdown = "".join(collected)
            if not markdown.strip():
                yield _sse("error", {"message": "The model returned nothing. Please retry."})
                return

            # A streaming body runs after the request-scoped session has already
            # been closed, so persistence needs a session of its own.
            async with SessionLocal() as session:
                note = await _persist_note(
                    session,
                    user_id,
                    markdown,
                    grounding_raw,
                    prompt=prompt,
                    lecture_id=request.lecture_id,
                    course_id=request.course_id,
                    note_type=request.note_type,
                )
                note_id, note_title = note.id, note.title
                note_course_id, note_lecture_id = note.course_id, note.lecture_id

            await run_in_threadpool(
                index_note, note_id, user_id, markdown, note_course_id, note_lecture_id
            )
            yield _sse("done", {"id": note_id, "title": note_title})
        except Exception as exc:  # pragma: no cover - network/stream failures
            logger.exception("Streaming generation failed: %s", exc)
            yield _sse("error", {"message": "Generation failed partway through. Please retry."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{id}/refine", response_model=GenerateNotesResponse, dependencies=[REFINE_LIMIT])
async def refine_user_notes(
    id: int,
    request: RefineRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Revise a note per an instruction, saving the result as a new version.

    The new note links back to its parent, so refining builds a history instead
    of scattering near-identical rows through the notes list.
    """
    if not request.instruction.strip():
        raise HTTPException(status_code=400, detail="Tell PersonaNotes what to change.")

    note = await get_owned_note(db, id, current_user)
    style_dict, _ = await _load_style(db, current_user)
    # Refine what the user is actually looking at, edits included.
    source = await note_body(db, note)

    try:
        refined, grounding_raw = await run_in_threadpool(
            llm_service.refine_notes,
            request.instruction,
            source,
            style_dict,
            current_user.id,
            note.lecture_id,
            note.course_id,
            request.selection,
        )
    except Exception as exc:
        logger.exception("Refine failed for note %s", id)
        raise LLMServiceError(
            f"{llm_service.describe_llm_error(exc)} The original note is unchanged."
        ) from exc

    new_note = await _persist_note(
        db,
        current_user.id,
        refined,
        grounding_raw,
        prompt=request.instruction,
        lecture_id=note.lecture_id,
        course_id=note.course_id,
        note_type=note.note_type,
        parent_note_id=note.id,
        title=note.title,
    )
    background_tasks.add_task(
        index_note, new_note.id, current_user.id, refined, new_note.course_id, new_note.lecture_id
    )

    grounding = await _hydrate_grounding(db, _grounding_model(grounding_raw))
    return _response(new_note, grounding)


# --------------------------------------------------------------------------
# Saving and teaching
# --------------------------------------------------------------------------


async def _apply_teaching(
    db: AsyncSession, note: GeneratedNote, edited_markdown: str, user: User
) -> tuple[list[str], float | None, list[str]]:
    """Run the style-learning loop over an edit. Returns (features, score, summary)."""
    from app.evaluation.engine import evaluate_generation
    from app.feedback.style_feedback import generate_style_feedback
    from app.feedback.summary import humanize_changes
    from app.feedback.updater import apply_feedback_to_profile
    from app.models.style import StyleProfileVersion
    from app.style.schema import StyleProfileSchema

    feedback_data = await run_in_threadpool(
        generate_style_feedback, note.generated_markdown, edited_markdown
    )
    eval_result = evaluate_generation(note.generated_markdown, edited_markdown)
    feedback_data["evaluation"] = eval_result

    db.add(StyleFeedback(generated_note_id=note.id, feedback_json=feedback_data))

    profile = (
        await db.execute(select(StyleProfile).where(StyleProfile.user_id == user.id))
    ).scalars().first()

    updated_features: list[str] = []
    if profile:
        db.add(
            StyleProfileVersion(
                user_id=user.id, version=profile.version, profile_json=profile.profile_json
            )
        )
        try:
            current_schema = StyleProfileSchema(**profile.profile_json)
        except Exception:
            current_schema = StyleProfileSchema()
        updated_schema = apply_feedback_to_profile(current_schema, feedback_data)
        profile.profile_json = updated_schema.model_dump()
        profile.version += 1
        updated_features = [c["feature"] for c in feedback_data.get("changes", [])]

    return (
        updated_features,
        eval_result.get("personalization_score"),
        humanize_changes(feedback_data),
    )


@router.patch("/{id}", response_model=NoteDetailResponse)
async def update_note(
    id: int,
    payload: NoteUpdateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Save the user's own version of a note, and optionally rename it.

    Saving always persists. Teaching the style profile is a separate, explicit
    side effect — conflating the two is how edits used to vanish.
    """
    note = await get_owned_note(db, id, current_user)

    if payload.title is not None:
        note.title = payload.title.strip() or None

    if payload.markdown is not None:
        markdown = payload.markdown
        await _replace_current_edit(db, note.id, markdown)

        if payload.teach and markdown.strip() != note.generated_markdown.strip():
            try:
                await _apply_teaching(db, note, markdown, current_user)
            except Exception:
                # A failure to learn must never cost the user their edit.
                logger.exception("Style learning failed for note %s; edit still saved", id)

        background_tasks.add_task(
            index_note, note.id, current_user.id, markdown, note.course_id, note.lecture_id
        )

    await db.commit()
    return await get_note(id, db, current_user)


@router.post("/{id}/feedback", response_model=FeedbackResponse)
async def submit_note_feedback(
    id: int,
    request: FeedbackRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Submit an edited note to the continual learning pipeline.

    Also persists the edit as the note's current body, so teaching and saving
    can no longer diverge.
    """
    note = await get_owned_note(db, id, current_user)

    await _replace_current_edit(db, note.id, request.edited_markdown)

    updated_features, score, summary = await _apply_teaching(
        db, note, request.edited_markdown, current_user
    )
    await db.commit()

    background_tasks.add_task(
        index_note,
        note.id,
        current_user.id,
        request.edited_markdown,
        note.course_id,
        note.lecture_id,
    )

    return FeedbackResponse(
        updated_features=updated_features,
        personalization_score=score,
        summary=summary,
    )


@router.post("/{id}/revert", response_model=NoteDetailResponse)
async def revert_note(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Discard the user's edits and go back to the generated text."""
    note = await get_owned_note(db, id, current_user)
    edit = await _current_edit(db, note.id)
    if edit is None:
        raise HTTPException(status_code=409, detail="This note has no edits to revert.")
    edit.is_current = False
    await db.commit()
    return await get_note(id, db, current_user)


@router.post("/save-answer", response_model=GenerateNotesResponse, status_code=201)
async def save_answer(
    payload: SaveAnswerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Keep a useful AI answer as a note, or append it to an existing one."""
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="There's nothing to save.")

    if payload.append_to_note_id is not None:
        target = await get_owned_note(db, payload.append_to_note_id, current_user)
        body = await note_body(db, target)
        merged = f"{body.rstrip()}\n\n{payload.content.strip()}\n"
        await _replace_current_edit(db, target.id, merged)
        await db.commit()
        background_tasks.add_task(
            index_note, target.id, current_user.id, merged, target.course_id, target.lecture_id
        )
        grounding = await _hydrate_grounding(db, _grounding_model(target.grounding_json))
        return _response(target, grounding)

    note = await _persist_note(
        db,
        current_user.id,
        payload.content,
        {},
        lecture_id=payload.lecture_id,
        course_id=payload.course_id,
        note_type="saved_answer",
        title=payload.title,
    )
    background_tasks.add_task(
        index_note, note.id, current_user.id, payload.content, note.course_id, note.lecture_id
    )
    return _response(note, Grounding())


@router.delete("/{id}", status_code=204)
async def delete_note(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Delete a note, its edits, its feedback, and its index entries."""
    note = await get_owned_note(db, id, current_user)

    for model in (EditedNote, StyleFeedback):
        rows = (
            await db.execute(select(model).where(model.generated_note_id == note.id))
        ).scalars().all()
        for row in rows:
            await db.delete(row)

    children = (
        await db.execute(
            select(GeneratedNote).where(GeneratedNote.parent_note_id == note.id)
        )
    ).scalars().all()
    for child in children:
        child.parent_note_id = note.parent_note_id

    threads = (
        await db.execute(select(ChatThread).where(ChatThread.note_id == note.id))
    ).scalars().all()
    for thread in threads:
        thread.note_id = None
        thread.scope = "all" if thread.scope == "note" else thread.scope

    await db.flush()
    delete_note_points(note.id, current_user.id)
    await db.delete(note)
    await db.commit()
    return None
