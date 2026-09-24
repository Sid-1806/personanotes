from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Lecture(Base):
    """
    SQLAlchemy model representing an uploaded lecture document.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key referencing the user who uploaded the lecture.
        course_id (int | None): Course this lecture belongs to.
        title (str | None): User-facing name; falls back to ``filename``.
        filename (str): Original name of the uploaded file.
        filepath (str): Storage path of the file.
        filetype (str): MIME type or extension of the file.
        ingestion_status (str): pending -> processing -> ready | failed.
        error_message (str | None): Why ingestion failed, surfaced to the UI.
        chunk_count (int): Number of indexed chunks.
        page_count (int): Pages parsed (PDFs).
        archived (bool): Hidden from default listings.
        uploaded_at (datetime): Timestamp when the file was uploaded.
        user (User): Relationship to the uploading user.
    """

    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    title = Column(String, nullable=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    filetype = Column(String, nullable=False)
    # Ingestion pipeline state, surfaced to the UI: pending -> processing -> ready | failed
    ingestion_status = Column(String, nullable=False, server_default="pending")
    # Populated on failure so the UI can explain what went wrong instead of
    # showing a bare red badge.
    error_message = Column(String, nullable=True)
    chunk_count = Column(Integer, nullable=False, server_default="0")
    page_count = Column(Integer, nullable=False, server_default="0")
    archived = Column(Boolean, nullable=False, server_default="false")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="lectures")

    @property
    def display_title(self) -> str:
        return self.title or self.filename
