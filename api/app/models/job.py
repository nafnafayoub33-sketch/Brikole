"""The accepted work, and the review it earns."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import CancelledBy, JobStatus
from app.models.base import Base, PkMixin, TimestampMixin, enum_column


class Job(PkMixin, TimestampMixin, Base):
    """Created when a client accepts an offer, in the same transaction that
    charges the lead fee. One per request, one per offer."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("request_id", name="uq_jobs_request_id"),
        UniqueConstraint("offer_id", name="uq_jobs_offer_id"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    request_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    offer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("offers.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    #: Copied from the offer so the record survives an edit to the offer.
    agreed_price_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    status: Mapped[JobStatus] = mapped_column(
        enum_column(JobStatus), nullable=False, default=JobStatus.ASSIGNED, index=True
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_by: Mapped[CancelledBy | None] = mapped_column(
        enum_column(CancelledBy), nullable=True
    )
    #: Mandatory when the tradesman cancels — it is what the rate is built from.
    cancel_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Job {self.id} {self.status}>"


class Review(PkMixin, TimestampMixin, Base):
    """One per job, written by the client, answerable once by the tradesman."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_reviews_job_id"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    job_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    is_hidden: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Review {self.id} {self.rating}/5>"
