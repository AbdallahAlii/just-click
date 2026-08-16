
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Literal
import json

from dotenv import load_dotenv
from cryptography.fernet import Fernet
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SameSite = Literal["lax", "strict", "none"]
SessionBackend = Literal["cookie", "filesystem", "redis"]


def _backend_root() -> Path:
    # backend/src/cmcp/config/settings.py -> backend/
    return Path(__file__).resolve().parents[3]

ENV_PATH = Path(os.getenv("CMCP_ENV_FILE", _backend_root() / ".env")).resolve()

# 🔥 Hard fail early if missing (so you don't get mysterious "Field required")
if not ENV_PATH.exists():
    raise FileNotFoundError(
        f"Could not find .env file at: {ENV_PATH}\n"
        f"Create backend/.env (copy from .env.example) or set CMCP_ENV_FILE."
    )

load_dotenv(dotenv_path=ENV_PATH, override=False)

class Settings(BaseSettings):
    # ✅ pydantic will also read this exact file
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        extra="ignore",
    )

    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    SECRET_KEY: str = Field(..., min_length=16)
    SECURITY_PASSWORD_SALT: str = Field(..., min_length=8)
    ENCRYPTION_KEY: str = Field(..., min_length=44)  # Fernet key

    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_NAME: str

    DEFAULT_COMPANY_ID: Optional[int] = None

    # -------------------------
    # Redis (optional)
    # -------------------------
    REDIS_ENABLED: bool = True
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # -------------------------
    # Sessions (FAIL-SAFE DEFAULT)
    # -------------------------
    SESSION_BACKEND: SessionBackend = "cookie"
    SESSION_FILESYSTEM_DIR: str = ".flask_session"

    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_MAX_AGE: int = 60 * 60 * 24
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: SameSite = "lax"
    SESSION_COOKIE_DOMAIN: Optional[str] = None
    CROSS_SITE_COOKIES: bool = False

    @field_validator("SESSION_COOKIE_SAMESITE", mode="before")
    @classmethod
    def _normalize_samesite(cls, v):
        if not isinstance(v, str):
            return "lax"
        s = v.strip().lower()
        return s if s in {"lax", "strict", "none"} else "lax"

    @property
    def cookie_samesite_effective(self) -> SameSite:
        return "none" if self.CROSS_SITE_COOKIES else self.SESSION_COOKIE_SAMESITE

    @property
    def cookie_secure_effective(self) -> bool:
        return True if self.CROSS_SITE_COOKIES else self.SESSION_COOKIE_SECURE

    # -------------------------
    # CORS
    # -------------------------
    CORS_ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    CORS_ALLOW_ORIGIN_REGEX: Optional[str] = None

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                try:
                    arr = json.loads(s)
                    if isinstance(arr, list):
                        return [str(x).strip() for x in arr if str(x).strip()]
                except Exception:
                    pass
            return [p.strip() for p in s.split(",") if p.strip()]
        return ["http://localhost:3000"]

    # -------------------------
    # Chatbot / RAG
    # -------------------------
    DEEPSEEK_API_KEY: str = ""
    CHATBOT_LLM_BASE_URL: str = "https://api.deepseek.com"
    CHATBOT_LLM_MODEL: str = "deepseek-chat"

    ANONYMIZED_TELEMETRY: bool = False

    CHATBOT_VECTOR_DB: str = "chroma"
    CHATBOT_CHROMA_DIR: str = "instance/chroma_db"
    CHATBOT_COLLECTION_NAME: str = "cmcp_material_chunks_v3"

    CHATBOT_EMBEDDING_PROVIDER: str = "local_sentence_transformers"
    CHATBOT_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    CHATBOT_EMBEDDING_CACHE_DIR: str = "instance/embedding_models"
    CHATBOT_EMBEDDING_DEVICE: str = "cpu"
    CHATBOT_ALLOW_RUNTIME_MODEL_DOWNLOAD: bool = False
    CHATBOT_WARMUP_EMBEDDING: bool = True

    CHATBOT_TOP_K: int = 5
    CHATBOT_RELEVANCE_THRESHOLD: float = 1.3
    CHATBOT_MAX_CONTEXT_CHUNKS: int = 8
    CHATBOT_DEFAULT_SCOPE: str = "material"

    CHATBOT_CHUNK_SIZE: int = 400
    CHATBOT_CHUNK_OVERLAP: int = 80

    CHATBOT_INDEX_WORKER_POLL_SECONDS: int = 10
    CHATBOT_INDEX_WORKER_MAX_ATTEMPTS: int = 3
    CHATBOT_INDEX_WORKER_IDLE_UNLOAD_SECONDS: int = 60

    CHATBOT_LLM_TIMEOUT_SECONDS: float = 90.0
    CHATBOT_LLM_MAX_TOKENS_CHAT: int = 800
    CHATBOT_LLM_MAX_TOKENS_SUMMARY: int = 1200
    CHATBOT_LLM_MAX_TOKENS_QUIZ: int = 2500
    CHATBOT_LLM_MAX_TOKENS_QNA: int = 2500

    @field_validator(
        "ANONYMIZED_TELEMETRY",
        "CHATBOT_ALLOW_RUNTIME_MODEL_DOWNLOAD",
        "REDIS_ENABLED",
        "SESSION_COOKIE_HTTPONLY",
        "SESSION_COOKIE_SECURE",
        "CROSS_SITE_COOKIES",
        mode="before",
    )
    @classmethod
    def _parse_bool(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "on"}
        return bool(v)


settings = Settings()

try:
    FERNET_INSTANCE = Fernet(settings.ENCRYPTION_KEY.encode())
except Exception as e:
    raise ValueError("Invalid ENCRYPTION_KEY") from e
