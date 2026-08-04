from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class NoteSourceEnum(str, enum.Enum):
    uploaded_note = "uploaded_note"
    imported_history = "imported_history"
    generated_note = "generated_note"


class HistoricalNote(Base):
    __tablename__ = "historical_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    source = Column(Enum(NoteSourceEnum), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analysis_status = Column(String, default="pending")
