from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.models.user import User
from app.models.feedback import GeneratedNote
from app.services.llm_service import generate_notes

router = APIRouter()


class NoteDetailResponse(BaseModel):
    id: int
    notes: str
    created_at: datetime


@router.get("/{id}", response_model=NoteDetailResponse)
async def get_note(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Fetch a single generated note owned by the current user."""
    result = await db.execute(
        select(GeneratedNote).where(
            GeneratedNote.id == id, GeneratedNote.user_id == current_user.id
        )
    )
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteDetailResponse(
        id=note.id, notes=note.generated_markdown, created_at=note.created_at
    )


class GenerateNotesRequest(BaseModel):
    prompt: str


class GenerateNotesResponse(BaseModel):
    id: int
    notes: str


@router.post("/generate", response_model=GenerateNotesResponse)
async def generate_user_notes(
    request: GenerateNotesRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Generate personalized notes based on user prompt, style, and their uploaded lectures.
    """
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    from sqlalchemy.future import select
    from app.models.style import StyleProfile

    result = await db.execute(
        select(StyleProfile).where(StyleProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()

    # Use empty dict if no profile exists yet
    style_dict = profile.profile_json if profile else {}

    from app.models.feedback import GeneratedNote

    # generate_notes is synchronous (embedding + blocking Gemini HTTP call);
    # run it in a threadpool so it doesn't block the async event loop.
    notes = await run_in_threadpool(
        generate_notes, request.prompt, style_dict, current_user.id
    )

    # Save GeneratedNote to DB
    new_note = GeneratedNote(user_id=current_user.id, generated_markdown=notes)
    db.add(new_note)
    await db.commit()
    await db.refresh(new_note)

    return GenerateNotesResponse(id=new_note.id, notes=notes)


class FeedbackRequest(BaseModel):
    edited_markdown: str


class FeedbackResponse(BaseModel):
    updated_features: list[str]


@router.post("/{id}/feedback", response_model=FeedbackResponse)
async def submit_note_feedback(
    id: int,
    request: FeedbackRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Submit an edited note to the continual learning pipeline."""
    from sqlalchemy.future import select
    from app.models.feedback import GeneratedNote, EditedNote, StyleFeedback
    from app.models.style import StyleProfile, StyleProfileVersion
    from app.feedback.style_feedback import generate_style_feedback
    from app.feedback.updater import apply_feedback_to_profile
    from app.style.schema import StyleProfileSchema

    # 1. Load generated note
    result = await db.execute(
        select(GeneratedNote).where(
            GeneratedNote.id == id, GeneratedNote.user_id == current_user.id
        )
    )
    generated_note = result.scalars().first()
    if not generated_note:
        raise HTTPException(status_code=404, detail="Generated note not found")

    # 2. Pipeline: Generate feedback (blocking; offload from the event loop)
    feedback_data = await run_in_threadpool(
        generate_style_feedback,
        generated_note.generated_markdown,
        request.edited_markdown,
    )

    # Save edited note and feedback records
    edited_note = EditedNote(
        generated_note_id=id, edited_markdown=request.edited_markdown
    )
    style_feedback = StyleFeedback(generated_note_id=id, feedback_json=feedback_data)

    db.add(edited_note)
    db.add(style_feedback)

    # 3. Update StyleProfile
    profile_result = await db.execute(
        select(StyleProfile).where(StyleProfile.user_id == current_user.id)
    )
    db_profile = profile_result.scalars().first()

    updated_features = []

    if db_profile:
        # Save snapshot
        snapshot = StyleProfileVersion(
            user_id=current_user.id,
            version=db_profile.version,
            profile_json=db_profile.profile_json,
        )
        db.add(snapshot)

        # Merge feedback
        try:
            current_schema = StyleProfileSchema(**db_profile.profile_json)
        except Exception:
            current_schema = StyleProfileSchema()  # Fallback for schema mismatches

        updated_schema = apply_feedback_to_profile(current_schema, feedback_data)
        db_profile.profile_json = updated_schema.model_dump()
        db_profile.version += 1

        updated_features = [
            change["feature"] for change in feedback_data.get("changes", [])
        ]

    await db.commit()

    return FeedbackResponse(updated_features=updated_features)
