from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

Scope = Literal["note", "lecture", "course", "all"]


class Citation(BaseModel):
    lecture_id: int | None = None
    lecture_title: str | None = None
    note_id: int | None = None
    # Set when the chunk came from one of the user's own generated notes, so the
    # UI can say so instead of implying it came from the source document.
    note_title: str | None = None
    page: int | None = None
    score: float | None = None
    kind: str | None = None
    text: str = ""


class ChatRequest(BaseModel):
    message: str
    scope: Scope = "all"
    course_id: int | None = None
    lecture_id: int | None = None
    note_id: int | None = None
    thread_id: int | None = None


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    # Only assistant turns carry citations, so a user turn stores NULL. Coerce
    # it to an empty list here rather than making every client null-check it.
    citations: list[Citation] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("citations", mode="before")
    @classmethod
    def _null_citations_are_empty(cls, value):
        return value or []


class ChatThreadSummary(BaseModel):
    id: int
    title: str
    scope: str
    course_id: int | None = None
    lecture_id: int | None = None
    note_id: int | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ChatThreadDetail(ChatThreadSummary):
    messages: list[ChatMessageResponse] = []


class ChatResponse(BaseModel):
    thread_id: int
    message: ChatMessageResponse
