"""add collection and document tombstones

Revision ID: 41c7e6d9a2bf
Revises: 9b4c0a2f5e8d
Create Date: 2026-09-26 10:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "41c7e6d9a2bf"
down_revision: str | None = "9b4c0a2f5e8d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("collections", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.add_column("documents", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.create_index("ix_collections_owner_deleted", "collections", ["owner_id", "deleted_at"])
    op.create_index("ix_documents_collection_deleted", "documents", ["collection_id", "deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_documents_collection_deleted", table_name="documents")
    op.drop_index("ix_collections_owner_deleted", table_name="collections")
    op.drop_column("documents", "deleted_at")
    op.drop_column("collections", "deleted_at")
