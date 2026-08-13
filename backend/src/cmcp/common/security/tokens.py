from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(int(length))


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def verify_token(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), token_hash)


@dataclass(frozen=True)
class TokenWithExpiry:
    token: str
    token_hash: str
    expires_at: datetime


def generate_email_verify_token(ttl_minutes: int = 30) -> TokenWithExpiry:
    tok = generate_token(32)
    exp = _utcnow() + timedelta(minutes=int(ttl_minutes))
    return TokenWithExpiry(token=tok, token_hash=hash_token(tok), expires_at=exp)


def generate_password_reset_token(ttl_minutes: int = 60) -> TokenWithExpiry:
    """Secure one-time password-reset token (hashed at rest)."""
    tok = generate_token(32)
    exp = _utcnow() + timedelta(minutes=int(ttl_minutes))
    return TokenWithExpiry(token=tok, token_hash=hash_token(tok), expires_at=exp)