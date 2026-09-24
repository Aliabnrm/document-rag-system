"""add ingestion dispatch recovery fields

Revision ID: c804af32a091
Revises: aa781185f5eb
Create Date: 2026-09-24 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c804af32a091"
down_revision: str | None = "aa781185f5eb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ingestion_jobs",
        sa.Column("dispatch_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_ingestion_jobs_non_negative_dispatch_count"),
        "ingestion_jobs",
        "dispatch_count >= 0",
    )
    op.create_index(
        "ix_ingestion_jobs_dispatch_recovery",
        "ingestion_jobs",
        ["status", "stage", "dispatched_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_jobs_dispatch_recovery", table_name="ingestion_jobs")
    op.drop_constraint(
        op.f("ck_ingestion_jobs_non_negative_dispatch_count"),
        "ingestion_jobs",
        type_="check",
    )
    op.drop_column("ingestion_jobs", "dispatched_at")
    op.drop_column("ingestion_jobs", "dispatch_count")
