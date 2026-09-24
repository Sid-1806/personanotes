"""Semantic search across the user's lectures and their own notes.

The retrieval engine already existed; it was only ever reachable from inside
generation. Exposing it directly is the cheapest way to make the corpus useful,
and it degrades to plain text matching when the vector store is unavailable
rather than silently returning nothing.
"""

import logging
from typing import Any, List

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.course import Course
from app.models.feedback import GeneratedNote
from app.models.lecture import Lecture
from app.models.user import User
from app.schemas.search import SearchExcerpt, SearchGroup, SearchResponse, TitleMatch
from app.services import llm_service
from app.services.vector_db import KIND_LECTURE, KIND_NOTE

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    scope: str = Query("all", pattern="^(all|lectures|notes)$"),
    course_id: int | None = Query(default=None),
    lecture_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Search lecture material and generated notes, grouped by source document."""
    query = q.strip()
    kind = {"lectures": KIND_LECTURE, "notes": KIND_NOTE}.get(scope)

    try:
        hits = await run_in_threadpool(
            llm_service.search_chunks,
            query,
            current_user.id,
            limit,
            lecture_id,
            course_id,
            None,
            kind,
            True,  # raise so an outage is distinguishable from an empty result
        )
    except Exception as exc:
        # The index is unreachable. Fall back to plain text matching and say so,
        # rather than silently returning worse results.
        logger.warning("Vector search unavailable, falling back to text: %s", exc)
        groups = await _text_fallback(db, current_user, query, scope, course_id)
        return SearchResponse(
            query=query, scope=scope, groups=groups, total_hits=len(groups), degraded=True
        )

    if not hits:
        # Genuinely nothing matched semantically. Titles might still match, and
        # that is not a degraded state -- it's just a different kind of hit.
        groups = await _text_fallback(db, current_user, query, scope, course_id)
        return SearchResponse(
            query=query, scope=scope, groups=groups, total_hits=len(groups), degraded=False
        )

    lecture_ids = {h["lecture_id"] for h in hits if h.get("lecture_id")}
    note_ids = {h["note_id"] for h in hits if h.get("note_id")}
    lecture_rows = (
        await db.execute(
            select(Lecture.id, Lecture.title, Lecture.filename, Lecture.course_id).where(
                Lecture.id.in_(lecture_ids or {-1})
            )
        )
    ).all()
    note_rows = (
        await db.execute(
            select(GeneratedNote.id, GeneratedNote.title, GeneratedNote.course_id,
                   GeneratedNote.lecture_id).where(GeneratedNote.id.in_(note_ids or {-1}))
        )
    ).all()
    lectures = {r[0]: r for r in lecture_rows}
    notes = {r[0]: r for r in note_rows}
    course_names = await _course_names(
        db,
        {r[3] for r in lecture_rows if r[3]} | {r[2] for r in note_rows if r[2]},
    )

    grouped: dict[tuple[str, int], SearchGroup] = {}
    for hit in hits:
        if hit.get("kind") == KIND_NOTE and hit.get("note_id") in notes:
            nid, title, cid, lid = notes[hit["note_id"]]
            key = ("note", nid)
            group = grouped.setdefault(
                key,
                SearchGroup(
                    kind="note",
                    source_id=nid,
                    title=title or f"Note {nid}",
                    course_id=cid,
                    course_name=course_names.get(cid),
                    lecture_id=lid,
                ),
            )
        elif hit.get("lecture_id") in lectures:
            lid, title, filename, cid = lectures[hit["lecture_id"]]
            key = ("lecture", lid)
            group = grouped.setdefault(
                key,
                SearchGroup(
                    kind="lecture",
                    source_id=lid,
                    title=title or filename,
                    course_id=cid,
                    course_name=course_names.get(cid),
                    lecture_id=lid,
                ),
            )
        else:
            continue

        group.excerpts.append(
            SearchExcerpt(text=hit.get("text", "")[:500], page=hit.get("page"), score=hit.get("score"))
        )
        score = hit.get("score")
        if score is not None and (group.best_score is None or score > group.best_score):
            group.best_score = score

    ordered = sorted(grouped.values(), key=lambda g: g.best_score or 0, reverse=True)
    return SearchResponse(
        query=query, scope=scope, groups=ordered, total_hits=len(hits), degraded=False
    )


async def _course_names(db: AsyncSession, course_ids: set[int]) -> dict[int, str]:
    if not course_ids:
        return {}
    rows = (
        await db.execute(select(Course.id, Course.name).where(Course.id.in_(course_ids)))
    ).all()
    return {cid: name for cid, name in rows}


async def _text_fallback(
    db: AsyncSession, user: User, query: str, scope: str, course_id: int | None
) -> List[SearchGroup]:
    """Plain ILIKE matching over note bodies and lecture names."""
    pattern = f"%{query}%"
    groups: List[SearchGroup] = []

    if scope in ("all", "notes"):
        filters = [
            GeneratedNote.user_id == user.id,
            GeneratedNote.archived.is_(False),
            or_(
                GeneratedNote.title.ilike(pattern),
                GeneratedNote.generated_markdown.ilike(pattern),
            ),
        ]
        if course_id is not None:
            filters.append(GeneratedNote.course_id == course_id)
        rows = (
            await db.execute(
                select(GeneratedNote).where(*filters).order_by(
                    GeneratedNote.created_at.desc()
                ).limit(10)
            )
        ).scalars().all()
        names = await _course_names(db, {r.course_id for r in rows if r.course_id})
        for note in rows:
            groups.append(
                SearchGroup(
                    kind="note",
                    source_id=note.id,
                    title=note.title or f"Note {note.id}",
                    course_id=note.course_id,
                    course_name=names.get(note.course_id),
                    lecture_id=note.lecture_id,
                    excerpts=[SearchExcerpt(text=_snippet(note.generated_markdown, query))],
                )
            )

    if scope in ("all", "lectures"):
        filters = [
            Lecture.user_id == user.id,
            Lecture.archived.is_(False),
            or_(Lecture.title.ilike(pattern), Lecture.filename.ilike(pattern)),
        ]
        if course_id is not None:
            filters.append(Lecture.course_id == course_id)
        rows = (
            await db.execute(select(Lecture).where(*filters).limit(10))
        ).scalars().all()
        names = await _course_names(db, {r.course_id for r in rows if r.course_id})
        for lecture in rows:
            groups.append(
                SearchGroup(
                    kind="lecture",
                    source_id=lecture.id,
                    title=lecture.title or lecture.filename,
                    course_id=lecture.course_id,
                    course_name=names.get(lecture.course_id),
                    lecture_id=lecture.id,
                    excerpts=[],
                )
            )

    return groups


def _snippet(text: str, query: str, width: int = 240) -> str:
    """A window of text around the first match, so the hit is visible."""
    lowered = (text or "").lower()
    index = lowered.find(query.lower())
    if index < 0:
        return (text or "")[:width]
    start = max(0, index - width // 3)
    return ("…" if start else "") + text[start : start + width].strip() + "…"


@router.get("/jump", response_model=List[TitleMatch])
async def jump(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=8, ge=1, le=20),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Title-only matches for the command palette's "jump to" section."""
    pattern = f"%{q.strip()}%"
    matches: List[TitleMatch] = []

    courses = (
        await db.execute(
            select(Course)
            .where(Course.user_id == current_user.id, Course.name.ilike(pattern))
            .limit(limit)
        )
    ).scalars().all()
    matches += [
        TitleMatch(kind="course", id=c.id, title=c.name, subtitle=c.code, created_at=c.created_at)
        for c in courses
    ]

    lectures = (
        await db.execute(
            select(Lecture)
            .where(
                Lecture.user_id == current_user.id,
                Lecture.archived.is_(False),
                or_(Lecture.title.ilike(pattern), Lecture.filename.ilike(pattern)),
            )
            .order_by(Lecture.uploaded_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    matches += [
        TitleMatch(
            kind="lecture",
            id=l.id,
            title=l.title or l.filename,
            subtitle=l.ingestion_status,
            created_at=l.uploaded_at,
        )
        for l in lectures
    ]

    notes = (
        await db.execute(
            select(GeneratedNote)
            .where(
                GeneratedNote.user_id == current_user.id,
                GeneratedNote.archived.is_(False),
                GeneratedNote.title.ilike(pattern),
            )
            .order_by(GeneratedNote.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    matches += [
        TitleMatch(
            kind="note",
            id=n.id,
            title=n.title or f"Note {n.id}",
            subtitle=n.note_type,
            created_at=n.created_at,
        )
        for n in notes
    ]

    return matches[: limit * 2]
