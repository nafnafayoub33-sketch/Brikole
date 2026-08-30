"""Disputes, as the two parties open them and a moderator reads them."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.dispute import MAX_DESCRIPTION, MAX_EVIDENCE, MAX_MESSAGE, MIN_DESCRIPTION
from app.core.enums import DisputeReason, DisputeStatus, DisputeVerdict
from app.schemas.common import ApiModel


class DisputePartyOut(ApiModel):
    """A side of the argument, with the history a moderator judges against.

    No phone number and no money: he is arbitrating, not calling anybody, and
    the whole reason the moderator role exists is that it sees no balances.
    """

    id: int
    full_name: str
    role: str
    #: Only set for a tradesman.
    provider_id: int | None = None
    rating_avg: float | None = None
    rating_count: int | None = None
    jobs_done: int | None = None
    #: How many disputes this person has been on the wrong end of before.
    disputes_lost: int = 0


class DisputeMessageOut(ApiModel):
    id: int
    author_id: int
    author_name: str
    body: str
    attachment_url: str | None
    #: Moderator notes. Never serialised to a party — the service filters them
    #: out rather than trusting the screen to hide them.
    is_internal: bool
    created_at: datetime


class DisputeJobOut(ApiModel):
    id: int
    title: str
    status: str
    agreed_price_centimes: int
    finished_at: datetime | None
    #: The one money figure a moderator sees, because he can refund it.
    lead_fee_centimes: int | None


class DisputeOut(ApiModel):
    id: int
    reason: DisputeReason
    description: str
    status: DisputeStatus
    created_at: datetime

    job: DisputeJobOut
    opened_by: DisputePartyOut
    against: DisputePartyOut

    claimed_by_id: int | None
    claimed_by_name: str | None
    claimed_at: datetime | None

    verdict: DisputeVerdict | None
    resolution_note: str | None
    lead_fee_refunded: bool
    resolved_at: datetime | None

    evidence: list[str]
    messages: list[DisputeMessageOut]

    #: Older than 48 hours and still unclaimed. D1 flags it.
    is_stale: bool


class DisputeRowOut(ApiModel):
    """One row of D1's queue. Enough to triage without opening it."""

    id: int
    reason: DisputeReason
    status: DisputeStatus
    created_at: datetime
    job_title: str
    opened_by_name: str
    against_name: str
    claimed_by_id: int | None
    is_stale: bool


class NewDisputeIn(BaseModel):
    reason: DisputeReason
    description: str = Field(min_length=MIN_DESCRIPTION, max_length=MAX_DESCRIPTION)
    evidence_paths: list[str] = Field(default_factory=list, max_length=MAX_EVIDENCE)


class DisputeMessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=MAX_MESSAGE)
    #: A note for other moderators, invisible to both parties.
    is_internal: bool = False


class ResolveDisputeIn(BaseModel):
    verdict: DisputeVerdict
    note: str = Field(min_length=1, max_length=2000)
    #: Only honoured when the client was at fault; the service refuses it
    #: otherwise rather than quietly ignoring it.
    refund_lead_fee: bool = False
    #: 48 hours on the party the verdict blames.
    suspend_at_fault: bool = False
