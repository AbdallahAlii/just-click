from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cmcp.modules.materials.schemas import _BaseIn


ALLOWED_FEEDBACK_TYPES = {"rating", "comment", "broken_file", "clarification"}


class MaterialFeedbackCreateIn(_BaseIn):
    feedback_type: str
    rating: Optional[int] = None
    message: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, v: str) -> str:
        s = str(v or "").strip().lower()
        if s not in ALLOWED_FEEDBACK_TYPES:
            raise ValueError("feedback_type must be rating, comment, broken_file, or clarification.")
        return s

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[int], info):
        feedback_type = (info.data or {}).get("feedback_type")
        if feedback_type == "rating":
            if v is None:
                raise ValueError("rating is required for rating feedback.")
            if v < 1 or v > 5:
                raise ValueError("rating must be between 1 and 5.")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: Optional[str], info):
        feedback_type = (info.data or {}).get("feedback_type")
        if feedback_type in {"comment", "broken_file", "clarification"}:
            text = (v or "").strip()
            if not text:
                raise ValueError("message is required for this feedback type.")
            if len(text) > 2000:
                raise ValueError("message is too long.")
            return text
        return (v or "").strip() or None


class MaterialFeedbackReplyIn(_BaseIn):
    admin_reply: str = Field(..., min_length=1, max_length=2000)


class MaterialFeedbackDiscussionReplyIn(_BaseIn):
    message: str = Field(..., min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        text = (v or "").strip()
        if not text:
            raise ValueError("message is required.")
        if len(text) > 2000:
            raise ValueError("message is too long.")
        return text


class MaterialFeedbackResolveIn(_BaseIn):
    admin_reply: Optional[str] = Field(default=None, max_length=2000)
