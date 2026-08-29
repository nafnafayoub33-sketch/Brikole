"""Every query about users. Nothing else writes SQL against them."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import Role, UserStatus
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.provider_profile))
            .where(User.id == user_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_phone(self, phone: str) -> User | None:
        """`phone` must already be E.164 — callers normalise at the edge."""
        stmt = (
            select(User)
            .options(selectinload(User.provider_profile))
            .where(User.phone == phone)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def phone_exists(self, phone: str) -> bool:
        stmt = select(User.id).where(User.phone == phone).limit(1)
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def add(
        self,
        *,
        phone: str,
        password_hash: str,
        full_name: str,
        role: Role,
        language: str = "ar",
        status: UserStatus = UserStatus.ACTIVE,
        city_id: int | None = None,
    ) -> User:
        user = User(
            phone=phone,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            language=language,
            status=status,
            city_id=city_id,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def record_failed_login(self, user: User, *, locked_until: datetime | None) -> None:
        user.failed_login_attempts += 1
        if locked_until is not None:
            user.locked_until = locked_until
            # The lock has been applied; the next attempt starts a fresh count.
            user.failed_login_attempts = 0

    def record_successful_login(self, user: User, *, now: datetime) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
