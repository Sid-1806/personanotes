"""Courses, note metadata/lineage, chat threads, ingestion diagnostics.

All changes are additive and backfillable:
  * every user with lectures gets an "Uncategorized" course and their lectures
    are attached to it, so the previously flat list keeps working;
  * existing notes become version roots (parent_note_id NULL);
  * existing edits become the current revision (is_current true).

Revision ID: a1b2c3d4e5f6
Revises: 9a1b2c3d4e5f
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f6"
down_revision = "9a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- courses -----------------------------------------------------------
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("color", sa.String(), server_default="indigo", nullable=False),
        sa.Column("archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_courses_id", "courses", ["id"])
    op.create_index("ix_courses_user_id", "courses", ["user_id"])

    # --- lectures ----------------------------------------------------------
    op.add_column("lectures", sa.Column("course_id", sa.Integer(), nullable=True))
    op.add_column("lectures", sa.Column("title", sa.String(), nullable=True))
    op.add_column("lectures", sa.Column("error_message", sa.String(), nullable=True))
    op.add_column(
        "lectures",
        sa.Column("page_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "lectures",
        sa.Column("archived", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_foreign_key(
        "fk_lectures_course_id", "lectures", "courses", ["course_id"], ["id"]
    )
    op.create_index("ix_lectures_course_id", "lectures", ["course_id"])

    # --- generated_notes ---------------------------------------------------
    op.add_column("generated_notes", sa.Column("title", sa.String(), nullable=True))
    op.add_column(
        "generated_notes",
        sa.Column("note_type", sa.String(), server_default="full", nullable=False),
    )
    op.add_column("generated_notes", sa.Column("prompt", sa.String(), nullable=True))
    op.add_column(
        "generated_notes", sa.Column("parent_note_id", sa.Integer(), nullable=True)
    )
    op.add_column("generated_notes", sa.Column("course_id", sa.Integer(), nullable=True))
    op.add_column(
        "generated_notes",
        sa.Column("grounding_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "generated_notes",
        sa.Column("archived", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "generated_notes",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_foreign_key(
        "fk_generated_notes_parent",
        "generated_notes",
        "generated_notes",
        ["parent_note_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_generated_notes_course", "generated_notes", "courses", ["course_id"], ["id"]
    )
    op.create_index("ix_generated_notes_parent_note_id", "generated_notes", ["parent_note_id"])
    op.create_index("ix_generated_notes_course_id", "generated_notes", ["course_id"])
    op.create_index("ix_generated_notes_lecture_id", "generated_notes", ["lecture_id"])
    op.create_index(
        "ix_generated_notes_user_created",
        "generated_notes",
        ["user_id", sa.text("created_at DESC")],
    )

    # --- edited_notes ------------------------------------------------------
    op.add_column(
        "edited_notes",
        sa.Column("is_current", sa.Boolean(), server_default="true", nullable=False),
    )

    # --- historical_notes --------------------------------------------------
    op.add_column(
        "historical_notes",
        sa.Column(
            "contribution_weight", sa.Float(), server_default="0", nullable=False
        ),
    )

    # --- chat --------------------------------------------------------------
    op.create_table(
        "chat_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(), server_default="all", nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("lecture_id", sa.Integer(), nullable=True),
        sa.Column("note_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), server_default="New conversation", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["lecture_id"], ["lectures.id"]),
        sa.ForeignKeyConstraint(["note_id"], ["generated_notes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_threads_id", "chat_threads", ["id"])
    op.create_index("ix_chat_threads_user_id", "chat_threads", ["user_id"])
    op.create_index("ix_chat_threads_course_id", "chat_threads", ["course_id"])
    op.create_index("ix_chat_threads_lecture_id", "chat_threads", ["lecture_id"])
    op.create_index("ix_chat_threads_note_id", "chat_threads", ["note_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["thread_id"], ["chat_threads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_id", "chat_messages", ["id"])
    op.create_index(
        "ix_chat_messages_thread_created", "chat_messages", ["thread_id", "created_at"]
    )

    # --- backfill ----------------------------------------------------------
    # One "Uncategorized" course per user that already owns lectures, so the
    # previously flat list has a home and nothing disappears from the UI.
    op.execute(
        """
        INSERT INTO courses (user_id, name, code, color, archived)
        SELECT DISTINCT l.user_id, 'Uncategorized', NULL, 'slate', false
        FROM lectures l
        WHERE NOT EXISTS (
            SELECT 1 FROM courses c
            WHERE c.user_id = l.user_id AND c.name = 'Uncategorized'
        )
        """
    )
    op.execute(
        """
        UPDATE lectures l
        SET course_id = c.id
        FROM courses c
        WHERE c.user_id = l.user_id
          AND c.name = 'Uncategorized'
          AND l.course_id IS NULL
        """
    )
    # Notes inherit their lecture's course where one exists.
    op.execute(
        """
        UPDATE generated_notes n
        SET course_id = l.course_id
        FROM lectures l
        WHERE n.lecture_id = l.id AND n.course_id IS NULL
        """
    )
    # Only the newest edit per note is the current body; older ones are history.
    op.execute(
        """
        UPDATE edited_notes e
        SET is_current = false
        WHERE e.id NOT IN (
            SELECT DISTINCT ON (generated_note_id) id
            FROM edited_notes
            ORDER BY generated_note_id, edited_at DESC, id DESC
        )
        """
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_threads")

    op.drop_column("historical_notes", "contribution_weight")
    op.drop_column("edited_notes", "is_current")

    op.drop_index("ix_generated_notes_user_created", table_name="generated_notes")
    op.drop_index("ix_generated_notes_lecture_id", table_name="generated_notes")
    op.drop_index("ix_generated_notes_course_id", table_name="generated_notes")
    op.drop_index("ix_generated_notes_parent_note_id", table_name="generated_notes")
    op.drop_constraint("fk_generated_notes_course", "generated_notes", type_="foreignkey")
    op.drop_constraint("fk_generated_notes_parent", "generated_notes", type_="foreignkey")
    for col in (
        "updated_at",
        "archived",
        "grounding_json",
        "course_id",
        "parent_note_id",
        "prompt",
        "note_type",
        "title",
    ):
        op.drop_column("generated_notes", col)

    op.drop_index("ix_lectures_course_id", table_name="lectures")
    op.drop_constraint("fk_lectures_course_id", "lectures", type_="foreignkey")
    for col in ("archived", "page_count", "error_message", "title", "course_id"):
        op.drop_column("lectures", col)

    op.drop_index("ix_courses_user_id", table_name="courses")
    op.drop_index("ix_courses_id", table_name="courses")
    op.drop_table("courses")
