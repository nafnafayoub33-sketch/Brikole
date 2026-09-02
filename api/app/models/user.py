"""The account. One row per phone number, whatever the role."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import Role, UserStatus
from app.models.base import Base, PkMixin, TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.catalog import City
    from app.models.provider import ProviderProfile


class User(PkMixin, TimestampMixin, Base):
    __tablename__ = "users"

    #: E.164, always. `app.core.phone.normalise_phone` is the only way in.
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)

    #: Set at registration, changeable only by an admin (A3).
    role: Mapped[Role] = mapped_column(enum_column(Role), nullable=False, index=True)
    status: Mapped[UserStatus] = mapped_column(
        enum_column(UserStatus), nullable=False, default=UserStatus.ACTIVE, index=True
    )

    city_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cities.id", ondelete="SET NULL"), nullable=True
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str] = mapped_column(String(2), nullable=False, default="ar")

    # Sign-in throttling. Counted server-side, because a counter in the browser
    # protects nobody.
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Suspension. `suspended_until` null on a suspended account means permanent.
    suspended_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    city: Mapped[City | None] = relationship(lazy="joined")

    provider_profile: Mapped[ProviderProfile | None] = relationship(
        back_populates="user",
        uselist=False,
        foreign_keys="ProviderProfile.user_id",
        cascade="all, delete-orphan",
    )

    @property
    def is_staff(self) -> bool:
        return self.role in (Role.MODERATOR, Role.ADMIN)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.id} {self.phone} {self.role}>"
