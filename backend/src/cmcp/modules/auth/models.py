# app/apps/auth/models.py
from __future__ import annotations

from typing import Optional
from datetime import datetime
import enum

from sqlalchemy import UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cmcp.config.database import db
from cmcp.common.models.base import BaseModel


class UserTypeEnum(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    STAFF = "staff"
    ADMIN = "admin"


class UserStatusEnum(str, enum.Enum):
    PENDING_EMAIL = "pending_email"          # registered, must verify email
    PENDING_APPROVAL = "pending_approval"    # email verified, waiting admin
    ACTIVE = "active"                        # approved, can login
    REJECTED = "rejected"                    # rejected by admin


class LinkedEntityTypeEnum(str, enum.Enum):
    STUDENT_PROFILE = "student_profile"
    STAFF_PROFILE = "staff_profile"


class User(BaseModel):
    __tablename__ = "users"

    # Login is ONLY username (for students: student_id)
    username: Mapped[str] = mapped_column(db.String(150), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)

    # Email is CONTACT + VERIFICATION only (not login)
    email: Mapped[str] = mapped_column(db.String(255), nullable=False, index=True)

    user_type: Mapped[UserTypeEnum] = mapped_column(
        db.Enum(UserTypeEnum, name="user_type_enum"),
        nullable=False,
        index=True,
    )

    status: Mapped[UserStatusEnum] = mapped_column(
        db.Enum(UserStatusEnum, name="user_status_enum"),
        nullable=False,
        default=UserStatusEnum.PENDING_EMAIL,
        index=True,
    )

    is_system_owner: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)

    # Auth / lifecycle
    last_login: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    # IMPORTANT: starts disabled until approved
    is_enabled: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)

    # Email verification lifecycle
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    # store HASH only (never store raw token)
    email_verify_token_hash: Mapped[Optional[str]] = mapped_column(db.String(255), nullable=True, index=True)
    email_verify_expires_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    # Self-service password reset (separate from email verification / temp-password approval)
    password_reset_token_hash: Mapped[Optional[str]] = mapped_column(db.String(255), nullable=True, index=True)
    password_reset_expires_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    # Admin approval audit
    approved_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    rejected_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[Optional[int]] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(db.String(500), nullable=True)

    # Temp password flow (optional but useful for your approval email)
    must_change_password: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)
    temp_password_expires_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    affiliations: Mapped[list["UserAffiliation"]] = db.relationship(
        "UserAffiliation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_enabled", "is_enabled"),
        Index("ix_users_status", "status"),
        Index("ix_users_type", "user_type"),
    )


class UserAffiliation(BaseModel):
    """
    Links a global User to a Company (University).
    Also links to the actual profile record (StudentProfile or StaffProfile) using polymorphic reference.
    """
    __tablename__ = "user_affiliations"

    user_id: Mapped[int] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company_id: Mapped[int] = mapped_column(
        db.BigInteger,
        db.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_primary: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)

    # IMPORTANT: disabled until approved
    is_enabled: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)

    is_company_owner: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)

    linked_entity_type: Mapped[Optional[LinkedEntityTypeEnum]] = mapped_column(
        db.Enum(LinkedEntityTypeEnum, name="linked_entity_type_enum"),
        nullable=True,
        index=True,
    )
    linked_entity_id: Mapped[Optional[int]] = mapped_column(db.BigInteger, nullable=True, index=True)

    user: Mapped["User"] = db.relationship("User", back_populates="affiliations", lazy="select")

    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_affiliation_user_company"),
        CheckConstraint(
            "(linked_entity_type is null and linked_entity_id is null) OR "
            "(linked_entity_type is not null and linked_entity_id is not null)",
            name="ck_user_affiliation_linked_entity_pair",
        ),
        Index("ix_user_aff_company_user", "company_id", "user_id"),
        Index("ix_user_aff_enabled", "company_id", "is_enabled"),
    )
