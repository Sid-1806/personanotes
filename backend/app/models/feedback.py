from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base


class GeneratedNote(Base):
    """A note produced by the generation pipeline.

    ``parent_note_id`` links a refinement back to the note it was derived from,
    which turns a refine chain into a real version timeline instead of a set of
    unrelated rows. ``grounding_json`` persists the retrieved excerpts so the UI
    can show citations long after generation.
    """

    __tablename__ = "generated_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    lecture_id = Column(
        Integer, ForeignKey("lectures.id"), nullable=True, index=True
    )  # Optional, note could be across lectures
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    parent_note_id = Column(
        Integer, ForeignKey("generated_notes.id"), nullable=True, index=True
    )
    title = Column(String, nullable=True)
    # full | summary | key_concepts | practice | cheatsheet | custom | saved_answer
    note_type = Column(String, nullable=False, server_default="full")
    prompt = Column(String, nullable=True)
    generated_markdown = Column(String, nullable=False)
    # {chunks_used, lecture_ids, excerpts: [{lecture_id, lecture_title, text, score}]}
    grounding_json = Column(JSONB, nullable=True)
    archived = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EditedNote(Base):
    """A user-authored revision of a generated note.

    ``is_current`` marks the revision that should be served as the note's body.
    Without it the user's own edits were written and never read back.
    """

    __tablename__ = "edited_notes"

    id = Column(Integer, primary_key=True, index=True)
    generated_note_id = Column(
        Integer, ForeignKey("generated_notes.id"), index=True, nullable=False
    )
    edited_markdown = Column(String, nullable=False)
    is_current = Column(Boolean, nullable=False, server_default="true")
    edited_at = Column(DateTime(timezone=True), server_default=func.now())


class StyleFeedback(Base):
    __tablename__ = "style_feedback"

    id = Column(Integer, primary_key=True, index=True)
    generated_note_id = Column(
        Integer, ForeignKey("generated_notes.id"), index=True, nullable=False
    )
    feedback_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
