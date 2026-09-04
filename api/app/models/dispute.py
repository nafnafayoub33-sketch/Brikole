"""Disputes and reports — what the moderator role exists for.

The platform never holds the client's money, so a dispute is not a refund
request. Its outcomes are a warning, a suspension, and a refund of the *lead
fee* to the tradesman when the client was at fault.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DisputeReason, DisputeStatus, DisputeVerdict
from app.models.base import Base, PkMixin, TimestampMixin, enum_column


class Dispute(PkMixin, TimestampMixin, Base):
    __tablename__ = "disputes"

    job_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opened_by_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    against_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    reason: Mapped[DisputeReason] = mapped_column(enum_column(DisputeReason), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[DisputeStatus] = mapped_column(
        enum_column(DisputeStatus), nullable=False, default=DisputeStatus.OPEN, index=True
    )
    #: A dispute is read-only until a moderator claims it, so two of them never
    #: arbitrate the same case in parallel.
    claimed_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    verdict: Mapped[DisputeVerdict | None] = mapped_column(
        enum_column(DisputeVerdict), nullable=True
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_fee_refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    messages: Mapped[list[DisputeMessage]] = relationship(
        back_populates="dispute", cascade="all, delete-orphan", order_by="DisputeMessage.id"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Dispute {self.id} job={self.job_id} {self.status}>"


class DisputeMessage(PkMixin, TimestampMixin, Base):
    __tablename__ = "dispute_messages"

    dispute_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    #: Moderator notes the two parties never see.
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    dispute: Mapped[Dispute] = relationship(back_populates="messages")


class Report(PkMixin, TimestampMixin, Base):
    """A user flagging a profile, a review or a message (D3)."""

    __tablename__ = "reports"

    #: Null when the platform filed it rather than a person — see
    #: `ReportReason.CONTACT_SHARING`. A staff screen reads the absence as
    #: "the system noticed this", which is a different weight from an
    #: accusation somebody put their name to.
    reporter_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    #: "user" | "review" | "provider_profile" — a loose pointer on purpose, so a
    #: new reportable thing does not need a migration.
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    handled_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
