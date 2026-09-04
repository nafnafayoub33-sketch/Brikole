"""The tradesman: his profile, his trades, his portfolio."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ProviderStatus
from app.models.base import Base, PkMixin, TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.catalog import City, Trade
    from app.models.user import User

#: Which trades a tradesman works in. A plumber who also paints is one account.
provider_trades = Table(
    "provider_trades",
    Base.metadata,
    Column(
        "provider_id",
        BigInteger,
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("trade_id", BigInteger, ForeignKey("trades.id", ondelete="CASCADE"), primary_key=True),
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_unicode_ci",
)


class ProviderProfile(PkMixin, TimestampMixin, Base):
    __tablename__ = "provider_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_provider_profiles_user_id"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    city_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    #: How far he is willing to travel. Bounds the feed at M4.
    radius_km: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    #: The one line a client reads before anything else — "Plomberie et
    #: dépannage, 7j/7". It is what turns a row in a table into a card worth
    #: clicking, so it is a column rather than the first line of the bio.
    headline: Mapped[str | None] = mapped_column(String(160), nullable=True)
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    #: What he charges to turn up and look, or his usual floor. Optional: the
    #: price of the job itself is still decided per request, in an offer. Null
    #: means he would rather not say, and the card simply omits it.
    starting_price_centimes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    #: Private — the bucket it lives in is never public-read. Admins only (A2).
    id_card_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[ProviderStatus] = mapped_column(
        enum_column(ProviderStatus), nullable=False, default=ProviderStatus.PENDING, index=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Caches of the reviews and jobs tables, kept for sorting search results.
    rating_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_cancelled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    #: Paid placement runs until this moment and then simply stops — nothing
    #: sweeps it, because a boost that has run out is a comparison against the
    #: clock and not a state anybody has to remember to clear.
    boosted_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="provider_profile", foreign_keys=[user_id])
    city: Mapped[City] = relationship(back_populates="providers")
    trades: Mapped[list[Trade]] = relationship(secondary=provider_trades, lazy="selectin")
    photos: Mapped[list[ProviderPhoto]] = relationship(
        back_populates="provider", cascade="all, delete-orphan", order_by="ProviderPhoto.sort_order"
    )

    @property
    def is_approved(self) -> bool:
        return self.status is ProviderStatus.APPROVED

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProviderProfile {self.id} user={self.user_id} {self.status}>"


class ProviderPhoto(PkMixin, TimestampMixin, Base):
    """A photo of past work. Public — this is the shop window at P3."""

    __tablename__ = "provider_photos"

    provider_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    provider: Mapped[ProviderProfile] = relationship(back_populates="photos")
