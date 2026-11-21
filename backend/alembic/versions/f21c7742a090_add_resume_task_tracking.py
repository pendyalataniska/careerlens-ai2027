"""add background resume task tracking

Revision ID: f21c7742a090
Revises: be3d84a91f62
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f21c7742a090"
down_revision: Union[str, Sequence[str], None] = "be3d84a91f62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column("task_id", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resumes", "task_id")
