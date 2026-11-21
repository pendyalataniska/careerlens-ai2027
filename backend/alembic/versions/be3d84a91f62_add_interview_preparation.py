"""add Gemini interview preparation sessions and question evaluations

Revision ID: be3d84a91f62
Revises: c9317a4d2e80
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "be3d84a91f62"
down_revision: Union[str, Sequence[str], None] = "c9317a4d2e80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("job_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "interview_sessions",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_interview_sessions_job_id_jobs"),
            "jobs",
            ["job_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("targeted_skills", sa.JSON(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("evaluation", sa.JSON(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["interview_sessions.id"],
            name=op.f("fk_interview_questions_session_id_interview_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_questions")),
        sa.UniqueConstraint(
            "session_id", "position", name="uq_interview_question_session_position"
        ),
    )
    op.create_index(
        op.f("ix_interview_questions_session_id"),
        "interview_questions",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_interview_questions_session_id"),
        table_name="interview_questions",
    )
    op.drop_table("interview_questions")
    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_interview_sessions_job_id_jobs"),
            type_="foreignkey",
        )
    op.drop_column("interview_sessions", "completed_at")
    op.drop_column("interview_sessions", "job_id")
