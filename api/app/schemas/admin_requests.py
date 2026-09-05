"""A4 — what the support browser renders."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import (
    DisputeStatus,
    JobStatus,
    OfferStatus,
    RequestStatus,
    Urgency,
)
from app.schemas.catalog import CityOut, TradeOut
from app.schemas.common import ApiModel


class RequestPersonOut(ApiModel):
    """Somebody on a request, as support needs them.

    The phone is here and nowhere else in the admin API by accident: A4 exists
    because a person is *on* the phone, and an admin who has to leave the
    screen to find the number is an admin who reads it out wrong.
    """

    id: int
    full_name: str
    phone: str


class RequestRowOut(ApiModel):
    """One line in the list. Everything a support agent scans by."""

    id: int
    title: str
    status: RequestStatus
    urgency: Urgency
    offers_count: int
    created_at: datetime

    client: RequestPersonOut
    trade: TradeOut
    city: CityOut


class RequestOfferOut(ApiModel):
    id: int
    price_centimes: int
    message: str | None
    status: OfferStatus
    created_at: datetime
    #: Frozen when the offer was accepted, so a later price change never
    #: rewrites what this lead actually cost. Null on an offer nobody took.
    lead_fee_centimes: int | None
    provider: RequestPersonOut
    provider_id: int


class RequestJobOut(ApiModel):
    id: int
    status: JobStatus
    agreed_price_centimes: int
    started_at: datetime | None
    finished_at: datetime | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancelled_by: str | None
    cancel_reason: str | None
    provider: RequestPersonOut | None


class RequestDisputeOut(ApiModel):
    id: int
    status: DisputeStatus
    reason: str
    opened_by_id: int


class RequestDetailOut(ApiModel):
    """The whole story of one request, in one response."""

    id: int
    title: str
    description: str
    status: RequestStatus
    urgency: Urgency
    address: str
    budget_min_centimes: int | None
    budget_max_centimes: int | None
    photos: int
    offers_count: int

    created_at: datetime
    expires_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None

    client: RequestPersonOut
    trade: TradeOut
    city: CityOut

    offers: list[RequestOfferOut]
    job: RequestJobOut | None
    dispute: RequestDisputeOut | None

    #: Whether A4's one action is available. Answered here rather than derived
    #: on the screen from `status`, so the button and the API agree about what
    #: "open" means.
    can_cancel: bool


class CancelRequestIn(BaseModel):
    #: Mandatory. Somebody reads this in three months and needs to know why a
    #: client's request vanished; "cancelled by an admin" is not a why.
    reason: str = Field(min_length=1, max_length=500)
