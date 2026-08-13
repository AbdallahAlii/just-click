from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional

from flask import session
from sqlalchemy.exc import SQLAlchemyError

from cmcp.config.database import db
from cmcp.modules.auth.repo.auth_repository import AuthRepository
from cmcp.modules.auth.models import UserStatusEnum
from cmcp.common.security.passwords import verify_password, hash_password
from cmcp.common.security.password_rules import ensure_password_ok
from cmcp.common.security.tokens import (
    generate_password_reset_token,
    hash_token,
    verify_token,
)
from cmcp.common.email.service import EmailService
from cmcp.common.validation.text import normalize_email

from cmcp.common.cache import cached_user_profile, bump_user_profile
from cmcp.common.cache.session_manager import (
    index_current_session,
    set_cached_user_status,
    remove_session,
)

from cmcp.security.rbac_context import build_auth_context

log = logging.getLogger(__name__)

_NEUTRAL_FORGOT_MSG = (
    "If an account exists for this email, password reset instructions have been sent."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _frontend_base_url() -> str:
    return (
        os.getenv("APP_BASE_URL")
        or os.getenv("FRONTEND_BASE_URL")
        or "http://localhost:3000"
    ).rstrip("/")


class AuthService:
    def __init__(self, repo: Optional[AuthRepository] = None):
        self.repo = repo or AuthRepository()
        self.email_svc = EmailService(
            session=db.session,
            provider=os.getenv("MAIL_PROVIDER", "smtp"),
            from_email=os.getenv("MAIL_FROM_EMAIL", ""),
            from_name=os.getenv("MAIL_FROM_NAME", "JustClick"),
            max_tries=int(os.getenv("EMAIL_OUTBOX_MAX_TRIES", "5")),
        )

    def login(
        self, *, username: str, password: str, company_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        user = self.repo.get_user_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            return False, "Invalid username or password.", None

        if not user.is_enabled:
            return False, "Your account is disabled.", None

        try:
            self.repo.update_last_login(user)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            return False, "A database error occurred during login.", None

        # bust profile cache (company-aware)
        bump_user_profile(int(user.id), company_id)

        prof_wrap = self.get_cached_profile(int(user.id), company_id=company_id)
        if not prof_wrap.get("ok"):
            return False, prof_wrap.get("message", "Profile error."), None

        profile = prof_wrap["profile"]

        # session set (cookie session is default now)
        session.clear()
        session["user_id"] = int(user.id)
        session["company_id"] = int(company_id) if company_id is not None else None

        # ✅ session_version support (safe if column not yet added)
        # if you add User.session_version later, it starts working automatically
        sv = int(getattr(user, "session_version", 0) or 0)
        session["sv"] = sv

        session.permanent = True

        # best-effort session indexing (should be Redis-optional too)
        try:
            index_current_session(int(user.id))
            set_cached_user_status(int(user.id), "enabled")
        except Exception:
            log.warning("Failed to index session / set status.", exc_info=True)

        return True, "Login successful.", profile

    def logout(self) -> Tuple[bool, str]:
        uid = session.get("user_id")
        if uid:
            try:
                remove_session(int(uid))
            except Exception:
                log.warning("Failed to remove session.", exc_info=True)

        session.clear()
        session.permanent = False
        return True, "Logout successful."

    def build_user_profile_dict(self, user_id: int, company_id: Optional[int]) -> Dict[str, Any]:
        user = self.repo.get_user_by_id(int(user_id))
        if not user:
            return {"ok": False, "message": "User not found"}

        ctx = build_auth_context(user_id=int(user.id), company_id=company_id)

        affiliations = []
        for a in (user.affiliations or []):
            affiliations.append(
                {
                    "id": int(a.id),
                    "company_id": int(a.company_id),
                    "is_primary": bool(a.is_primary),
                    "is_enabled": bool(a.is_enabled),
                    "is_company_owner": bool(getattr(a, "is_company_owner", False)),
                    "linked_entity_type": a.linked_entity_type.value if a.linked_entity_type else None,
                    "linked_entity_id": int(a.linked_entity_id) if a.linked_entity_id is not None else None,
                }
            )

        return {
            "ok": True,
            "profile": {
                "user_id": int(user.id),
                "username": str(user.username),
                "user_type": str(user.user_type.value),
                "is_system_owner": bool(getattr(user, "is_system_owner", False)),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "affiliations": affiliations,
                "active_company_id": ctx.active_company_id,
                "roles": ctx.roles,
                "permissions": sorted(list(ctx.permissions or [])),
                "is_company_admin": bool(ctx.is_company_admin),
            },
        }

    def get_cached_profile(self, user_id: int, company_id: Optional[int] = None) -> Dict[str, Any]:
        return cached_user_profile(
            user_id=int(user_id),
            company_id=company_id,
            builder=lambda: self.build_user_profile_dict(int(user_id), company_id),
            ttl=3 * 3600,
        )

    def _display_name_for_user(self, user) -> str:
        try:
            from cmcp.modules.education_people.models import StudentProfile, StaffProfile

            student = (
                db.session.query(StudentProfile.full_name)
                .filter(StudentProfile.user_id == int(user.id))
                .first()
            )
            if student and student[0]:
                return str(student[0])

            staff = (
                db.session.query(StaffProfile.full_name)
                .filter(StaffProfile.user_id == int(user.id))
                .first()
            )
            if staff and staff[0]:
                return str(staff[0])
        except Exception:
            log.debug("Could not resolve display name for password reset.", exc_info=True)
        return str(user.username)

    def request_password_reset(self, *, email: str) -> Tuple[bool, str]:
        """
        Always returns a neutral success message (no account enumeration).
        Queues reset email via EmailOutbox when a resettable account exists.
        """
        try:
            normalized = normalize_email(email)
        except Exception:
            return True, _NEUTRAL_FORGOT_MSG

        user = self.repo.get_user_by_email(normalized)
        if not user or not user.is_enabled or user.status != UserStatusEnum.ACTIVE:
            return True, _NEUTRAL_FORGOT_MSG

        ttl = int(os.getenv("PASSWORD_RESET_TOKEN_TTL_MINUTES", "60"))
        tok = generate_password_reset_token(ttl_minutes=ttl)
        reset_link = f"{_frontend_base_url()}/reset-password?token={tok.token}"

        try:
            user.password_reset_token_hash = tok.token_hash
            user.password_reset_expires_at = tok.expires_at

            self.email_svc.enqueue(
                to_email=user.email,
                subject="Reset your JustClick password",
                template="password_reset",
                payload={
                    "full_name": self._display_name_for_user(user),
                    "username": user.username,
                    "reset_link": reset_link,
                    "expires_minutes": ttl,
                },
                ref_type="User",
                ref_id=int(user.id),
            )
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            log.exception("Failed to queue password reset for user_id=%s", getattr(user, "id", None))
            # Still neutral — do not reveal failure type to client
            return True, _NEUTRAL_FORGOT_MSG

        return True, _NEUTRAL_FORGOT_MSG

    def reset_password_with_token(
        self, *, token: str, new_password: str, confirm_password: str
    ) -> Tuple[bool, str]:
        raw = (token or "").strip()
        if not raw:
            return False, "Invalid or expired password reset link."

        if (new_password or "") != (confirm_password or ""):
            return False, "Passwords do not match."

        try:
            ensure_password_ok(new_password)
        except Exception as e:
            return False, getattr(e, "description", None) or str(e) or "Invalid password."

        token_hash = hash_token(raw)
        user = self.repo.get_user_by_password_reset_token_hash(token_hash)
        if not user or not user.password_reset_token_hash or not user.password_reset_expires_at:
            return False, "Invalid or expired password reset link."

        expires = user.password_reset_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if _utcnow() > expires:
            user.password_reset_token_hash = None
            user.password_reset_expires_at = None
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
            return False, "Invalid or expired password reset link."

        if not verify_token(raw, user.password_reset_token_hash):
            return False, "Invalid or expired password reset link."

        try:
            user.password_hash = hash_password(new_password)
            user.password_reset_token_hash = None
            user.password_reset_expires_at = None
            user.must_change_password = False
            user.temp_password_expires_at = None
            if hasattr(user, "session_version"):
                user.session_version = int(getattr(user, "session_version", 0) or 0) + 1
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            log.exception("Failed to reset password for user_id=%s", getattr(user, "id", None))
            return False, "Could not reset password. Please try again."

        try:
            bump_user_profile(int(user.id), None)
            remove_session(int(user.id))
        except Exception:
            log.warning("Post password-reset session cleanup failed.", exc_info=True)

        return True, "Password reset successfully. You can now sign in."
