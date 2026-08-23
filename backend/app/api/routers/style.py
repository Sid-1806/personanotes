from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import shutil
import os
import uuid

from app.api import deps
from app.models.user import User
from app.models.style import StyleProfile, StyleProfileVersion
from app.models.historical import HistoricalNote
from app.models.feedback import GeneratedNote, EditedNote, StyleFeedback
from app.style.schema import StyleProfileSchema, StyleResponse, UpdateStyleRequest
from app.services.document_parser import parse_document
from app.style.analyzer import analyze_style_from_document
from app.style.updater import merge_profiles
from sqlalchemy import func, desc

router = APIRouter()

UPLOAD_DIR = "uploads/style_analysis"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/", response_model=StyleResponse)
async def get_style_profile(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get the current user's style profile."""
    result = await db.execute(
        select(StyleProfile).where(StyleProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()

    if not profile:
        # Return an empty/default profile if none exists.
        # Schema field defaults are valid nested FeatureValue objects.
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
    result = await db.execute(
        select(StyleProfile).where(StyleProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()

    if not profile:
        return {}

    try:
        schema = StyleProfileSchema(**profile.profile_json)
        # Convert schema to dict, extracting the FeatureValue objects
        explanations = {}
        dump = schema.model_dump()
        for field, feature_val in dump.items():
            if field == "source_contributions":
                continue  # Handled below or separately if needed
            explanations[field] = {
                "value": feature_val["value"],
                "reason": feature_val["reason"],
                "confidence": feature_val["confidence"],
                "last_updated": feature_val.get("last_updated"),
                "source_contributions": dump.get("source_contributions"),
            }
        return explanations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing profile: {e}")


@router.get("/dashboard")
async def get_style_dashboard(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Aggregated endpoint for the Style Intelligence Dashboard."""
    # 1. Current Profile & Sources
    result = await db.execute(
        select(StyleProfile).where(StyleProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()

    current_profile = {}
    sources = {}

    if profile:
        schema = StyleProfileSchema(**profile.profile_json)
        dump = schema.model_dump()
        for field, feature_val in dump.items():
            if field == "source_contributions":
                sources = feature_val
                continue
            current_profile[field] = {
                "value": feature_val["value"],
                "reason": feature_val["reason"],
                "confidence": feature_val["confidence"],
                "last_updated": feature_val.get("last_updated"),
            }

    # 2. Versions
    versions_stmt = (
        select(StyleProfileVersion)
        .where(StyleProfileVersion.user_id == current_user.id)
        .order_by(StyleProfileVersion.version)
    )
    versions_res = await db.execute(versions_stmt)
    versions = []
    for v in versions_res.scalars().all():
        versions.append(
            {
                "version": v.version,
                "created_at": v.created_at,
                "profile_json": v.profile_json,
            }
        )

    # 3. Learning Progress
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

    feedback_stmt = (
        select(func.count(StyleFeedback.id))
        .join(GeneratedNote)
        .where(GeneratedNote.user_id == current_user.id)
    )
    feedback_count = await db.execute(feedback_stmt)

    _confs = [
        v.get("confidence") for v in current_profile.values()
        if isinstance(v.get("confidence"), (int, float))
    ]
    average_score = round((sum(_confs) / len(_confs)) * 100, 1) if _confs else 0

    learning_progress = {
        "style_profile_version": profile.version if profile else 0,
        "total_imported_notes": historical_count.scalar() or 0,
        "generated_notes": generated_count.scalar() or 0,
        "edited_notes": edited_count.scalar() or 0,
        "feedback_sessions": feedback_count.scalar() or 0,
        "average_score": round(average_score, 1),
    }

    return {
        "current_profile": current_profile,
        "sources": sources,
        "versions": versions,
        "learning_progress": learning_progress,
    }


@router.post("/analyze", response_model=StyleResponse)
async def analyze_style(
    file: UploadFile = File(...), current_user: User = Depends(deps.get_current_user)
):
    """Analyze an uploaded document and infer the style profile without saving."""
    # Sanitize the client-supplied filename to prevent path traversal.
    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse document structure
        parsed_doc = parse_document(filepath, file.content_type)
        if not parsed_doc.text.strip():
            raise HTTPException(
                status_code=400, detail="Could not extract text from the file."
            )

        # Analyze style
        inferred_profile = analyze_style_from_document(parsed_doc)

        # Return the profile but don't save it yet
        return StyleResponse(profile=inferred_profile, version=0)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
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
    result = await db.execute(
        select(StyleProfile).where(StyleProfile.user_id == current_user.id)
    )
    db_profile = result.scalars().first()

    if db_profile:
        # Merge new profile into existing
        merged_json = merge_profiles(db_profile.profile_json, request.profile)
        db_profile.profile_json = merged_json
        db_profile.version += 1
    else:
        # Create new profile
        db_profile = StyleProfile(
            user_id=current_user.id,
            profile_json=request.profile.model_dump(),
            version=1,
        )
        db.add(db_profile)

    await db.commit()
    await db.refresh(db_profile)

    return StyleResponse(
        profile=StyleProfileSchema(**db_profile.profile_json),
        version=db_profile.version,
    )
