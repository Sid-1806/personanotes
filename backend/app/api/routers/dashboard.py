from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func

from app.api import deps
from app.models.user import User
from app.models.lecture import Lecture
from app.models.feedback import GeneratedNote, EditedNote, StyleFeedback
from app.models.style import StyleProfile, StyleProfileVersion
from app.models.historical import HistoricalNote
from app.evaluation.analytics import calculate_improvement_insights

router = APIRouter()


def summarize_profile(profile_json: Dict[str, Any]):
    """Build a compact style summary + an overall personalization score (0-100)
    from a stored StyleProfile JSONB (nested FeatureValue shape).

    Personalization score = the mean confidence across learned style features
    (a real signal of how much the system has learned the user's style),
    replacing the previously hardcoded value.
    """
    if not profile_json:
        return {}, 0

    def _val(key, default=None):
        f = profile_json.get(key)
        return f.get("value", default) if isinstance(f, dict) else default

    confidences = [
        f["confidence"] for f in profile_json.values()
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


@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    # 1. Recent Lectures
    lectures_stmt = (
        select(Lecture)
        .where(Lecture.user_id == current_user.id)
        .order_by(desc(Lecture.uploaded_at))
        .limit(5)
    )
    lectures_res = await db.execute(lectures_stmt)
    recent_lectures = lectures_res.scalars().all()

    # 2. Recent Notes
    notes_stmt = (
        select(GeneratedNote, Lecture.filename)
        .outerjoin(Lecture, GeneratedNote.lecture_id == Lecture.id)
        .where(GeneratedNote.user_id == current_user.id)
        .order_by(desc(GeneratedNote.created_at))
        .limit(5)
    )
    notes_res = await db.execute(notes_stmt)
    recent_notes = []
    for note, lecture_filename in notes_res.all():
        recent_notes.append(
            {
                "id": note.id,
                "lecture_id": note.lecture_id,
                "lecture_filename": lecture_filename,
                "created_at": note.created_at,
            }
        )

    # 3. Style Summary
    style_stmt = select(StyleProfile).where(StyleProfile.user_id == current_user.id)
    style_res = await db.execute(style_stmt)
    style_profile = style_res.scalars().first()

    style_summary, personalization_score = summarize_profile(
        style_profile.profile_json if style_profile else {}
    )

    # 4. Learning Progress
    historical_count = await db.execute(
        select(func.count(HistoricalNote.id)).where(
            HistoricalNote.user_id == current_user.id
        )
    )
    generated_count = await db.execute(
        select(func.count(GeneratedNote.id)).where(
            GeneratedNote.user_id == current_user.id
        )
    )

    edited_stmt = (
        select(func.count(EditedNote.id))
        .join(GeneratedNote)
        .where(GeneratedNote.user_id == current_user.id)
    )
    edited_count = await db.execute(edited_stmt)

    style_versions_count = await db.execute(
        select(func.count(StyleProfileVersion.id)).where(
            StyleProfileVersion.user_id == current_user.id
        )
    )

    learning_progress = {
        "style_profile_version": style_profile.version if style_profile else 0,
        "total_imported_notes": historical_count.scalar() or 0,
        "generated_notes": generated_count.scalar() or 0,
        "edited_notes": edited_count.scalar() or 0,
        "style_versions": style_versions_count.scalar() or 0,
    }

    # 5. Personalization score + trend from the wired evaluation loop.
    #    Each feedback event stores an evaluate_generation() result in
    #    StyleFeedback.feedback_json["evaluation"]; we read that time-ordered
    #    history to report the latest score and whether it is improving.
    fb_stmt = (
        select(StyleFeedback.feedback_json, StyleFeedback.created_at)
        .join(GeneratedNote, StyleFeedback.generated_note_id == GeneratedNote.id)
        .where(GeneratedNote.user_id == current_user.id)
        .order_by(StyleFeedback.created_at)
    )
    fb_res = await db.execute(fb_stmt)
    eval_history = []
    for fjson, _created in fb_res.all():
        ev = (fjson or {}).get("evaluation")
        if isinstance(ev, dict) and "personalization_score" in ev:
            eval_history.append(ev)

    if eval_history:
        current = round(eval_history[-1]["personalization_score"])
        trend = round(
            eval_history[-1]["personalization_score"]
            - eval_history[0]["personalization_score"]
        )
        insights = (
            calculate_improvement_insights(eval_history)
            if len(eval_history) >= 2
            else []
        )
        personalization_metrics = {
            "current_score": current,
            "trend": trend,
            "measured": True,
            "feedback_sessions": len(eval_history),
            "insights": insights,
        }
    else:
        # No feedback yet -> fall back to the mean-confidence proxy.
        personalization_metrics = {
            "current_score": personalization_score,
            "trend": 0,
            "measured": False,
            "feedback_sessions": 0,
            "insights": [],
        }

    # 6. Activity Feed
    activity_feed = []

    for lec in recent_lectures:
        activity_feed.append(
            {
                "type": "lecture_uploaded",
                "title": f"Uploaded {lec.filename}",
                "timestamp": lec.uploaded_at,
            }
        )

    for note in recent_notes:
        activity_feed.append(
            {
                "type": "note_generated",
                "title": f"Generated notes for {note['lecture_filename'] or 'Lecture'}",
                "timestamp": note["created_at"],
            }
        )

    hist_stmt = (
        select(HistoricalNote)
        .where(HistoricalNote.user_id == current_user.id)
        .order_by(desc(HistoricalNote.created_at))
        .limit(5)
    )
    hist_res = await db.execute(hist_stmt)
    for hist in hist_res.scalars().all():
        activity_feed.append(
            {
                "type": "historical_imported",
                "title": f"Imported history: {hist.title}",
                "timestamp": hist.created_at,
            }
        )

    activity_feed.sort(key=lambda x: x["timestamp"], reverse=True)
    activity_feed = activity_feed[:10]

    return {
        "recent_lectures": [
            {
                "id": l.id,
                "filename": l.filename,
                "uploaded_at": l.uploaded_at,
                "status": "Ready",
            }
            for l in recent_lectures
        ],
        "recent_notes": recent_notes,
        "style_summary": style_summary,
        "learning_progress": learning_progress,
        "personalization_metrics": personalization_metrics,
        "activity_feed": activity_feed,
    }
