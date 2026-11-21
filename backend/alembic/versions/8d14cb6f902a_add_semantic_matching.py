"""add semantic matching storage

Revision ID: 8d14cb6f902a
Revises: 7c32b5e91a40
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = "8d14cb6f902a"
down_revision: Union[str, Sequence[str], None] = "7c32b5e91a40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EMBEDDING_DIMENSIONS = 384
_VECTOR_TYPE = Vector(_EMBEDDING_DIMENSIONS).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "jobs",
        sa.Column("required_skills", sa.JSON(), server_default="[]", nullable=False),
    )
    op.add_column(
        "jobs",
        sa.Column("minimum_experience_years", sa.Integer(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("required_education", sa.String(length=300), nullable=True),
    )
    op.create_table(
        "matching_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=True),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("embedding_kind", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", _VECTOR_TYPE, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(candidate_id IS NOT NULL AND job_id IS NULL) OR "
            "(candidate_id IS NULL AND job_id IS NOT NULL)",
            name=op.f("ck_matching_embeddings_single_embedding_owner"),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_matching_embeddings_candidate_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_matching_embeddings_job_id_jobs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_matching_embeddings")),
    )
    op.create_index(
        "uq_matching_embeddings_candidate_kind_model",
        "matching_embeddings",
        ["candidate_id", "embedding_kind", "model_name"],
        unique=True,
        sqlite_where=sa.text("candidate_id IS NOT NULL"),
        postgresql_where=sa.text("candidate_id IS NOT NULL"),
    )
    op.create_index(
        "uq_matching_embeddings_job_kind_model",
        "matching_embeddings",
        ["job_id", "embedding_kind", "model_name"],
        unique=True,
        sqlite_where=sa.text("job_id IS NOT NULL"),
        postgresql_where=sa.text("job_id IS NOT NULL"),
    )
    op.create_index(
        "ix_matching_embeddings_vector",
        "matching_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_table(
        "matching_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("score_details", sa.JSON(), nullable=False),
        sa.Column("scoring_model_version", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_matching_results_candidate_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_matching_results_job_id_jobs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            name=op.f("fk_matching_results_resume_id_resumes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_matching_results")),
    )
    op.create_index(
        "ix_matching_results_candidate_created",
        "matching_results",
        ["candidate_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_matching_results_candidate_created", table_name="matching_results")
    op.drop_table("matching_results")
    op.drop_index("ix_matching_embeddings_vector", table_name="matching_embeddings")
    op.drop_index(
        "uq_matching_embeddings_job_kind_model", table_name="matching_embeddings"
    )
    op.drop_index(
        "uq_matching_embeddings_candidate_kind_model", table_name="matching_embeddings"
    )
    op.drop_table("matching_embeddings")
    op.drop_column("jobs", "required_education")
    op.drop_column("jobs", "minimum_experience_years")
    op.drop_column("jobs", "required_skills")
