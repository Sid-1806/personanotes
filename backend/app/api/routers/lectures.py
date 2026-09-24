import logging
import os
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.routers.courses import ensure_default_course, get_owned_course
from app.models.chat import ChatThread
from app.models.course import Course
from app.models.feedback import EditedNote, GeneratedNote, StyleFeedback
from app.models.lecture import Lecture
from app.models.user import User
from app.schemas.lecture import LectureResponse, LectureTextResponse, LectureUpdate
from app.schemas.note import NoteSummary
from app.services import lecture_service
from app.services.ingestion import process_lecture
from app.services.vector_db import delete_lecture_points

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_owned_lecture(db: AsyncSession, lecture_id: int, user: User) -> Lecture:
    result = await db.execute(
        select(Lecture).where(Lecture.id == lecture_id, Lecture.user_id == user.id)
    )
    lecture = result.scalars().first()
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return lecture


async def _decorate(db: AsyncSession, lectures: List[Lecture]) -> List[LectureResponse]:
    """Attach course name and note count so list rows are self-explanatory."""
    if not lectures:
        return []

    course_ids = {l.course_id for l in lectures if l.course_id}
    names: dict[int, str] = {}
    if course_ids:
        rows = (
            await db.execute(select(Course.id, Course.name).where(Course.id.in_(course_ids)))
        ).all()
        names = {cid: name for cid, name in rows}

    counts_rows = (
        await db.execute(
            select(GeneratedNote.lecture_id, func.count(GeneratedNote.id))
            .where(
                GeneratedNote.lecture_id.in_([l.id for l in lectures]),
                GeneratedNote.archived.is_(False),
            )
            .group_by(GeneratedNote.lecture_id)
        )
    ).all()
    counts = {lid: n for lid, n in counts_rows}

    return [
        LectureResponse(
            id=l.id,
            user_id=l.user_id,
            filename=l.filename,
            filetype=l.filetype,
            uploaded_at=l.uploaded_at,
            course_id=l.course_id,
            course_name=names.get(l.course_id),
            title=l.title,
            ingestion_status=l.ingestion_status,
            error_message=l.error_message,
            chunk_count=l.chunk_count,
            page_count=l.page_count,
            note_count=counts.get(l.id, 0),
        )
        for l in lectures
    ]


def _schedule_ingestion(
    background_tasks: BackgroundTasks, lecture: Lecture, user_id: int
) -> None:
    background_tasks.add_task(
        process_lecture,
        lecture_id=lecture.id,
        user_id=user_id,
        filepath=lecture.filepath,
        filetype=lecture.filetype,
        course_id=lecture.course_id,
    )


@router.post("/upload", response_model=List[LectureResponse])
async def upload_lectures(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    course_id: int | None = Query(default=None),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Upload one or more lecture files and schedule background indexing.

    Accepts a list so a student can add a whole week at once. Files land in the
    named course, or in the default course when none is given.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    if course_id is not None:
        course = await get_owned_course(db, course_id, current_user)
    else:
        course = await ensure_default_course(db, current_user)

    created: List[Lecture] = []
    for file in files:
        if not file.filename:
            continue
        lecture = await lecture_service.save_lecture(
            db, file, current_user, course_id=course.id
        )
        created.append(lecture)

    if not created:
        raise HTTPException(status_code=400, detail="No valid files were uploaded.")

    for lecture in created:
        _schedule_ingestion(background_tasks, lecture, current_user.id)

    return await _decorate(db, created)


@router.get("/", response_model=List[LectureResponse])
async def read_lectures(
    course_id: int | None = Query(default=None),
    include_archived: bool = Query(default=False),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """All lectures the user owns, newest first, optionally scoped to a course."""
    stmt = select(Lecture).where(Lecture.user_id == current_user.id)
    if course_id is not None:
        stmt = stmt.where(Lecture.course_id == course_id)
    if not include_archived:
        stmt = stmt.where(Lecture.archived.is_(False))
    stmt = stmt.order_by(Lecture.uploaded_at.desc())

    lectures = (await db.execute(stmt)).scalars().all()
    return await _decorate(db, list(lectures))


@router.get("/{id}", response_model=LectureResponse)
async def read_lecture(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Fetch a single lecture owned by the current user (with processing status)."""
    lecture = await get_owned_lecture(db, id, current_user)
    return (await _decorate(db, [lecture]))[0]


@router.patch("/{id}", response_model=LectureResponse)
async def update_lecture(
    id: int,
    payload: LectureUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Rename a lecture, or move it to a different course."""
    lecture = await get_owned_lecture(db, id, current_user)
    if payload.title is not None:
        lecture.title = payload.title.strip() or None
    if payload.course_id is not None:
        await get_owned_course(db, payload.course_id, current_user)
        lecture.course_id = payload.course_id
    await db.commit()
    await db.refresh(lecture)
    return (await _decorate(db, [lecture]))[0]


@router.post("/{id}/retry", response_model=LectureResponse)
async def retry_lecture(
    id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Re-run ingestion for a lecture that failed or was interrupted."""
    lecture = await get_owned_lecture(db, id, current_user)
    if lecture.ingestion_status == "processing":
        raise HTTPException(status_code=409, detail="This lecture is already processing.")
    if not os.path.exists(lecture.filepath):
        raise HTTPException(
            status_code=409,
            detail="The original file is no longer on the server. Re-upload it instead.",
        )

    # Drop any partial index from the failed run so a retry can't leave
    # duplicate chunks behind.
    delete_lecture_points(lecture.id, current_user.id)

    lecture.ingestion_status = "pending"
    lecture.error_message = None
    lecture.chunk_count = 0
    await db.commit()
    await db.refresh(lecture)

    _schedule_ingestion(background_tasks, lecture, current_user.id)
    return (await _decorate(db, [lecture]))[0]


@router.get("/{id}/text", response_model=LectureTextResponse)
async def read_lecture_text(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Preview what the parser actually extracted, so a bad parse is diagnosable."""
    from fastapi.concurrency import run_in_threadpool

    from app.services.document_parser import parse_document

    lecture = await get_owned_lecture(db, id, current_user)
    if not os.path.exists(lecture.filepath):
        raise HTTPException(status_code=404, detail="The source file is no longer available.")

    parsed = await run_in_threadpool(parse_document, lecture.filepath, lecture.filetype)
    limit = 20000
    text = parsed.text or ""
    return LectureTextResponse(
        id=lecture.id,
        page_count=lecture.page_count or len(parsed.pages),
        chunk_count=lecture.chunk_count,
        text=text[:limit],
        truncated=len(text) > limit,
    )


@router.get("/{id}/notes", response_model=List[NoteSummary])
async def read_lecture_notes(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Every note generated from this lecture."""
    from app.api.routers.notes import summarize_notes

    lecture = await get_owned_lecture(db, id, current_user)
    notes = (
        await db.execute(
            select(GeneratedNote)
            .where(
                GeneratedNote.lecture_id == lecture.id,
                GeneratedNote.user_id == current_user.id,
                GeneratedNote.archived.is_(False),
            )
            .order_by(GeneratedNote.created_at.desc())
        )
    ).scalars().all()
    return await summarize_notes(db, list(notes))


@router.delete("/{id}", status_code=204)
async def delete_lecture(
    id: int,
    keep_notes: bool = Query(
        default=True,
        description="Keep notes generated from this lecture (they lose their source link).",
    ),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Delete a lecture, its vectors, and optionally the notes made from it.

    The vector points must go with it — an orphaned index would keep feeding
    deleted material into future generations.
    """
    lecture = await get_owned_lecture(db, id, current_user)

    notes = (
        await db.execute(
            select(GeneratedNote).where(GeneratedNote.lecture_id == lecture.id)
        )
    ).scalars().all()

    if keep_notes:
        for note in notes:
            note.lecture_id = None
    else:
        note_ids = [n.id for n in notes]
        if note_ids:
            from app.services.vector_db import delete_note_points

            for nid in note_ids:
                delete_note_points(nid, current_user.id)
            for model in (EditedNote, StyleFeedback):
                rows = (
                    await db.execute(
                        select(model).where(model.generated_note_id.in_(note_ids))
                    )
                ).scalars().all()
                for row in rows:
                    await db.delete(row)
            await db.flush()
            # Break parent links before deleting, so the self-FK can't block it.
            children = (
                await db.execute(
                    select(GeneratedNote).where(
                        GeneratedNote.parent_note_id.in_(note_ids)
                    )
                )
            ).scalars().all()
            for child in children:
                child.parent_note_id = None
            note_threads = (
                await db.execute(
                    select(ChatThread).where(ChatThread.note_id.in_(note_ids))
                )
            ).scalars().all()
            for thread in note_threads:
                thread.note_id = None
                thread.scope = "all" if thread.scope == "note" else thread.scope
            await db.flush()
            for note in notes:
                await db.delete(note)

    delete_lecture_points(lecture.id, current_user.id)

    # Conversations that were scoped to this lecture survive as general threads
    # rather than blocking the delete on a foreign key.
    threads = (
        await db.execute(
            select(ChatThread).where(ChatThread.lecture_id == lecture.id)
        )
    ).scalars().all()
    for thread in threads:
        thread.lecture_id = None
        thread.scope = "all" if thread.scope == "lecture" else thread.scope
    await db.flush()

    try:
        if lecture.filepath and os.path.exists(lecture.filepath):
            os.remove(lecture.filepath)
    except OSError as exc:  # the DB row is the source of truth; log and continue
        logger.warning("Could not remove file for lecture %s: %s", lecture.id, exc)

    await db.delete(lecture)
    await db.commit()
    return None
