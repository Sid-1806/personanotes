"""The style profile: what PersonaNotes has learned, and the user's control over it.

The profile used to be a read-only report. The endpoints that let someone
correct it existed but nothing called them; now overriding, pinning and
resetting are first-class, and the learning rule honours a pin.
"""

import logging
import os
import shutil
import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import FileProcessingError
from app.models.feedback import EditedNote, GeneratedNote, StyleFeedback
from app.models.historical import HistoricalNote
from app.models.style import StyleProfile, StyleProfileVersion
from app.models.user import User
from app.services.document_parser import parse_document
from app.style.analyzer import analyze_style_from_document
from app.style.learning import pin_value, unpin
from app.style.schema import (
    AttributeOverrideRequest,
    StyleProfileSchema,
    StyleResponse,
    UpdateStyleRequest,
)
from app.style.updater import merge_profiles

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = "uploads/style_analysis"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _get_profile(db: AsyncSession, user: User) -> StyleProfile | None:
    result = await db.execute(
        select(StyleProfile).where(StyleProfile.user_id == user.id)
    )
    return result.scalars().first()


_TRUTHY = {"true", "yes", "y", "1", "on"}
_FALSY = {"false", "no", "n", "0", "off", ""}


def _coerce_attribute_value(feature: str, current, incoming):
    """Coerce a hand-set value to the type the attribute already holds.

    Storing the wrong type would make ``StyleProfileSchema`` fail to parse on
    the next read, and the parse failure falls back to a *default* profile —
    meaning one bad override could silently wipe everything the system learned.
    So anything that can't be coerced is refused with a 400 rather than written.
    """
    try:
        # bool before int/float: bool is a subclass of int, and bool("false")
        # is True, which would store the opposite of what was asked for.
        if isinstance(current, bool):
            if isinstance(incoming, bool):
                return incoming
            text = str(incoming).strip().lower()
            if text in _TRUTHY:
                return True
            if text in _FALSY:
                return False
            raise ValueError(f"{incoming!r} is not a yes/no value")

        if isinstance(current, (int, float)):
            return float(incoming)

        if isinstance(current, str):
            return str(incoming)

        if isinstance(current, list):
            if isinstance(incoming, list):
                return [str(v).strip() for v in incoming if str(v).strip()]
            return [v.strip() for v in str(incoming).split(",") if v.strip()]

        if isinstance(current, dict):
            # A structured field can only be replaced by a structure. Accepting
            # a string here used to raise an unhandled 500.
            if not isinstance(incoming, dict):
                raise ValueError("expected an object")
            return incoming

        return incoming
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"'{incoming}' isn't a valid value for {feature} ({exc}).",
        ) from exc


async def _snapshot(db: AsyncSession, profile: StyleProfile) -> None:
    """Record the profile before changing it, so every change is reversible."""
    db.add(
        StyleProfileVersion(
            user_id=profile.user_id,
            version=profile.version,
            profile_json=profile.profile_json,
        )
    )


@router.get("/", response_model=StyleResponse)
async def get_style_profile(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get the current user's style profile."""
    profile = await _get_profile(db, current_user)
    if not profile:
        return StyleResponse(profile=StyleProfileSchema(), version=0)
    return StyleResponse(
        profile=StyleProfileSchema(**profile.profile_json), version=profile.version
    )


@router.get("/explain")
async def explain_style_profile(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Return the profile fields with their reasoning and confidence scores."""
    profile = await _get_profile(db, current_user)
    if not profile:
        return {}

    try:
        dump = StyleProfileSchema(**profile.profile_json).model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing profile: {e}")

    explanations = {}
    for field, feature in dump.items():
        if field == "source_contributions":
            continue
        explanations[field] = {
            "value": feature["value"],
            "reason": feature["reason"],
            "confidence": feature["confidence"],
            "observations": feature.get("observations", 0),
            "pinned": feature.get("pinned", False),
            "last_updated": feature.get("last_updated"),
            "source_contributions": dump.get("source_contributions"),
        }
    return explanations


@router.get("/dashboard")
async def get_style_dashboard(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Aggregated endpoint for the Style Intelligence Dashboard."""
    profile = await _get_profile(db, current_user)

    current_profile: dict[str, Any] = {}
    sources: dict[str, float] = {}

    if profile:
        dump = StyleProfileSchema(**profile.profile_json).model_dump()
        for field, feature in dump.items():
            if field == "source_contributions":
                sources = feature
                continue
            current_profile[field] = {
                "value": feature["value"],
                "reason": feature["reason"],
                "confidence": feature["confidence"],
                "observations": feature.get("observations", 0),
                "pinned": feature.get("pinned", False),
                "last_updated": feature.get("last_updated"),
            }

    versions_res = await db.execute(
        select(StyleProfileVersion)
        .where(StyleProfileVersion.user_id == current_user.id)
        .order_by(StyleProfileVersion.version)
    )
    versions = [
        {
            "version": v.version,
            "created_at": v.created_at,
            "profile_json": v.profile_json,
        }
        for v in versions_res.scalars().all()
    ]

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
    edited_count = await db.execute(
        select(func.count(EditedNote.id))
        .join(GeneratedNote)
        .where(GeneratedNote.user_id == current_user.id)
    )
    feedback_count = await db.execute(
        select(func.count(StyleFeedback.id))
        .join(GeneratedNote)
        .where(GeneratedNote.user_id == current_user.id)
    )

    confidences = [
        v.get("confidence")
        for v in current_profile.values()
        if isinstance(v.get("confidence"), (int, float))
    ]
    average_score = (
        round((sum(confidences) / len(confidences)) * 100, 1) if confidences else 0
    )

    return {
        "current_profile": current_profile,
        "sources": sources,
        "versions": versions,
        "learning_progress": {
            "style_profile_version": profile.version if profile else 0,
            "total_imported_notes": historical_count.scalar() or 0,
            "generated_notes": generated_count.scalar() or 0,
            "edited_notes": edited_count.scalar() or 0,
            "feedback_sessions": feedback_count.scalar() or 0,
            "average_score": average_score,
        },
    }


@router.get("/progress")
async def get_style_progress(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Whether personalization is actually improving, from the evaluation loop."""
    from app.evaluation.analytics import calculate_improvement_insights
    from app.evaluation.benchmark import compute_benchmark

    rows = (
        await db.execute(
            select(StyleFeedback.feedback_json, StyleFeedback.created_at)
            .join(GeneratedNote, StyleFeedback.generated_note_id == GeneratedNote.id)
            .where(GeneratedNote.user_id == current_user.id)
            .order_by(StyleFeedback.created_at)
        )
    ).all()

    history = []
    for feedback_json, created_at in rows:
        evaluation = (feedback_json or {}).get("evaluation")
        if isinstance(evaluation, dict) and "personalization_score" in evaluation:
            history.append({**evaluation, "created_at": created_at})

    if not history:
        return {
            "measured": False,
            "points": [],
            "insights": [],
            "benchmark": compute_benchmark([]),
        }

    return {
        "measured": True,
        "points": [
            {
                "score": h["personalization_score"],
                "created_at": h["created_at"],
            }
            for h in history
        ],
        "current_score": round(history[-1]["personalization_score"]),
        "trend": round(
            history[-1]["personalization_score"] - history[0]["personalization_score"]
        ),
        "insights": calculate_improvement_insights(history),
        "benchmark": compute_benchmark(history),
    }


@router.post("/analyze", response_model=StyleResponse)
async def analyze_style(
    file: UploadFile = File(...), current_user: User = Depends(deps.get_current_user)
):
    """Analyze an uploaded document and infer the style profile without saving."""
    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(file.filename or 'note')}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        parsed = await run_in_threadpool(parse_document, filepath, file.content_type)
        if not parsed.text.strip():
            raise FileProcessingError(
                "No readable text was found in that file, so there's nothing to learn from."
            )

        inferred = await run_in_threadpool(analyze_style_from_document, parsed)
        return StyleResponse(profile=inferred, version=0)
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@router.post("/update", response_model=StyleResponse)
async def update_style_profile(
    request: UpdateStyleRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Merge the provided style profile with the existing one and save it."""
    db_profile = await _get_profile(db, current_user)

    if db_profile:
        await _snapshot(db, db_profile)
        db_profile.profile_json = merge_profiles(db_profile.profile_json, request.profile)
        db_profile.version += 1
    else:
        db_profile = StyleProfile(
            user_id=current_user.id,
            profile_json=request.profile.model_dump(),
            version=1,
        )
        db.add(db_profile)

    await db.commit()
    await db.refresh(db_profile)
    return StyleResponse(
        profile=StyleProfileSchema(**db_profile.profile_json), version=db_profile.version
    )


@router.put("/attributes/{feature}", response_model=StyleResponse)
async def override_attribute(
    feature: str,
    payload: AttributeOverrideRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Set one style attribute by hand, optionally pinning it against learning.

    A pinned attribute is skipped by the learning rule, so "I always want
    tables" actually sticks instead of being averaged away by the next edit.
    """
    profile = await _get_profile(db, current_user)
    if profile is None:
        profile = StyleProfile(
            user_id=current_user.id, profile_json=StyleProfileSchema().model_dump(), version=1
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    try:
        schema = StyleProfileSchema(**profile.profile_json)
    except Exception:
        schema = StyleProfileSchema()

    if not hasattr(schema, feature) or feature == "source_contributions":
        raise HTTPException(status_code=404, detail=f"Unknown style attribute '{feature}'.")

    current = getattr(schema, feature)
    value = _coerce_attribute_value(feature, current.value, payload.value)

    await _snapshot(db, profile)
    try:
        if payload.pinned:
            setattr(schema, feature, pin_value(current, value))
        else:
            setattr(schema, feature, unpin(pin_value(current, value)))
        updated_json = schema.model_dump()
        # Round-trip before persisting: if the result can't be re-parsed, the
        # next read would silently fall back to a default profile.
        StyleProfileSchema(**updated_json)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"'{payload.value}' isn't a valid value for {feature}.",
        ) from exc

    profile.profile_json = updated_json
    profile.version += 1
    await db.commit()
    await db.refresh(profile)

    return StyleResponse(
        profile=StyleProfileSchema(**profile.profile_json), version=profile.version
    )


@router.delete("/attributes/{feature}", response_model=StyleResponse)
async def reset_attribute(
    feature: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Release a hand-set attribute so PersonaNotes learns it again."""
    profile = await _get_profile(db, current_user)
    if profile is None:
        raise HTTPException(status_code=404, detail="No style profile yet.")

    try:
        schema = StyleProfileSchema(**profile.profile_json)
    except Exception:
        schema = StyleProfileSchema()

    if not hasattr(schema, feature) or feature == "source_contributions":
        raise HTTPException(status_code=404, detail=f"Unknown style attribute '{feature}'.")

    await _snapshot(db, profile)
    setattr(schema, feature, unpin(getattr(schema, feature)))
    profile.profile_json = schema.model_dump()
    profile.version += 1
    await db.commit()
    await db.refresh(profile)

    return StyleResponse(
        profile=StyleProfileSchema(**profile.profile_json), version=profile.version
    )


@router.post("/reset", response_model=StyleResponse)
async def reset_profile(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Start the style profile over, keeping the old version as history."""
    profile = await _get_profile(db, current_user)
    if profile is None:
        return StyleResponse(profile=StyleProfileSchema(), version=0)

    await _snapshot(db, profile)
    profile.profile_json = StyleProfileSchema().model_dump()
    profile.version += 1
    await db.commit()
    await db.refresh(profile)
    return StyleResponse(
        profile=StyleProfileSchema(**profile.profile_json), version=profile.version
    )


@router.post("/versions/{version}/restore", response_model=StyleResponse)
async def restore_version(
    version: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Roll the profile back to an earlier snapshot."""
    snapshot = (
        await db.execute(
            select(StyleProfileVersion).where(
                StyleProfileVersion.user_id == current_user.id,
                StyleProfileVersion.version == version,
            )
        )
    ).scalars().first()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="That profile version doesn't exist.")

    profile = await _get_profile(db, current_user)
    if profile is None:
        raise HTTPException(status_code=404, detail="No style profile yet.")

    await _snapshot(db, profile)
    profile.profile_json = snapshot.profile_json
    profile.version += 1
    await db.commit()
    await db.refresh(profile)
    return StyleResponse(
        profile=StyleProfileSchema(**profile.profile_json), version=profile.version
    )


@router.post("/preview")
async def preview_style(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Render a short sample passage in the current profile.

    Makes an abstract 16-dimensional object concrete without spending a full
    generation on it.
    """
    from app.core.config import settings as app_settings
    from app.services.llm_service import generation_model
    from app.style.prompt_format import summarize_style_for_prompt

    profile = await _get_profile(db, current_user)
    style_json = summarize_style_for_prompt(profile.profile_json if profile else {})

    if not app_settings.GEMINI_API_KEY:
        return {"markdown": "Add a GEMINI_API_KEY on the server to see a live preview."}

    prompt = (
        "Write a short sample of lecture notes (about 120 words) on the topic "
        "'how a hash table works', formatted exactly according to this style "
        "profile. Return only the notes.\n\nSTYLE PROFILE:\n" + style_json
    )
    try:
        response = await run_in_threadpool(generation_model.generate_content, prompt)
        return {"markdown": response.text}
    except Exception as exc:
        logger.warning("Style preview failed: %s", exc)
        return {"markdown": "The preview couldn't be generated right now."}
