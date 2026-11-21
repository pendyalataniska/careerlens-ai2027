"""add resume analysis metadata

Revision ID: 7c32b5e91a40
Revises: ef47f8ad5182
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c32b5e91a40"
down_revision: Union[str, Sequence[str], None] = "ef47f8ad5182"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column("file_size_bytes", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "resumes",
        sa.Column("sha256_digest", sa.String(length=64), server_default="", nullable=False),
    )
    op.add_column(
        "resumes",
        sa.Column(
            "extraction_status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "resumes",
        sa.Column("extracted_data", sa.JSON(), server_default="{}", nullable=False),
    )
    op.add_column(
        "resumes",
        sa.Column(
            "contact_information_encrypted",
            sa.Text(),
            server_default="",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("resumes", "contact_information_encrypted")
    op.drop_column("resumes", "extracted_data")
    op.drop_column("resumes", "extraction_status")
    op.drop_column("resumes", "sha256_digest")
    op.drop_column("resumes", "file_size_bytes")
