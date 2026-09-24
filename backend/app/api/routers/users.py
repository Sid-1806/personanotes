import logging
import os
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import create_access_token
from app.models.chat import ChatMessage, ChatThread
from app.models.course import Course
from app.models.feedback import EditedNote, GeneratedNote, StyleFeedback
from app.models.historical import HistoricalNote
from app.models.lecture import Lecture
from app.models.style import StyleProfile, StyleProfileVersion
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserResponse
from app.services.vector_db import delete_user_points

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: User = Depends(deps.get_current_user)) -> Any:
    """
    Retrieve the profile of the currently authenticated user.

    Args:
        current_user (User): The authenticated user instance injected by dependencies.

    Returns:
        Any: The user data serialized by UserResponse.
    """
    return current_user


@router.post("/me/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(deps.get_current_user)) -> Any:
    """Exchange a still-valid token for a fresh one.

    Lets the client extend a session in the background rather than dropping
    someone onto the login page in the middle of writing.
    """
    return Token(
        access_token=create_access_token(subject=current_user.id), token_type="bearer"
    )


@router.get("/me/export")
async def export_everything(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Download every note as a single markdown file.

    Coursework someone can't get back out isn't really theirs.
    """
    from app.api.routers.notes import note_body

    notes = (
        await db.execute(
            select(GeneratedNote)
            .where(GeneratedNote.user_id == current_user.id)
            .order_by(GeneratedNote.created_at)
        )
    ).scalars().all()

    course_rows = (
        await db.execute(
            select(Course.id, Course.name).where(Course.user_id == current_user.id)
        )
    ).all()
    courses = {cid: name for cid, name in course_rows}

    parts = [f"# PersonaNotes export — {current_user.name}", ""]
    for note in notes:
        body = await note_body(db, note)
        heading = note.title or f"Note {note.id}"
        meta = [note.created_at.strftime("%Y-%m-%d") if note.created_at else "", note.note_type]
        if note.course_id and note.course_id in courses:
            meta.append(courses[note.course_id])
        parts += [f"\n\n---\n\n## {heading}", f"*{' · '.join(m for m in meta if m)}*", "", body]

    return PlainTextResponse(
        "\n".join(parts),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="personanotes-export.md"'},
    )


@router.delete("/me", status_code=204)
async def delete_account(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Permanently delete the account and everything in it.

    Ordered so foreign keys never block the delete: chat, then note children,
    then notes, then lectures, courses, style and finally the user.
    """
    user_id = current_user.id

    threads = (
        await db.execute(select(ChatThread).where(ChatThread.user_id == user_id))
    ).scalars().all()
    thread_ids = [t.id for t in threads]
    if thread_ids:
        messages = (
            await db.execute(
                select(ChatMessage).where(ChatMessage.thread_id.in_(thread_ids))
            )
        ).scalars().all()
        for message in messages:
            await db.delete(message)
    for thread in threads:
        await db.delete(thread)
    await db.flush()

    notes = (
        await db.execute(
            select(GeneratedNote).where(GeneratedNote.user_id == user_id)
        )
    ).scalars().all()
    note_ids = [n.id for n in notes]
    if note_ids:
        for model in (EditedNote, StyleFeedback):
            rows = (
                await db.execute(
                    select(model).where(model.generated_note_id.in_(note_ids))
                )
            ).scalars().all()
            for row in rows:
                await db.delete(row)
        await db.flush()
        for note in notes:
            note.parent_note_id = None
        await db.flush()
        for note in notes:
            await db.delete(note)
    await db.flush()

    lectures = (
        await db.execute(select(Lecture).where(Lecture.user_id == user_id))
    ).scalars().all()
    historical = (
        await db.execute(
            select(HistoricalNote).where(HistoricalNote.user_id == user_id)
        )
    ).scalars().all()

    for record in (*lectures, *historical):
        try:
            if record.filepath and os.path.exists(record.filepath):
                os.remove(record.filepath)
        except OSError as exc:
            logger.warning("Could not remove file during account deletion: %s", exc)
        await db.delete(record)
    await db.flush()

    for model in (Course, StyleProfile, StyleProfileVersion):
        rows = (
            await db.execute(select(model).where(model.user_id == user_id))
        ).scalars().all()
        for row in rows:
            await db.delete(row)
    await db.flush()

    delete_user_points(user_id)

    await db.delete(current_user)
    await db.commit()
    return None
