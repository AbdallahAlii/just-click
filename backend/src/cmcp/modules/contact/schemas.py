from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


ALLOWED_STATUSES = {"open", "in_progress", "resolved", "spam"}


class ContactCreateIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    subject: str = Field(..., min_length=2, max_length=255)
    message: str = Field(..., min_length=5, max_length=5000)

    @field_validator("name", "subject", "message")
    @classmethod
    def strip_text(cls, v: str) -> str:
        text = (v or "").strip()
        if not text:
            raise ValueError("This field is required.")
        return text


class ContactStatusUpdateIn(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if s not in ALLOWED_STATUSES:
            raise ValueError("status must be open, in_progress, resolved, or spam.")
        return s


class ContactHandleIn(BaseModel):
    status: Optional[str] = None
    admin_notes: Optional[str] = Field(default=None, max_length=5000)
    admin_reply: Optional[str] = Field(default=None, max_length=5000)
    send_reply_email: bool = False

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None or str(v).strip() == "":
            return None
        s = str(v).strip().lower()
        if s not in ALLOWED_STATUSES:
            raise ValueError("status must be open, in_progress, resolved, or spam.")
        return s

    @field_validator("admin_notes", "admin_reply")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        text = str(v).strip()
        return text or None
