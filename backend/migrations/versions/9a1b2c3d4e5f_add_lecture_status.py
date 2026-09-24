"""add lecture ingestion_status and chunk_count

Revision ID: 9a1b2c3d4e5f
Revises: 3c78baad7199
Create Date: 2026-08-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a1b2c3d4e5f"
down_revision: Union[str, None] = "3c78baad7199"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lectures",
        sa.Column(
            "ingestion_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "lectures",
        sa.Column(
            "chunk_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("lectures", "chunk_count")
    op.drop_column("lectures", "ingestion_status")
