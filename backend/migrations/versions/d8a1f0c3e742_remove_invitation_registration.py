"""remove invitation-gated registration

Revision ID: d8a1f0c3e742
Revises: c4a8e2f1b6d3
Create Date: 2026-09-26 20:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8a1f0c3e742"
down_revision: str | None = "c4a8e2f1b6d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_invitations_email_state", table_name="invitations")
    op.drop_table("invitations")


def downgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email_normalized", sa.String(length=320), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invitations")),
        sa.UniqueConstraint("token_digest", name=op.f("uq_invitations_token_digest")),
    )
    op.create_index(
        "ix_invitations_email_state",
        "invitations",
        ["email_normalized", "expires_at"],
        unique=False,
    )
