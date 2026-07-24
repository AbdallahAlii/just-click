from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Index, BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from cmcp.config.database import db
from cmcp.common.models.base import BaseModel, TenantMixin


class NotificationEventType(str, enum.Enum):
    MATERIAL_CREATED = "material_created"
    MATERIAL_UPDATED = "material_updated"
    ADMIN_BROADCAST = "admin_broadcast"


class PushOutboxStatus:
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class NotificationBatch(BaseModel, TenantMixin):
    """Groups a broadcast (auto material or admin manual)."""
    __tablename__ = "notification_batches"

    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(db.String(50), nullable=False, index=True)
    channels_json: Mapped[str] = mapped_column(db.String(120), nullable=False, default='["in_app"]')

    material_id: Mapped[Optional[int]] = mapped_column(
        db.BigInteger,
        db.ForeignKey("edu_materials.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    recipient_count: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    in_app_count: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    email_count: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    push_count: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_notification_batches_company_created", "company_id", "created_at"),
    )


class UserNotification(BaseModel, TenantMixin):
    """In-app notification for a single user."""
    __tablename__ = "user_notifications"

    user_id: Mapped[int] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[Optional[int]] = mapped_column(
        db.BigInteger,
        db.ForeignKey("notification_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(db.String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    material_id: Mapped[Optional[int]] = mapped_column(db.BigInteger, nullable=True, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("ix_user_notifications_user_unread", "company_id", "user_id", "read_at"),
    )


class UserDeviceToken(BaseModel, TenantMixin):
    """Mobile push token (FCM)."""
    __tablename__ = "user_device_tokens"

    user_id: Mapped[int] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(db.String(512), nullable=False)
    platform: Mapped[str] = mapped_column(db.String(20), nullable=False, default="android")
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True, index=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_user_device_tokens_user_token", "company_id", "user_id", "token", unique=True),
    )


class PushOutbox(BaseModel, TenantMixin):
    """Async push delivery queue (processed by notification_worker)."""
    __tablename__ = "push_outbox"

    user_id: Mapped[int] = mapped_column(db.BigInteger, nullable=False, index=True)
    device_token: Mapped[str] = mapped_column(db.String(512), nullable=False)
    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(db.String(20), nullable=False, default=PushOutboxStatus.PENDING, index=True)
    tries: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(db.String(800), nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    notification_id: Mapped[Optional[int]] = mapped_column(db.BigInteger, nullable=True, index=True)
    batch_id: Mapped[Optional[int]] = mapped_column(db.BigInteger, nullable=True, index=True)

    __table_args__ = (
        Index("ix_push_outbox_status_created", "status", "created_at"),
    )
