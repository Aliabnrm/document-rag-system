"""add durable deletion cleanup jobs

Revision ID: c4a8e2f1b6d3
Revises: 7d2f3a8c9e10
Create Date: 2026-09-26 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4a8e2f1b6d3"
down_revision: str | None = "7d2f3a8c9e10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deletion_cleanup_jobs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=24), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("storage_keys", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(length=80)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name=op.f("ck_deletion_cleanup_jobs_non_negative_attempt_count"),
        ),
        sa.CheckConstraint(
            "resource_type IN ('document','collection')",
            name=op.f("ck_deletion_cleanup_jobs_valid_resource_type"),
        ),
        sa.CheckConstraint(
            "status IN ('pending','running','succeeded','failed')",
            name=op.f("ck_deletion_cleanup_jobs_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_deletion_cleanup_jobs_owner_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deletion_cleanup_jobs")),
        sa.UniqueConstraint(
            "owner_id",
            "resource_type",
            "resource_id",
            name=op.f(
                "uq_deletion_cleanup_jobs_owner_id_resource_type_resource_id"
            ),
        ),
    )
    op.create_index(
        "ix_deletion_cleanup_dispatch",
        "deletion_cleanup_jobs",
        ["status", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_deletion_cleanup_dispatch", table_name="deletion_cleanup_jobs")
    op.drop_table("deletion_cleanup_jobs")
