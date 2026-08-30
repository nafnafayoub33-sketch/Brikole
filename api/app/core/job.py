"""The job lifecycle, and what accepting an offer costs.

Framework-free: no FastAPI, no SQLAlchemy, no clock. Everything here is a
decision the product makes, testable without a database.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import JobStatus, TransactionType

#: Who may move a job where. The client and the tradesman own different arrows,
#: and neither owns the other's — a client cannot mark work started, and a
#: tradesman cannot confirm his own job.
PROVIDER_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.ASSIGNED: frozenset({JobStatus.IN_PROGRESS, JobStatus.CANCELLED}),
    JobStatus.IN_PROGRESS: frozenset({JobStatus.DONE, JobStatus.CANCELLED}),
    JobStatus.DONE: frozenset(),
    JobStatus.CONFIRMED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}

CLIENT_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    # He can walk away before and during, but once the work is done the only
    # thing left to him is confirming it or disputing it.
    JobStatus.ASSIGNED: frozenset({JobStatus.CANCELLED}),
    JobStatus.IN_PROGRESS: frozenset({JobStatus.CANCELLED}),
    JobStatus.DONE: frozenset({JobStatus.CONFIRMED}),
    JobStatus.CONFIRMED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}

#: Statuses a job never leaves.
TERMINAL = frozenset({JobStatus.CONFIRMED, JobStatus.CANCELLED})


def can_move(current: JobStatus, target: JobStatus, *, by_provider: bool) -> bool:
    table = PROVIDER_TRANSITIONS if by_provider else CLIENT_TRANSITIONS
    return target in table[current]


@dataclass(frozen=True, slots=True)
class LeadCharge:
    """What accepting an offer does to the tradesman's account.

    Two numbers and a ledger row, decided together: a balance that moves
    without its explaining row is the one thing `credit.py` exists to prevent.
    """

    #: Signed, so it can be added to the balance directly. Zero on a free lead.
    amount_centimes: int
    balance_after_centimes: int
    free_leads_after: int
    transaction_type: TransactionType
    reason: str

    @property
    def went_negative(self) -> bool:
        return self.balance_after_centimes < 0


def charge_for_lead(
    *, free_leads_left: int, balance_centimes: int, fee_centimes: int
) -> LeadCharge:
    """Spend a free lead if he has one, otherwise take the fee.

    **A short balance does not refuse the acceptance.** The client is the one
    clicking, he has no way to see or fix the tradesman's wallet, and blocking
    him there would break the only flow that makes the platform any money. So
    the balance is allowed to go negative and the debt is recorded: the
    tradesman stops seeing the request feed until he clears it, which is where
    the pressure belongs.

    The real guard is upstream — M5 refuses to send an offer without credit —
    so a shortfall here is the narrow case where the fee changed, or the
    balance was spent, between the offer and its acceptance.
    """
    if fee_centimes < 0:
        raise ValueError("a lead fee is never negative")

    if free_leads_left > 0:
        return LeadCharge(
            amount_centimes=0,
            balance_after_centimes=balance_centimes,
            free_leads_after=free_leads_left - 1,
            transaction_type=TransactionType.FREE_LEAD,
            reason="free_lead",
        )

    return LeadCharge(
        amount_centimes=-fee_centimes,
        balance_after_centimes=balance_centimes - fee_centimes,
        free_leads_after=0,
        transaction_type=TransactionType.LEAD_FEE,
        reason="offer_accepted",
    )
