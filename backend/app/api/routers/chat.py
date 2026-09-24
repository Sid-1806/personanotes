"""Ask questions about your own material, scoped to a note, lecture or course.

Built directly on the existing retrieval path: a chat turn is a scoped
``search_chunks`` plus a short conversational instruction. Answers carry their
citations so the student can check them, and threads persist so a conversation
survives a reload.
"""

import json
import logging
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.exceptions import LLMServiceError
from app.core.ratelimit import rate_limit
from app.db.database import SessionLocal
from app.models.chat import ChatMessage, ChatThread
from app.models.feedback import GeneratedNote
from app.models.lecture import Lecture
from app.models.user import User
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatThreadDetail,
    ChatThreadSummary,
)
from app.services import llm_service
from app.services.vector_db import KIND_NOTE

logger = logging.getLogger(__name__)

router = APIRouter()

CHAT_LIMIT = Depends(
    rate_limit("chat", settings.RATE_LIMIT_CHAT, settings.RATE_LIMIT_WINDOW_SECONDS)
)


async def _get_thread(db: AsyncSession, thread_id: int, user: User) -> ChatThread:
    thread = (
        await db.execute(
            select(ChatThread).where(
                ChatThread.id == thread_id, ChatThread.user_id == user.id
            )
        )
    ).scalars().first()
    if thread is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return thread


async def _resolve_thread(db: AsyncSession, payload: ChatRequest, user: User) -> ChatThread:
    """Find the thread for this turn, creating one on the first message."""
    if payload.thread_id is not None:
        return await _get_thread(db, payload.thread_id, user)

    thread = ChatThread(
        user_id=user.id,
        scope=payload.scope,
        course_id=payload.course_id,
        lecture_id=payload.lecture_id,
        note_id=payload.note_id,
        # The first question makes a far better thread name than "New conversation".
        title=payload.message.strip()[:80] or "New conversation",
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


async def _history(db: AsyncSession, thread_id: int) -> list[dict]:
    rows = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at)
        )
    ).scalars().all()
    return [{"role": m.role, "content": m.content} for m in rows]


async def _hydrate_citations(db: AsyncSession, citations: list[dict]) -> list[dict]:
    """Attach source titles so a citation names a document, not an id.

    A chunk from one of the user's own generated notes carries the lecture id it
    came from, so labelling purely by ``lecture_id`` would present AI-written
    text as if it were the source PDF. Citations exist to be checked, so a note
    chunk is named as a note and a lecture chunk as the lecture.
    """
    lecture_ids = {
        c.get("lecture_id")
        for c in citations
        if c.get("lecture_id") and c.get("kind") != KIND_NOTE
    }
    note_ids = {c.get("note_id") for c in citations if c.get("note_id")}

    lecture_names: dict[int, str] = {}
    if lecture_ids:
        rows = (
            await db.execute(
                select(Lecture.id, Lecture.title, Lecture.filename).where(
                    Lecture.id.in_(lecture_ids)
                )
            )
        ).all()
        lecture_names = {lid: (title or filename) for lid, title, filename in rows}

    note_names: dict[int, str] = {}
    if note_ids:
        rows = (
            await db.execute(
                select(GeneratedNote.id, GeneratedNote.title).where(
                    GeneratedNote.id.in_(note_ids)
                )
            )
        ).all()
        note_names = {nid: (title or f"Note {nid}") for nid, title in rows}

    for citation in citations:
        if citation.get("kind") == KIND_NOTE or citation.get("note_id"):
            citation["note_title"] = note_names.get(citation.get("note_id"))
            # Don't stamp a note chunk with the lecture's name.
            citation["lecture_title"] = None
        elif citation.get("lecture_id"):
            citation["lecture_title"] = lecture_names.get(citation["lecture_id"])
    return citations


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.post("/", response_model=ChatResponse, dependencies=[CHAT_LIMIT])
async def ask(
    payload: ChatRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Answer a question about the user's material (non-streaming)."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Ask a question first.")

    thread = await _resolve_thread(db, payload, current_user)
    is_new_thread = payload.thread_id is None
    history = await _history(db, thread.id)

    user_message = ChatMessage(
        thread_id=thread.id, role="user", content=payload.message
    )
    db.add(user_message)
    await db.commit()

    try:
        answer, citations = await run_in_threadpool(
            llm_service.answer_question,
            payload.message,
            current_user.id,
            thread.scope,
            thread.lecture_id,
            thread.course_id,
            thread.note_id,
            history,
        )
    except Exception as exc:
        logger.exception("Chat answer failed for user %s", current_user.id)
        # A thread created for this turn has nothing worth keeping if the answer
        # never arrived; leaving it behind litters the conversation list with
        # questions that can't be reopened. An existing thread keeps its message
        # so the user can retry in place.
        if is_new_thread:
            await db.delete(user_message)
            await db.delete(thread)
            await db.commit()
        raise LLMServiceError(llm_service.describe_llm_error(exc)) from exc

    citations = await _hydrate_citations(db, citations)
    message = ChatMessage(
        thread_id=thread.id, role="assistant", content=answer, citations=citations
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return ChatResponse(
        thread_id=thread.id, message=ChatMessageResponse.model_validate(message)
    )


@router.post("/stream", dependencies=[CHAT_LIMIT])
async def ask_stream(
    payload: ChatRequest,
    http_request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Stream an answer, emitting citations as soon as retrieval resolves."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Ask a question first.")

    thread = await _resolve_thread(db, payload, current_user)
    history = await _history(db, thread.id)
    db.add(ChatMessage(thread_id=thread.id, role="user", content=payload.message))
    await db.commit()

    user_id = current_user.id
    scope, lecture_id, course_id, note_id = (
        thread.scope,
        thread.lecture_id,
        thread.course_id,
        thread.note_id,
    )
    thread_id, thread_title = thread.id, thread.title

    async def event_stream():
        collected: list[str] = []
        citations: list[dict] = []
        yield _sse("thread", {"thread_id": thread_id, "title": thread_title})

        stream = llm_service.stream_answer(
            payload.message, user_id, scope, lecture_id, course_id, note_id, history
        )
        try:
            # A streaming body outlives the request-scoped session, so every
            # database touch below runs on a session this generator owns.
            async with SessionLocal() as session:
                while True:
                    item = await run_in_threadpool(lambda: next(stream, None))
                    if item is None:
                        break
                    if await http_request.is_disconnected():
                        break
                    event, data = item
                    if event == "citations":
                        citations = await _hydrate_citations(session, data["citations"])
                        yield _sse("citations", {"citations": citations})
                        continue
                    if event == "delta":
                        collected.append(data["text"])
                    yield _sse(event, data)

                answer = "".join(collected)
                if not answer.strip():
                    yield _sse("error", {"message": "No answer was produced. Please retry."})
                    return

                message = ChatMessage(
                    thread_id=thread_id,
                    role="assistant",
                    content=answer,
                    citations=citations,
                )
                session.add(message)
                await session.commit()
                await session.refresh(message)
                yield _sse("done", {"message_id": message.id, "thread_id": thread_id})
        except Exception as exc:  # pragma: no cover - stream/network failures
            logger.exception("Streaming chat failed: %s", exc)
            yield _sse("error", {"message": "The answer failed partway through. Please retry."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/threads", response_model=List[ChatThreadSummary])
async def list_threads(
    scope: str | None = Query(default=None),
    course_id: int | None = Query(default=None),
    lecture_id: int | None = Query(default=None),
    note_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    filters = [ChatThread.user_id == current_user.id]
    if scope:
        filters.append(ChatThread.scope == scope)
    if course_id is not None:
        filters.append(ChatThread.course_id == course_id)
    if lecture_id is not None:
        filters.append(ChatThread.lecture_id == lecture_id)
    if note_id is not None:
        filters.append(ChatThread.note_id == note_id)

    threads = (
        await db.execute(
            select(ChatThread)
            .where(*filters)
            .order_by(ChatThread.updated_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    counts_rows = (
        await db.execute(
            select(ChatMessage.thread_id, func.count(ChatMessage.id))
            .where(ChatMessage.thread_id.in_([t.id for t in threads] or [-1]))
            .group_by(ChatMessage.thread_id)
        )
    ).all()
    counts = {tid: n for tid, n in counts_rows}

    return [
        ChatThreadSummary(
            id=t.id,
            title=t.title,
            scope=t.scope,
            course_id=t.course_id,
            lecture_id=t.lecture_id,
            note_id=t.note_id,
            message_count=counts.get(t.id, 0),
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in threads
    ]


@router.get("/threads/{thread_id}", response_model=ChatThreadDetail)
async def get_thread(
    thread_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    thread = await _get_thread(db, thread_id, current_user)
    messages = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread.id)
            .order_by(ChatMessage.created_at)
        )
    ).scalars().all()
    return ChatThreadDetail(
        id=thread.id,
        title=thread.title,
        scope=thread.scope,
        course_id=thread.course_id,
        lecture_id=thread.lecture_id,
        note_id=thread.note_id,
        message_count=len(messages),
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
    )


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    thread = await _get_thread(db, thread_id, current_user)
    messages = (
        await db.execute(select(ChatMessage).where(ChatMessage.thread_id == thread.id))
    ).scalars().all()
    for message in messages:
        await db.delete(message)
    await db.delete(thread)
    await db.commit()
    return None


@router.get("/suggestions", response_model=List[str])
async def suggestions(
    note_id: int | None = Query(default=None),
    lecture_id: int | None = Query(default=None),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Seed an empty conversation with questions drawn from the material itself."""
    if note_id is not None:
        note = (
            await db.execute(
                select(GeneratedNote).where(
                    GeneratedNote.id == note_id, GeneratedNote.user_id == current_user.id
                )
            )
        ).scalars().first()
        if note:
            found = llm_service.suggested_questions(note.generated_markdown)
            if found:
                return found

    if lecture_id is not None:
        lecture = (
            await db.execute(
                select(Lecture).where(
                    Lecture.id == lecture_id, Lecture.user_id == current_user.id
                )
            )
        ).scalars().first()
        if lecture:
            name = lecture.title or lecture.filename
            return [
                f"What are the main ideas in {name}?",
                "Which parts of this are most likely to be examined?",
                "Explain the hardest concept here in simpler terms",
            ]

    return [
        "What topics have I covered so far?",
        "Summarise the key ideas across my lectures",
        "What should I revise first?",
    ]
