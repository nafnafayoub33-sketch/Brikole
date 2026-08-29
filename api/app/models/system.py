"""Settings, the audit trail, and notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import NotificationKind
from app.models.base import Base, PkMixin, TimestampMixin, enum_column


class PlatformSetting(TimestampMixin, Base):
    """Key/value, edited at A7. Values are JSON so a setting can be a number,
    a flag, or the bank details block shown at M9."""

    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PlatformSetting {self.key}>"


class AuditLog(PkMixin, Base):
    """Every staff action that changes another user's state lands here.

    Append-only, and never deletable from the UI. `before` and `after` hold just
    the fields that moved, not whole rows.
    """

    __tablename__ = "audit_log"

    actor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    before: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    after: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)  # fits IPv6
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.action} {self.target_type}:{self.target_id}>"


class Notification(PkMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[NotificationKind] = mapped_column(enum_column(NotificationKind), nullable=False)
    #: Ids and numbers the web app interpolates into its own translated string.
    #: The API never ships a sentence.
    payload: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
