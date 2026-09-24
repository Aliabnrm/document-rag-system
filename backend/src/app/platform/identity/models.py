from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, TimestampMixin


class UserModel(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
