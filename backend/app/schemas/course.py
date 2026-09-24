from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=40)
    color: str = "indigo"


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=40)
    color: str | None = None
    archived: bool | None = None


class CourseResponse(BaseModel):
    id: int
    name: str
    code: str | None = None
    color: str = "indigo"
    archived: bool = False
    created_at: datetime

    # Counts drive the course card without a second round-trip.
    lecture_count: int = 0
    note_count: int = 0
    ready_lecture_count: int = 0
    processing_lecture_count: int = 0
    failed_lecture_count: int = 0
    last_activity_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
