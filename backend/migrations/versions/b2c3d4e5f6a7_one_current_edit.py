"""Enforce at most one current revision per note.

Saves used to read the previous revision and flip it in Python, so two
concurrent saves both saw the same "previous" and both inserted
``is_current=true``. The note then had several revisions claiming to be
current and which one you read back depended on timing.

The application now serialises saves on the note row, and this partial unique
index makes the invariant impossible to violate regardless of what later code
does. Existing duplicates are resolved first, keeping the newest revision.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-24
"""

from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_edited_notes_one_current_per_note"


def upgrade() -> None:
    # Keep only the newest current revision per note; retire the rest.
    op.execute(
        """
        UPDATE edited_notes
        SET is_current = false
        WHERE is_current = true
          AND id NOT IN (
            SELECT DISTINCT ON (generated_note_id) id
            FROM edited_notes
            WHERE is_current = true
            ORDER BY generated_note_id, edited_at DESC, id DESC
          )
        """
    )

    # Partial unique index: unlimited historical revisions, at most one current.
    op.execute(
        f"""
        CREATE UNIQUE INDEX {INDEX_NAME}
        ON edited_notes (generated_note_id)
        WHERE is_current
        """
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
