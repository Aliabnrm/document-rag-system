"""add application-owned identity and opaque sessions

Revision ID: 9b4c0a2f5e8d
Revises: c804af32a091
Create Date: 2026-09-26 09:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9b4c0a2f5e8d"
down_revision: str | None = "c804af32a091"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=320), nullable=True))
    op.add_column("users", sa.Column("email_normalized", sa.String(length=320), nullable=True))
    op.add_column("users", sa.Column("display_name", sa.String(length=120), nullable=True))
    op.add_column(
        "users",
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
    )
    op.execute(
        "UPDATE users SET "
        "email = 'legacy-' || id::text || '@invalid.local', "
        "email_normalized = 'legacy-' || id::text || '@invalid.local' "
        "WHERE email IS NULL"
    )
    op.alter_column("users", "email", nullable=False)
    op.alter_column("users", "email_normalized", nullable=False)
    op.create_unique_constraint(op.f("uq_users_email_normalized"), "users", ["email_normalized"])
    op.create_check_constraint(
        op.f("ck_users_valid_status"), "users", "status IN ('active','disabled')"
    )

    op.create_table(
        "password_credentials",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_password_credentials_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_password_credentials")),
    )
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email_normalized", sa.String(length=320), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_sessions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_digest", name=op.f("uq_sessions_token_digest")),
    )
    op.create_index("ix_sessions_user_active", "sessions", ["user_id", "revoked_at"], unique=False)
    op.create_index(
        "ix_sessions_expiry",
        "sessions",
        ["idle_expires_at", "absolute_expires_at"],
        unique=False,
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_password_reset_tokens_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_tokens")),
        sa.UniqueConstraint("token_digest", name=op.f("uq_password_reset_tokens_token_digest")),
    )
    op.create_index(
        "ix_password_reset_user_state",
        "password_reset_tokens",
        ["user_id", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_user_state", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_sessions_expiry", table_name="sessions")
    op.drop_index("ix_sessions_user_active", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_invitations_email_state", table_name="invitations")
    op.drop_table("invitations")
    op.drop_table("password_credentials")
    op.drop_constraint(op.f("ck_users_valid_status"), "users", type_="check")
    op.drop_constraint(op.f("uq_users_email_normalized"), "users", type_="unique")
    op.drop_column("users", "status")
    op.drop_column("users", "display_name")
    op.drop_column("users", "email_normalized")
    op.drop_column("users", "email")
