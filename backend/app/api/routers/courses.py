"""Courses: the organising unit for lectures and the notes generated from them."""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select

from app.api import deps
from app.models.chat import ChatThread
from app.models.course import Course
from app.models.feedback import GeneratedNote
from app.models.lecture import Lecture
from app.models.user import User
from app.schemas.course import CourseCreate, CourseResponse, CourseUpdate
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

DEFAULT_COURSE_NAME = "Uncategorized"


async def get_owned_course(db: AsyncSession, course_id: int, user: User) -> Course:
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    course = result.scalars().first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


async def ensure_default_course(db: AsyncSession, user: User) -> Course:
    """Return (creating if needed) the catch-all course for uncategorised uploads.

    Uploading should never be blocked on first creating a course, so anything
    without an explicit course lands here.
    """
    result = await db.execute(
        select(Course).where(
            Course.user_id == user.id, Course.name == DEFAULT_COURSE_NAME
        )
    )
    course = result.scalars().first()
    if course is not None:
        return course

    course = Course(user_id=user.id, name=DEFAULT_COURSE_NAME, color="slate")
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


async def _course_rows(db: AsyncSession, user: User, include_archived: bool):
    """Courses with their lecture/note counts in one pass."""
    lecture_stats = (
        select(
            Lecture.course_id.label("course_id"),
            func.count(Lecture.id).label("lecture_count"),
            func.sum(case((Lecture.ingestion_status == "ready", 1), else_=0)).label("ready"),
            func.sum(
                case(
                    (Lecture.ingestion_status.in_(["pending", "processing"]), 1),
                    else_=0,
                )
            ).label("processing"),
            func.sum(case((Lecture.ingestion_status == "failed", 1), else_=0)).label("failed"),
            func.max(Lecture.uploaded_at).label("last_upload"),
        )
        .where(Lecture.user_id == user.id, Lecture.archived.is_(False))
        .group_by(Lecture.course_id)
        .subquery()
    )

    note_stats = (
        select(
            GeneratedNote.course_id.label("course_id"),
            func.count(GeneratedNote.id).label("note_count"),
            func.max(GeneratedNote.created_at).label("last_note"),
        )
        .where(GeneratedNote.user_id == user.id, GeneratedNote.archived.is_(False))
        .group_by(GeneratedNote.course_id)
        .subquery()
    )

    stmt = (
        select(
            Course,
            func.coalesce(lecture_stats.c.lecture_count, 0),
            func.coalesce(lecture_stats.c.ready, 0),
            func.coalesce(lecture_stats.c.processing, 0),
            func.coalesce(lecture_stats.c.failed, 0),
            func.coalesce(note_stats.c.note_count, 0),
            lecture_stats.c.last_upload,
            note_stats.c.last_note,
        )
        .outerjoin(lecture_stats, lecture_stats.c.course_id == Course.id)
        .outerjoin(note_stats, note_stats.c.course_id == Course.id)
        .where(Course.user_id == user.id)
        .order_by(Course.archived, Course.name)
    )
    if not include_archived:
        stmt = stmt.where(Course.archived.is_(False))

    return (await db.execute(stmt)).all()


def _to_response(row) -> CourseResponse:
    (course, lectures, ready, processing, failed, notes, last_upload, last_note) = row
    stamps = [s for s in (last_upload, last_note) if s is not None]
    return CourseResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        color=course.color,
        archived=course.archived,
        created_at=course.created_at,
        lecture_count=int(lectures or 0),
        ready_lecture_count=int(ready or 0),
        processing_lecture_count=int(processing or 0),
        failed_lecture_count=int(failed or 0),
        note_count=int(notes or 0),
        last_activity_at=max(stamps) if stamps else course.created_at,
    )


@router.get("/", response_model=List[CourseResponse])
async def list_courses(
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """All of the user's courses with lecture and note counts."""
    rows = await _course_rows(db, current_user, include_archived)
    return [_to_response(row) for row in rows]


@router.post("/", response_model=CourseResponse, status_code=201)
async def create_course(
    payload: CourseCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    course = Course(
        user_id=current_user.id,
        name=payload.name.strip(),
        code=(payload.code or "").strip() or None,
        color=payload.color,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return CourseResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        color=course.color,
        archived=course.archived,
        created_at=course.created_at,
    )


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    await get_owned_course(db, course_id, current_user)
    rows = await _course_rows(db, current_user, include_archived=True)
    for row in rows:
        if row[0].id == course_id:
            return _to_response(row)
    raise HTTPException(status_code=404, detail="Course not found")


@router.patch("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    course = await get_owned_course(db, course_id, current_user)
    if payload.name is not None:
        course.name = payload.name.strip()
    if payload.code is not None:
        course.code = payload.code.strip() or None
    if payload.color is not None:
        course.color = payload.color
    if payload.archived is not None:
        course.archived = payload.archived
    await db.commit()
    await db.refresh(course)
    return CourseResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        color=course.color,
        archived=course.archived,
        created_at=course.created_at,
    )


@router.delete("/{course_id}", status_code=204)
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Delete a course, moving its lectures and notes to the default course.

    Deleting a subject folder should not destroy the material inside it; the
    user asked to remove the grouping, not their coursework.
    """
    course = await get_owned_course(db, course_id, current_user)
    fallback = await ensure_default_course(db, current_user)
    if fallback.id == course.id:
        raise HTTPException(
            status_code=400,
            detail="The default course can't be deleted. Rename it instead.",
        )

    for model in (Lecture, GeneratedNote):
        rows = (
            await db.execute(select(model).where(model.course_id == course.id))
        ).scalars().all()
        for row in rows:
            row.course_id = fallback.id

    # Conversations scoped to this course move with it. Without this the
    # foreign key blocks the delete outright.
    threads = (
        await db.execute(select(ChatThread).where(ChatThread.course_id == course.id))
    ).scalars().all()
    for thread in threads:
        thread.course_id = fallback.id

    await db.flush()
    await db.delete(course)
    await db.commit()
    return None
