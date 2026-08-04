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

    model_config = ConfigDict(from_attributes=True)
