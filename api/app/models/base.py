"""Declarative base, shared column helpers, and the project's time rule."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import BigInteger, DateTime, MetaData
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming every constraint means Alembic can always find one to drop, on MySQL
# where anonymous constraints are otherwise unaddressable.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    """Naive UTC.

    MySQL's DATETIME carries no timezone, so the whole database is UTC and the
    conversion to the reader's clock happens in the browser. Storing an aware
    datetime here would be silently truncated, which is worse than being
    explicit about it.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # utf8mb4 or Arabic and emoji both break. Set per table, not per install.
    __table_args__: Any = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


def enum_column(enum_cls: type[StrEnum], length: int = 32) -> SAEnum:
    """A StrEnum as VARCHAR + CHECK rather than a native MySQL ENUM.

    Native ENUM needs a table rebuild to add a value and reports itself
    differently across MySQL and MariaDB; a checked VARCHAR migrates cleanly on
    both.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [member.value for member in e],
        validate_strings=True,
    )


class PkMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
