"""Prepaid credit: the balance, the ledger it is derived from, and top-ups.

The invariant this file exists to protect: `CreditAccount.balance_centimes` is a
cache. Every change to it is written together with the `CreditTransaction` row
that explains it, in one transaction. A balance with no matching ledger row is a
bug, not a shortcut.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import TopupStatus, TransactionType
from app.models.base import Base, PkMixin, TimestampMixin, enum_column


class CreditAccount(PkMixin, TimestampMixin, Base):
    __tablename__ = "credit_accounts"
    __table_args__ = (
        UniqueConstraint("provider_id", name="uq_credit_accounts_provider_id"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    provider_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False
    )
    balance_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    #: Leads a new tradesman gets before the fee starts applying.
    free_leads_left: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    transactions: Mapped[list[CreditTransaction]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CreditAccount provider={self.provider_id} {self.balance_centimes}c>"


class CreditTransaction(PkMixin, TimestampMixin, Base):
    """One movement. Append-only: corrections are new rows of type ADJUSTMENT."""

    __tablename__ = "credit_transactions"

    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("credit_accounts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    type: Mapped[TransactionType] = mapped_column(enum_column(TransactionType), nullable=False)

    #: Signed: negative takes money out, positive puts it in.
    amount_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    #: The balance after this row, so the ledger can be audited without replay.
    balance_after_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    #: A short machine-readable note, not a sentence for a user to read.
    reason: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    offer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("offers.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    topup_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("topup_requests.id", ondelete="SET NULL"), nullable=True
    )
    #: The admin or moderator behind a manual movement, if there was one.
    actor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    account: Mapped[CreditAccount] = relationship(back_populates="transactions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CreditTransaction {self.type} {self.amount_centimes}c>"


class TopupRequest(PkMixin, TimestampMixin, Base):
    """A bank transfer waiting for an admin to confirm it landed (A5).

    Submitting one moves no money. Only approval does, and approval writes the
    ledger row.
    """

    __tablename__ = "topup_requests"

    provider_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    #: The transfer reference the bank gave the tradesman.
    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Private bucket — a receipt has an account number on it.
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[TopupStatus] = mapped_column(
        enum_column(TopupStatus), nullable=False, default=TopupStatus.PENDING, index=True
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TopupRequest {self.id} {self.amount_centimes}c {self.status}>"
