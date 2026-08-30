"""A job a client wants done, and the photos that describe it."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RequestStatus, Urgency
from app.models.base import Base, PkMixin, TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.catalog import City, Trade
    from app.models.offer import Offer


class ServiceRequest(PkMixin, TimestampMixin, Base):
    """C1 creates one of these. M4 is a query over them."""

    __tablename__ = "requests"
    __table_args__ = (
        # The feed at M4 is "open requests, this trade, this city, newest first".
        Index("ix_requests_feed", "status", "trade_id", "city_id", "created_at"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    client_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trade_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("trades.id", ondelete="RESTRICT"), nullable=False
    )
    city_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    #: Full address. Shown to the tradesman only once his offer is accepted (M5).
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    urgency: Mapped[Urgency] = mapped_column(
        enum_column(Urgency), nullable=False, default=Urgency.FLEXIBLE
    )
    budget_min_centimes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    budget_max_centimes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    status: Mapped[RequestStatus] = mapped_column(
        enum_column(RequestStatus), nullable=False, default=RequestStatus.OPEN, index=True
    )
    #: Cache of `offers`, so the list at C2 needs one query rather than N.
    offers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    trade: Mapped[Trade] = relationship()
    city: Mapped[City] = relationship()

    photos: Mapped[list[RequestPhoto]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="RequestPhoto.sort_order"
    )
    offers: Mapped[list[Offer]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ServiceRequest {self.id} {self.status}>"


class RequestPhoto(PkMixin, TimestampMixin, Base):
    __tablename__ = "request_photos"

    request_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    request: Mapped[ServiceRequest] = relationship(back_populates="photos")
