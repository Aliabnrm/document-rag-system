"""add structured answer feedback

Revision ID: 7d2f3a8c9e10
Revises: 41c7e6d9a2bf
Create Date: 2026-09-26 10:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7d2f3a8c9e10"
down_revision: str | None = "41c7e6d9a2bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "answer_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("answer_message_id", sa.Uuid(), nullable=False),
        sa.Column("rag_run_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("pipeline_metadata", postgresql.JSONB(), nullable=False),
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
        sa.CheckConstraint("rating IN (-1, 1)", name=op.f("ck_answer_feedback_valid_rating")),
        sa.ForeignKeyConstraint(
            ["answer_message_id"],
            ["messages.id"],
            ondelete="CASCADE",
            name=op.f("fk_answer_feedback_answer_message_id_messages"),
        ),
        sa.ForeignKeyConstraint(
            ["rag_run_id"],
            ["rag_runs.id"],
            ondelete="CASCADE",
            name=op.f("fk_answer_feedback_rag_run_id_rag_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_answer_feedback_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_answer_feedback")),
        sa.UniqueConstraint(
            "user_id",
            "answer_message_id",
            name=op.f("uq_answer_feedback_user_id_answer_message_id"),
        ),
    )


def downgrade() -> None:
    op.drop_table("answer_feedback")
