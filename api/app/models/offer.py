"""A tradesman's priced answer to a request."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OfferStatus
from app.models.base import Base, PkMixin, TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.request import ServiceRequest


class Offer(PkMixin, TimestampMixin, Base):
    __tablename__ = "offers"
    __table_args__ = (
        # One live offer per tradesman per request. He edits it, he does not
        # stack a second one under the first.
        UniqueConstraint("request_id", "provider_id", name="uq_offers_request_id_provider_id"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    request_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    price_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    available_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[OfferStatus] = mapped_column(
        enum_column(OfferStatus), nullable=False, default=OfferStatus.PENDING, index=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    #: What the platform actually charged when this offer was accepted. Written
    #: once, at acceptance, so a later change to the trade's fee never rewrites
    #: history. Null on every offer that was not accepted.
    lead_fee_centimes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    request: Mapped[ServiceRequest] = relationship(back_populates="offers")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Offer {self.id} req={self.request_id} {self.status}>"
