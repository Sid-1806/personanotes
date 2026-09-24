"""Every delete path must clear the foreign keys pointing at what it removes.

A missed reference is a hard 500 at the database, not a soft failure, and it
only shows up once a user has built the object graph that touches it — a course
with a conversation scoped to it, say. These tests read the delete handlers and
assert each inbound foreign key is accounted for, so a new relationship can't
be added without the matching cleanup.
"""

import inspect

import pytest

from app.api.routers import courses as courses_router
from app.api.routers import lectures as lectures_router
from app.api.routers import notes as notes_router
from app.api.routers import users as users_router
from app.models.chat import ChatMessage, ChatThread
from app.models.course import Course
from app.models.feedback import EditedNote, GeneratedNote, StyleFeedback
from app.models.lecture import Lecture


def _inbound_foreign_keys(target_table: str) -> set[str]:
    """Every "<table>.<column>" in the mapped models that points at a table."""
    models = (
        Course, Lecture, GeneratedNote, EditedNote,
        StyleFeedback, ChatThread, ChatMessage,
    )
    refs: set[str] = set()
    for model in models:
        for column in model.__table__.columns:
            for fk in column.foreign_keys:
                if fk.column.table.name == target_table:
                    refs.add(f"{model.__tablename__}.{column.name}")
    return refs


@pytest.mark.parametrize(
    "target, handler, expected_refs",
    [
        (
            "courses",
            courses_router.delete_course,
            {"lectures.course_id", "generated_notes.course_id", "chat_threads.course_id"},
        ),
        (
            "lectures",
            lectures_router.delete_lecture,
            {"generated_notes.lecture_id", "chat_threads.lecture_id"},
        ),
        (
            "generated_notes",
            notes_router.delete_note,
            {
                "edited_notes.generated_note_id",
                "style_feedback.generated_note_id",
                "generated_notes.parent_note_id",
                "chat_threads.note_id",
            },
        ),
    ],
)
def test_schema_has_exactly_the_references_we_handle(target, handler, expected_refs):
    """If a new FK is added, this fails until the delete handler is updated."""
    actual = _inbound_foreign_keys(target)
    assert actual == expected_refs, (
        f"Foreign keys into {target!r} changed: {actual}. "
        f"Update {handler.__name__} to clear the new reference, then this list."
    )


@pytest.mark.parametrize(
    "handler, must_mention",
    [
        (courses_router.delete_course, ["ChatThread", "Lecture", "GeneratedNote"]),
        (lectures_router.delete_lecture, ["ChatThread", "GeneratedNote"]),
        (notes_router.delete_note, ["ChatThread", "EditedNote", "StyleFeedback", "parent_note_id"]),
        (users_router.delete_account, ["ChatThread", "ChatMessage", "GeneratedNote", "Lecture", "Course"]),
    ],
)
def test_delete_handler_touches_every_dependent_model(handler, must_mention):
    source = inspect.getsource(handler)
    for name in must_mention:
        assert name in source, (
            f"{handler.__name__} never references {name}; a row pointing at the "
            f"deleted record would raise a ForeignKeyViolation"
        )


def test_course_delete_relocates_rather_than_destroys():
    """Removing a grouping must not destroy the coursework inside it."""
    source = inspect.getsource(courses_router.delete_course)
    assert "fallback" in source
    assert "ensure_default_course" in source
    # It must not delete lectures or notes outright.
    assert "db.delete(row)" not in source
