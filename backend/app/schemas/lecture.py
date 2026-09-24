from pydantic import BaseModel, ConfigDict
from datetime import datetime


class LectureBase(BaseModel):
    """
    Base Pydantic schema for Lecture properties.

    Attributes:
        filename (str): Original filename of the uploaded lecture.
        filetype (str): Type/extension of the file.
    """
    filename: str
    filetype: str


class LectureCreate(LectureBase):
    """
    Schema for creating a new Lecture record.

    Attributes:
        filepath (str): Internal storage path of the file.
    """
    filepath: str


class LectureResponse(LectureBase):
    """
    Schema for returning Lecture data in API responses.

    Attributes:
        id (int): Primary key of the lecture.
        user_id (int): Foreign key of the user who owns it.
        uploaded_at (datetime): Timestamp of the upload.
    """
    id: int
    user_id: int
    uploaded_at: datetime
    course_id: int | None = None
    course_name: str | None = None
    title: str | None = None
    ingestion_status: str = "pending"
    # Populated on failure so the UI can explain what went wrong and offer a retry.
    error_message: str | None = None
    chunk_count: int = 0
    page_count: int = 0
    note_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class LectureUpdate(BaseModel):
    """Rename a lecture or move it to another course."""

    title: str | None = None
    course_id: int | None = None


class LectureTextResponse(BaseModel):
    """Preview of what the parser actually extracted from the file."""

    id: int
    page_count: int
    chunk_count: int
    text: str
    truncated: bool = False
