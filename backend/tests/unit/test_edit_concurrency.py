"""A note has at most one current revision, even under concurrent saves.

The original code read the previous revision, flipped it in Python, then
inserted the new one. Two saves landing together both read the same
"previous", both inserted ``is_current=true``, and which revision you read
back afterwards depended on timing. Two things prevent that now: saves are
serialised on the note row, and a partial unique index makes more than one
current revision unrepresentable.
"""

import inspect
import pathlib

import pytest

from app.api.routers import notes as notes_router

MIGRATION = (
    pathlib.Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "b2c3d4e5f6a7_one_current_edit.py"
)


def test_every_save_path_goes_through_the_serialised_helper():
    """No handler may set is_current by hand; that is what raced."""
    module_source = inspect.getsource(notes_router)
    assert "previous.is_current = False" not in module_source, (
        "a read-modify-write on is_current is back; use _replace_current_edit"
    )

    for handler in (
        notes_router.update_note,
        notes_router.submit_note_feedback,
        notes_router.save_answer,
    ):
        source = inspect.getsource(handler)
        if "EditedNote(" in source:
            pytest.fail(
                f"{handler.__name__} constructs an EditedNote directly instead of "
                "using _replace_current_edit, which serialises the write"
            )


def test_helper_locks_the_note_and_retires_prior_revisions_in_one_statement():
    source = inspect.getsource(notes_router._replace_current_edit)
    assert "with_for_update" in source, "saves must serialise on the note row"
    assert "update(EditedNote)" in source, (
        "prior revisions must be retired with a single UPDATE, not object by object"
    )


def test_revert_only_clears_the_current_revision():
    """Reverting discards the user's edit; it must not delete history."""
    source = inspect.getsource(notes_router.revert_note)
    assert "is_current = False" in source
    assert "db.delete" not in source, "revert must not destroy revision history"


def test_migration_enforces_the_invariant_in_the_schema():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "CREATE UNIQUE INDEX" in sql
    assert "WHERE is_current" in sql, (
        "the index must be partial, or historical revisions would collide"
    )
    # Existing duplicates have to be resolved before the index can be created.
    assert "UPDATE edited_notes" in sql
    assert "DISTINCT ON (generated_note_id)" in sql


def test_migration_keeps_the_newest_revision_when_deduplicating():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ORDER BY generated_note_id, edited_at DESC" in sql, (
        "deduplication must keep the newest revision, not an arbitrary one"
    )
