"""add candidate learning activities

Revision ID: c9317a4d2e80
Revises: 8d14cb6f902a
Create Date: 2026-11-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9317a4d2e80"
down_revision: Union[str, Sequence[str], None] = "8d14cb6f902a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("skill", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=11), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_learning_activities_candidate_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_activities")),
    )
    op.create_index(
        "uq_learning_activity_candidate_resource",
        "learning_activities",
        ["candidate_id", "skill", "resource_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_learning_activities_candidate_id"),
        "learning_activities",
        ["candidate_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_learning_activity_candidate_resource",
        table_name="learning_activities",
    )
    op.drop_index(
        op.f("ix_learning_activities_candidate_id"),
        table_name="learning_activities",
    )
    op.drop_table("learning_activities")
