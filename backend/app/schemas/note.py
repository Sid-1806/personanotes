from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

NoteType = Literal[
    "full", "summary", "key_concepts", "practice", "cheatsheet", "custom", "saved_answer"
]


class Excerpt(BaseModel):
    """One retrieved chunk, kept so the UI can show what the note was built on."""

    lecture_id: int | None = None
    lecture_title: str | None = None
    note_id: int | None = None
    note_title: str | None = None
    page: int | None = None
    score: float | None = None
    kind: str | None = None
    text: str = ""


class Grounding(BaseModel):
    chunks_used: int = 0
    lecture_ids: list[int] = []
    top_score: float | None = None
    excerpts: list[Excerpt] = []


class GenerateNotesRequest(BaseModel):
    prompt: str = ""
    lecture_id: int | None = None
    course_id: int | None = None
    note_type: NoteType = "full"
    # One-off nudges (length / diagrams / examples) that do NOT change the
    # saved style profile.
    style_overrides: dict[str, str] | None = None
    # Explicit regeneration must skip the response cache, or "Regenerate"
    # silently returns the identical text it just produced.
    no_cache: bool = False


class RefineRequest(BaseModel):
    instruction: str
    # When present, only this passage is rewritten and spliced back in.
    selection: str | None = None


class NoteUpdateRequest(BaseModel):
    """Save the user's own version of a note, and/or rename it."""

    markdown: str | None = None
    title: str | None = Field(default=None, max_length=200)
    # Feed the edit into the style-learning loop. Default true keeps the
    # existing behaviour; the UI shows it as an explainable toggle.
    teach: bool = True


class NoteSummary(BaseModel):
    """Row shape for the notes index and course/lecture listings."""

    id: int
    title: str | None = None
    note_type: str = "full"
    lecture_id: int | None = None
    lecture_title: str | None = None
    course_id: int | None = None
    course_name: str | None = None
    parent_note_id: int | None = None
    has_edits: bool = False
    excerpt: str = ""
    word_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NoteListResponse(BaseModel):
    items: list[NoteSummary]
    total: int
    limit: int
    offset: int


class NoteDetailResponse(BaseModel):
    id: int
    title: str | None = None
    note_type: str = "full"
    prompt: str | None = None
    lecture_id: int | None = None
    lecture_title: str | None = None
    course_id: int | None = None
    course_name: str | None = None
    parent_note_id: int | None = None
    root_note_id: int | None = None
    # The model's output, always preserved.
    original_markdown: str
    # The user's saved version, when they have one. Without this the user's own
    # edits were stored and never readable again.
    edited_markdown: str | None = None
    has_edits: bool = False
    grounding: Grounding = Grounding()
    version_count: int = 1
    created_at: datetime
    updated_at: datetime | None = None


class GenerateNotesResponse(BaseModel):
    id: int
    title: str | None = None
    notes: str
    note_type: str = "full"
    lecture_id: int | None = None
    course_id: int | None = None
    parent_note_id: int | None = None
    chunks_used: int = 0
    lecture_ids: list[int] = []
    grounding: Grounding = Grounding()
    created_at: datetime | None = None


class NoteVersion(BaseModel):
    """A point in a note's history: a generation, a refinement, or a user edit."""

    id: int
    kind: Literal["generated", "refined", "edited"]
    note_id: int
    label: str
    title: str | None = None
    word_count: int = 0
    created_at: datetime
    is_current: bool = False


class NoteVersionsResponse(BaseModel):
    root_note_id: int
    versions: list[NoteVersion]


class NoteDiffResponse(BaseModel):
    from_label: str
    to_label: str
    from_markdown: str
    to_markdown: str
    stats: dict[str, Any] = {}


class FeedbackRequest(BaseModel):
    edited_markdown: str


class FeedbackResponse(BaseModel):
    updated_features: list[str]
    personalization_score: float | None = None
    summary: list[str] = []


class AskRequest(BaseModel):
    question: str
    scope: Literal["note", "lecture", "course", "all"] = "all"
    lecture_id: int | None = None
    course_id: int | None = None
    note_id: int | None = None
    thread_id: int | None = None


class SaveAnswerRequest(BaseModel):
    """Promote a useful chat answer into a note the user keeps."""

    content: str
    title: str | None = None
    lecture_id: int | None = None
    course_id: int | None = None
    # When set, the answer is appended to that note instead of creating one.
    append_to_note_id: int | None = None
