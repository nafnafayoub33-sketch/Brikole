"""Trades and cities — the two lists everything else points at."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PkMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.provider import ProviderProfile


class Trade(PkMixin, TimestampMixin, Base):
    """A craft: plumber, painter, carpenter, mobile car wash…

    Names are stored in the three languages rather than as i18n keys, because an
    admin adds a trade at runtime (A6) and cannot ship a translation file.
    """

    __tablename__ = "trades"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    name_fr: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    icon: Mapped[str] = mapped_column(String(64), nullable=False, default="tool")

    #: Overrides the platform default when set. Null means "use the default".
    lead_fee_centimes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Trade {self.slug}>"


class City(PkMixin, TimestampMixin, Base):
    __tablename__ = "cities"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    name_fr: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    providers: Mapped[list[ProviderProfile]] = relationship(back_populates="city")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<City {self.slug}>"
