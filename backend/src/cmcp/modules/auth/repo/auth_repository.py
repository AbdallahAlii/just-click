from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from cmcp.config.database import db
from cmcp.modules.auth.models import User, UserAffiliation


class AuthRepository:
    """
    Minimal queries for auth:
    - user by username/id (with affiliations)
    """

    def get_user_by_username(self, username: str) -> Optional[User]:
        if not username:
            return None
        u = username.strip()

        stmt = (
            select(User)
            .options(selectinload(User.affiliations))
            .where(func.lower(User.username) == func.lower(u))
        )
        return db.session.scalar(stmt)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.affiliations))
            .where(User.id == int(user_id))
        )
        return db.session.scalar(stmt)

    def get_user_by_email(self, email: str) -> Optional[User]:
        if not email:
            return None
        e = email.strip().lower()
        stmt = (
            select(User)
            .options(selectinload(User.affiliations))
            .where(func.lower(User.email) == e)
        )
        return db.session.scalar(stmt)

    def get_user_by_password_reset_token_hash(self, token_hash: str) -> Optional[User]:
        if not token_hash:
            return None
        stmt = (
            select(User)
            .options(selectinload(User.affiliations))
            .where(User.password_reset_token_hash == token_hash)
        )
        return db.session.scalar(stmt)

    def update_last_login(self, user: User) -> None:
        from datetime import datetime, timezone
        user.last_login = datetime.now(timezone.utc)
