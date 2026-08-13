# config/media_config.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


def _backend_root() -> Path:
    # .../backend/src/cmcp/config/media_config.py → backend/
    return Path(__file__).resolve().parents[3]


class MediaSettings(BaseSettings):
    MEDIA_BACKEND: str = "local"
    MEDIA_ALLOWED_EXTS: List[str] = Field(
        default_factory=lambda: [
            # images
            "png", "jpg", "jpeg", "webp",
            # docs
            "pdf", "doc", "docx",
            # slides
            "ppt", "pptx", "key",
            # video
            "mp4", "mkv", "mov",
            # spreadsheets
            "csv", "xlsx", "xls",
        ]
    )
    MEDIA_MAX_MB: int = 100
    S3_ENDPOINT_URL: Optional[str] = None
    S3_REGION: str = "us-east-1"
    S3_BUCKET: str = "erp-media"
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_PUBLIC_BASE: Optional[str] = None
    S3_SIGNED_URL_TTL: int = 300

    # Relative values resolve against the backend project root (not process cwd),
    # so API + chatbot index worker share the same media files.
    LOCAL_MEDIA_ROOT: str = "media"
    LOCAL_PUBLIC_BASE: str = "/media"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("LOCAL_MEDIA_ROOT", mode="after")
    @classmethod
    def resolve_local_media_root(cls, v: str) -> str:
        raw = (v or "media").strip() or "media"
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = _backend_root() / path
        return str(path.resolve())


settings = MediaSettings()