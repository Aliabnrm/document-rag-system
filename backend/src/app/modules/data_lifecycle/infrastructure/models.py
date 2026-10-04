from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, TimestampMixin


class DeletionCleanupJobModel(TimestampMixin, Base):
    __tablename__ = "deletion_cleanup_jobs"
    __table_args__ = (
        CheckConstraint(
            "resource_type IN ('document','collection')",
            name="valid_resource_type",
        ),
        CheckConstraint(
            "status IN ('pending','running','succeeded','failed')",
            name="valid_status",
        ),
        CheckConstraint("attempt_count >= 0", name="non_negative_attempt_count"),
        UniqueConstraint("owner_id", "resource_type", "resource_id"),
        Index("ix_deletion_cleanup_dispatch", "status", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(24), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(nullable=False)
    storage_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
