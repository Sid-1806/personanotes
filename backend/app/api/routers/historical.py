from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Any
import logging

from app.api import deps
from app.models.user import User
from app.models.historical import HistoricalNote, NoteSourceEnum
from app.models.style import StyleProfile, StyleProfileVersion
from app.style.schema import StyleProfileSchema
from app.historical_notes.importer import import_files
from app.historical_notes.analyzer import (
    analyze_historical_note,
    aggregate_historical_features,
)
from app.historical_notes.merger import merge_historical_analysis

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_historical_notes(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Upload and analyze historical notes to bootstrap the style profile.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    # 1. Import files
    imported_data = await import_files(files)

    analyses = []

    for filename, filepath, markdown_text in imported_data:
        # Save to DB
        hist_note = HistoricalNote(
            user_id=current_user.id,
            title=filename,
            filename=filename,
            filepath=filepath,
            source=NoteSourceEnum.uploaded_note,
            analysis_status="analyzed",
        )
        db.add(hist_note)

        # Analyze in a threadpool to prevent blocking the event loop with synchronous Gemini calls
        analysis = await run_in_threadpool(analyze_historical_note, markdown_text)
        analyses.append(analysis)

    # Aggregate
    aggregated = aggregate_historical_features(analyses)

    # 2. Update Style Profile
    result = await db.execute(
        select(StyleProfile).where(StyleProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()

    if profile:
        # Snapshot
        snapshot = StyleProfileVersion(
            user_id=current_user.id,
            version=profile.version,
            profile_json=profile.profile_json,
        )
        db.add(snapshot)

        # Merge
        try:
            current_schema = StyleProfileSchema(**profile.profile_json)
        except Exception:
            current_schema = StyleProfileSchema()

        updated_schema = merge_historical_analysis(
            current_schema, aggregated, len(imported_data)
        )

        profile.profile_json = updated_schema.model_dump()
        profile.version += 1
    else:
        # Create new
        new_schema = merge_historical_analysis(
            StyleProfileSchema(), aggregated, len(imported_data)
        )
        new_profile = StyleProfile(
            user_id=current_user.id, profile_json=new_schema.model_dump()
        )
        db.add(new_profile)

    await db.commit()

    return {
        "status": "success",
        "imported_count": len(imported_data),
        "aggregated_features": aggregated.get("aggregated_features", {}),
    }


@router.get("/status")
async def get_historical_status(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get count of historical notes analyzed."""
    result = await db.execute(
        select(HistoricalNote).where(HistoricalNote.user_id == current_user.id)
    )
    notes = result.scalars().all()
    return {"total_imported": len(notes)}
