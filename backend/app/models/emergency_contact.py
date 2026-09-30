"""Emergency contact database model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, orm
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class EmergencyContact(Base):
    """Emergency contacts for critical clinical escalations and SOS."""

    __tablename__ = "emergency_contacts"

    id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: orm.Mapped[str] = orm.mapped_column(String(255), nullable=False)
    relationship: orm.Mapped[str] = orm.mapped_column(String(100), nullable=False)
    phone_number: orm.Mapped[str] = orm.mapped_column(String(30), nullable=False)
    is_primary: orm.Mapped[bool] = orm.mapped_column(Boolean, default=False, nullable=False)

    created_at: orm.Mapped[datetime] = orm.mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: orm.Mapped[datetime] = orm.mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: orm.Mapped["User"] = orm.relationship("User", back_populates="emergency_contacts")
