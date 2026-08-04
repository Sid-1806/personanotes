from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base


class GeneratedNote(Base):
    __tablename__ = "generated_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    lecture_id = Column(
        Integer, ForeignKey("lectures.id"), nullable=True
    )  # Optional, note could be across lectures
    generated_markdown = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EditedNote(Base):
    __tablename__ = "edited_notes"

    id = Column(Integer, primary_key=True, index=True)
    generated_note_id = Column(
        Integer, ForeignKey("generated_notes.id"), index=True, nullable=False
    )
    edited_markdown = Column(String, nullable=False)
    edited_at = Column(DateTime(timezone=True), server_default=func.now())


class StyleFeedback(Base):
    __tablename__ = "style_feedback"

    id = Column(Integer, primary_key=True, index=True)
    generated_note_id = Column(
        Integer, ForeignKey("generated_notes.id"), index=True, nullable=False
    )
    feedback_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
