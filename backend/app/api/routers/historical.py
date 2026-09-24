"""Historical notes: the past work that bootstraps someone's style profile.

These are *training sources*, not a second content library — which is why they
live under Style in the UI rather than beside Lectures. Listing and removing
them matters: a bad import used to be permanent and invisible.
"""

import logging
import os
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.historical_notes.analyzer import (
    aggregate_historical_features,
    analyze_historical_note,
)
from app.historical_notes.importer import import_files
from app.historical_notes.merger import merge_historical_analysis
from app.models.historical import HistoricalNote, NoteSourceEnum
from app.models.style import StyleProfile, StyleProfileVersion
from app.models.user import User
from app.style.schema import StyleProfileSchema

router = APIRouter()
logger = logging.getLogger(__name__)


class HistoricalNoteResponse(BaseModel):
    id: int
    title: str
    filename: str
    source: str
    analysis_status: str
    contribution_weight: float = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


async def _rebuild_profile_from_sources(db: AsyncSession, user: User) -> None:
    """Recompute the historical contribution after a source is removed.

    Removing a source should visibly change the profile, otherwise the delete
    button is cosmetic. The remaining sources are re-analysed from disk and the
    profile is rebuilt from a clean slate plus their aggregate.
    """
    from app.services.document_parser import parse_document

    notes = (
        await db.execute(
            select(HistoricalNote).where(HistoricalNote.user_id == user.id)
        )
    ).scalars().all()

    profile = (
        await db.execute(select(StyleProfile).where(StyleProfile.user_id == user.id))
    ).scalars().first()
    if profile is None:
        return

    db.add(
        StyleProfileVersion(
            user_id=user.id, version=profile.version, profile_json=profile.profile_json
        )
    )

    if not notes:
        profile.profile_json = StyleProfileSchema().model_dump()
        profile.version += 1
        return

    analyses = []
    for note in notes:
        if not note.filepath or not os.path.exists(note.filepath):
            continue
        parsed = await run_in_threadpool(parse_document, note.filepath)
        if parsed.text.strip():
            analyses.append(await run_in_threadpool(analyze_historical_note, parsed.text))

    if not analyses:
        return

    aggregated = aggregate_historical_features(analyses)
    rebuilt = merge_historical_analysis(
        StyleProfileSchema(), aggregated, len(analyses)
    )
    profile.profile_json = rebuilt.model_dump()
    profile.version += 1


@router.post("/upload")
async def upload_historical_notes(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Upload and analyze historical notes to bootstrap the style profile."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    imported_data = await import_files(files)
    if not imported_data:
        raise HTTPException(
            status_code=400, detail="None of those files could be read."
        )

    analyses = []
    skipped: list[str] = []

    for filename, filepath, markdown_text in imported_data:
        if not (markdown_text or "").strip():
            skipped.append(filename)
            continue

        db.add(
            HistoricalNote(
                user_id=current_user.id,
                title=filename,
                filename=filename,
                filepath=filepath,
                source=NoteSourceEnum.uploaded_note,
                analysis_status="analyzed",
                contribution_weight=1.0,
            )
        )
        analyses.append(await run_in_threadpool(analyze_historical_note, markdown_text))

    if not analyses:
        raise HTTPException(
            status_code=400,
            detail="No readable text was found in those files, so nothing could be learned.",
        )

    aggregated = aggregate_historical_features(analyses)

    profile = (
        await db.execute(
            select(StyleProfile).where(StyleProfile.user_id == current_user.id)
        )
    ).scalars().first()

    if profile:
        db.add(
            StyleProfileVersion(
                user_id=current_user.id,
                version=profile.version,
                profile_json=profile.profile_json,
            )
        )
        try:
            current_schema = StyleProfileSchema(**profile.profile_json)
        except Exception:
            current_schema = StyleProfileSchema()

        updated = merge_historical_analysis(current_schema, aggregated, len(analyses))
        profile.profile_json = updated.model_dump()
        profile.version += 1
    else:
        new_schema = merge_historical_analysis(
            StyleProfileSchema(), aggregated, len(analyses)
        )
        db.add(
            StyleProfile(user_id=current_user.id, profile_json=new_schema.model_dump())
        )

    await db.commit()

    return {
        "status": "success",
        "imported_count": len(analyses),
        "skipped": skipped,
        "aggregated_features": aggregated.get("aggregated_features", {}),
    }


@router.get("/", response_model=List[HistoricalNoteResponse])
async def list_historical_notes(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Every past note that has shaped the style profile."""
    notes = (
        await db.execute(
            select(HistoricalNote)
            .where(HistoricalNote.user_id == current_user.id)
            .order_by(HistoricalNote.created_at.desc())
        )
    ).scalars().all()
    return [
        HistoricalNoteResponse(
            id=n.id,
            title=n.title,
            filename=n.filename,
            source=n.source.value if hasattr(n.source, "value") else str(n.source),
            analysis_status=n.analysis_status or "pending",
            contribution_weight=n.contribution_weight or 0.0,
            created_at=n.created_at,
        )
        for n in notes
    ]


@router.get("/status")
async def get_historical_status(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get count of historical notes analyzed."""
    notes = (
        await db.execute(
            select(HistoricalNote).where(HistoricalNote.user_id == current_user.id)
        )
    ).scalars().all()
    return {"total_imported": len(notes)}


@router.delete("/{note_id}", status_code=204)
async def delete_historical_note(
    note_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Remove a training source and recompute the profile without it."""
    note = (
        await db.execute(
            select(HistoricalNote).where(
                HistoricalNote.id == note_id,
                HistoricalNote.user_id == current_user.id,
            )
        )
    ).scalars().first()
    if note is None:
        raise HTTPException(status_code=404, detail="That source doesn't exist.")

    filepath = note.filepath
    await db.delete(note)
    await db.flush()

    await _rebuild_profile_from_sources(db, current_user)
    await db.commit()

    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except OSError as exc:
        logger.warning("Could not remove historical file %s: %s", filepath, exc)

    return None
