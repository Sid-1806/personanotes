"""Home-screen data: what to do next, not just a wall of counters."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.evaluation.analytics import calculate_improvement_insights
from app.models.course import Course
from app.models.feedback import EditedNote, GeneratedNote, StyleFeedback
from app.models.historical import HistoricalNote
from app.models.lecture import Lecture
from app.models.style import StyleProfile, StyleProfileVersion
from app.models.user import User

router = APIRouter()


def summarize_profile(profile_json: Dict[str, Any]):
    """Build a compact style summary + an overall personalization score (0-100)
    from a stored StyleProfile JSONB (nested FeatureValue shape).

    Personalization score = the mean confidence across learned style features
    (a real signal of how much the system has learned the user's style).
    """
    if not profile_json:
        return {}, 0

    def _val(key, default=None):
        f = profile_json.get(key)
        return f.get("value", default) if isinstance(f, dict) else default

    confidences = [
        f["confidence"]
        for f in profile_json.values()
        if isinstance(f, dict) and isinstance(f.get("confidence"), (int, float))
    ]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    asl = _val("average_sentence_length")
    if isinstance(asl, (int, float)) and asl > 0:
        sentence_length = "Short" if asl < 12 else ("Long" if asl > 20 else "Medium")
    else:
        sentence_length = "N/A"

    summary = {
        "tone": _val("tone", "N/A"),
        "bullet_preference": _val("bullet_style", "N/A"),
        "sentence_length": sentence_length,
        "confidence": round(avg_conf, 2),
    }
    return summary, round(avg_conf * 100)


def _heading_of(markdown: str) -> str | None:
    for line in (markdown or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            text = stripped.lstrip("#").strip()
            if text:
                return text
    return None


@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    # 1. Recent lectures (real status, not a hardcoded label)
    recent_lectures = (
        await db.execute(
            select(Lecture)
            .where(Lecture.user_id == current_user.id, Lecture.archived.is_(False))
            .order_by(desc(Lecture.uploaded_at))
            .limit(5)
        )
    ).scalars().all()

    # 2. Recent notes
    notes_rows = (
        await db.execute(
            select(GeneratedNote, Lecture.filename, Lecture.title, Course.name)
            .outerjoin(Lecture, GeneratedNote.lecture_id == Lecture.id)
            .outerjoin(Course, GeneratedNote.course_id == Course.id)
            .where(
                GeneratedNote.user_id == current_user.id,
                GeneratedNote.archived.is_(False),
            )
            .order_by(desc(GeneratedNote.created_at))
            .limit(6)
        )
    ).all()
    recent_notes = [
        {
            "id": note.id,
            "title": note.title,
            "note_type": note.note_type,
            "lecture_id": note.lecture_id,
            "lecture_filename": lecture_title or lecture_filename,
            "course_id": note.course_id,
            "course_name": course_name,
            "created_at": note.created_at,
        }
        for note, lecture_filename, lecture_title, course_name in notes_rows
    ]

    # 3. Style summary
    style_profile = (
        await db.execute(
            select(StyleProfile).where(StyleProfile.user_id == current_user.id)
        )
    ).scalars().first()
    style_summary, confidence_score = summarize_profile(
        style_profile.profile_json if style_profile else {}
    )

    # 4. Counters
    counts = {}
    for key, stmt in {
        "total_imported_notes": select(func.count(HistoricalNote.id)).where(
            HistoricalNote.user_id == current_user.id
        ),
        "generated_notes": select(func.count(GeneratedNote.id)).where(
            GeneratedNote.user_id == current_user.id
        ),
        "style_versions": select(func.count(StyleProfileVersion.id)).where(
            StyleProfileVersion.user_id == current_user.id
        ),
        "courses": select(func.count(Course.id)).where(
            Course.user_id == current_user.id, Course.archived.is_(False)
        ),
        "lectures": select(func.count(Lecture.id)).where(
            Lecture.user_id == current_user.id, Lecture.archived.is_(False)
        ),
    }.items():
        counts[key] = (await db.execute(stmt)).scalar() or 0

    counts["edited_notes"] = (
        await db.execute(
            select(func.count(EditedNote.id))
            .join(GeneratedNote)
            .where(GeneratedNote.user_id == current_user.id)
        )
    ).scalar() or 0

    learning_progress = {
        "style_profile_version": style_profile.version if style_profile else 0,
        "total_imported_notes": counts["total_imported_notes"],
        "generated_notes": counts["generated_notes"],
        "edited_notes": counts["edited_notes"],
        "style_versions": counts["style_versions"],
    }

    # 5. Personalization score + trend from the wired evaluation loop.
    feedback_rows = (
        await db.execute(
            select(StyleFeedback.feedback_json, StyleFeedback.created_at)
            .join(GeneratedNote, StyleFeedback.generated_note_id == GeneratedNote.id)
            .where(GeneratedNote.user_id == current_user.id)
            .order_by(StyleFeedback.created_at)
        )
    ).all()

    eval_history = []
    for feedback_json, _created in feedback_rows:
        evaluation = (feedback_json or {}).get("evaluation")
        if isinstance(evaluation, dict) and "personalization_score" in evaluation:
            eval_history.append(evaluation)

    if eval_history:
        personalization_metrics = {
            "current_score": round(eval_history[-1]["personalization_score"]),
            "trend": round(
                eval_history[-1]["personalization_score"]
                - eval_history[0]["personalization_score"]
            ),
            "measured": True,
            "feedback_sessions": len(eval_history),
            "insights": (
                calculate_improvement_insights(eval_history)
                if len(eval_history) >= 2
                else []
            ),
        }
    else:
        personalization_metrics = {
            "current_score": confidence_score,
            "trend": 0,
            "measured": False,
            "feedback_sessions": 0,
            "insights": [],
        }

    # 6. Onboarding state -- a brand-new account needs a path, not empty cards.
    onboarding = {
        "has_style": bool(style_profile) or counts["total_imported_notes"] > 0,
        "has_course": counts["courses"] > 0,
        "has_lecture": counts["lectures"] > 0,
        "has_note": counts["generated_notes"] > 0,
    }
    onboarding["complete"] = all(onboarding.values())

    # 7. What needs attention: failures first, then material with no notes yet.
    needs_attention: List[Dict[str, Any]] = []
    failed = (
        await db.execute(
            select(Lecture)
            .where(
                Lecture.user_id == current_user.id,
                Lecture.ingestion_status == "failed",
                Lecture.archived.is_(False),
            )
            .order_by(desc(Lecture.uploaded_at))
            .limit(3)
        )
    ).scalars().all()
    for lecture in failed:
        needs_attention.append(
            {
                "type": "lecture_failed",
                "lecture_id": lecture.id,
                "course_id": lecture.course_id,
                "title": lecture.title or lecture.filename,
                "detail": lecture.error_message or "Processing failed.",
            }
        )

    noteless = (
        await db.execute(
            select(Lecture)
            .outerjoin(GeneratedNote, GeneratedNote.lecture_id == Lecture.id)
            .where(
                Lecture.user_id == current_user.id,
                Lecture.ingestion_status == "ready",
                Lecture.archived.is_(False),
                GeneratedNote.id.is_(None),
            )
            .order_by(desc(Lecture.uploaded_at))
            .limit(3)
        )
    ).scalars().all()
    for lecture in noteless:
        needs_attention.append(
            {
                "type": "lecture_without_notes",
                "lecture_id": lecture.id,
                "course_id": lecture.course_id,
                "title": lecture.title or lecture.filename,
                "detail": "Ready to turn into notes.",
            }
        )

    # 8. Weak topics: the notes you rewrote most heavily are the ones you were
    #    least happy with -- worth revisiting.
    weak_rows = (
        await db.execute(
            select(StyleFeedback.feedback_json, GeneratedNote.id, GeneratedNote.title,
                   GeneratedNote.generated_markdown, GeneratedNote.course_id)
            .join(GeneratedNote, StyleFeedback.generated_note_id == GeneratedNote.id)
            .where(GeneratedNote.user_id == current_user.id)
            .order_by(desc(StyleFeedback.created_at))
            .limit(25)
        )
    ).all()

    weak_topics = []
    seen_notes: set[int] = set()
    for feedback_json, note_id, title, markdown, course_id in weak_rows:
        evaluation = (feedback_json or {}).get("evaluation") or {}
        score = evaluation.get("personalization_score")
        if score is None or note_id in seen_notes:
            continue
        seen_notes.add(note_id)
        if score < 75:
            weak_topics.append(
                {
                    "note_id": note_id,
                    "title": title or _heading_of(markdown) or f"Note {note_id}",
                    "course_id": course_id,
                    "score": round(score),
                }
            )
    weak_topics.sort(key=lambda w: w["score"])
    weak_topics = weak_topics[:4]

    # 9. Activity feed
    activity_feed = [
        {
            "type": "lecture_uploaded",
            "title": f"Uploaded {lecture.title or lecture.filename}",
            "timestamp": lecture.uploaded_at,
        }
        for lecture in recent_lectures
    ]
    activity_feed += [
        {
            "type": "note_generated",
            "title": f"Generated {note['title'] or 'notes'}",
            "timestamp": note["created_at"],
        }
        for note in recent_notes
    ]
    historical = (
        await db.execute(
            select(HistoricalNote)
            .where(HistoricalNote.user_id == current_user.id)
            .order_by(desc(HistoricalNote.created_at))
            .limit(5)
        )
    ).scalars().all()
    activity_feed += [
        {
            "type": "historical_imported",
            "title": f"Imported history: {item.title}",
            "timestamp": item.created_at,
        }
        for item in historical
    ]
    activity_feed = sorted(
        [a for a in activity_feed if a["timestamp"] is not None],
        key=lambda a: a["timestamp"],
        reverse=True,
    )[:10]

    return {
        "recent_lectures": [
            {
                "id": lecture.id,
                "filename": lecture.filename,
                "title": lecture.title,
                "course_id": lecture.course_id,
                "uploaded_at": lecture.uploaded_at,
                # The real pipeline state; this used to be hardcoded to "Ready".
                "status": lecture.ingestion_status,
                "error_message": lecture.error_message,
                "chunk_count": lecture.chunk_count,
            }
            for lecture in recent_lectures
        ],
        "recent_notes": recent_notes,
        "style_summary": style_summary,
        "learning_progress": learning_progress,
        "personalization_metrics": personalization_metrics,
        "onboarding": onboarding,
        "needs_attention": needs_attention,
        "weak_topics": weak_topics,
        "activity_feed": activity_feed,
    }
