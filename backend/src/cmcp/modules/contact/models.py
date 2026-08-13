from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from cmcp.config.database import db
from cmcp.common.models.base import BaseModel


def _enum_values(enum_cls):
    return [item.value for item in enum_cls]


class ContactMessageStatusEnum(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    SPAM = "spam"


class ContactMessage(BaseModel):
    """Public Contact Us submissions."""

    __tablename__ = "contact_messages"

    name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    email: Mapped[str] = mapped_column(db.String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(db.String(255), nullable=False)
    message: Mapped[str] = mapped_column(db.Text, nullable=False)

    status: Mapped[ContactMessageStatusEnum] = mapped_column(
        db.Enum(
            ContactMessageStatusEnum,
            name="contact_message_status_enum",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ContactMessageStatusEnum.OPEN,
        index=True,
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[Optional[int]] = mapped_column(
        db.BigInteger,
        db.ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    admin_notes: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    admin_reply: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    handled_by_user_id: Mapped[Optional[int]] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    handled_at: Mapped[Optional[datetime]] = mapped_column(
        db.DateTime(timezone=True),
        nullable=True,
    )
