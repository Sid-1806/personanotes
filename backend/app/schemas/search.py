from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SearchScope = Literal["all", "lectures", "notes"]


class SearchHit:
    pass


class SearchExcerpt(BaseModel):
    text: str
    page: int | None = None
    score: float | None = None


class SearchGroup(BaseModel):
    """Hits grouped by their source document, so results read as documents."""

    kind: Literal["lecture", "note"]
    source_id: int
    title: str
    course_id: int | None = None
    course_name: str | None = None
    lecture_id: int | None = None
    best_score: float | None = None
    excerpts: list[SearchExcerpt] = []


class SearchResponse(BaseModel):
    query: str
    scope: SearchScope = "all"
    groups: list[SearchGroup] = []
    total_hits: int = 0
    # Set when the vector store is unreachable and we fell back to plain text
    # matching, so the UI can say so instead of quietly returning worse results.
    degraded: bool = False


class TitleMatch(BaseModel):
    kind: Literal["lecture", "note", "course"]
    id: int
    title: str
    subtitle: str | None = None
    created_at: datetime | None = None
