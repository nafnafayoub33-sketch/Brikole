"""Jobs, as the two people doing one read them."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import CancelledBy, JobStatus
from app.core.policy import MAX_RATING, MIN_RATING
from app.schemas.catalog import TradeOut
from app.schemas.common import ApiModel
from app.schemas.provider import ProviderCityOut


class JobPartyOut(ApiModel):
    """The other person, as the one reading needs them.

    The phone number is on this model and on no other. It is the whole point of
    C4 and M7 — two people who have agreed to meet need to reach each other —
    and it appears nowhere before an offer is accepted.
    """

    id: int
    full_name: str
    avatar_url: str | None
    phone: str

    #: Only set when the other party is a tradesman; a client has no rating.
    rating_avg: float | None = None
    rating_count: int | None = None
    jobs_done: int | None = None


class JobReviewOut(ApiModel):
    id: int
    rating: int
    comment: str | None
    created_at: datetime
    reply: str | None
    replied_at: datetime | None


class JobOut(ApiModel):
    id: int
    request_id: int
    status: JobStatus

    title: str
    description: str
    trade: TradeOut
    city: ProviderCityOut
    #: The full address, which both sides now need and neither saw before.
    address: str

    agreed_price_centimes: int
    #: What the platform charged the tradesman for this lead. Null on the
    #: client's copy — it is none of his business what the m3allem paid.
    lead_fee_centimes: int | None = None

    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancelled_by: CancelledBy | None
    cancel_reason: str | None

    client: JobPartyOut
    provider: JobPartyOut

    #: Present once the client has rated. C5 reads it to go read-only.
    review: JobReviewOut | None = None


class CancelJobIn(BaseModel):
    #: Mandatory for the tradesman — the cancellation rate is built from it —
    #: and the service is what enforces that, not this schema.
    reason: str | None = Field(default=None, max_length=500)


class NewReviewIn(BaseModel):
    rating: int = Field(ge=MIN_RATING, le=MAX_RATING)
    comment: str | None = Field(default=None, max_length=2000)
