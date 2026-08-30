"""Offers, as the client who asked for them reads them (C3)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import OfferStatus, Urgency
from app.core.offer import MAX_MESSAGE
from app.schemas.catalog import TradeOut
from app.schemas.common import ApiModel
from app.schemas.provider import ProviderCityOut
from app.schemas.request import RequestPhotoOut


class OfferProviderOut(ApiModel):
    """Enough of the tradesman to choose between two offers without leaving
    the page — and a link to P3 for everything else."""

    id: int
    full_name: str
    avatar_url: str | None
    headline: str | None
    city: ProviderCityOut

    rating_avg: float
    rating_count: int
    jobs_done: int
    years_experience: int


class OfferOut(ApiModel):
    id: int
    price_centimes: int
    message: str
    #: When he can come. Null means he did not say, and C3 says so rather than
    #: inventing a date.
    available_from: datetime | None
    status: OfferStatus
    created_at: datetime

    provider: OfferProviderOut


class MyOfferOut(ApiModel):
    """His own offer, as M6 lists it and M5 edits it."""

    id: int
    request_id: int
    request_title: str
    trade: TradeOut
    city: ProviderCityOut
    price_centimes: int
    message: str
    available_from: datetime | None
    status: OfferStatus
    created_at: datetime
    responded_at: datetime | None
    #: Set once accepted, so M6 can link to the job it became.
    job_id: int | None = None


class FeedRequestOut(ApiModel):
    """One row of M4.

    Deliberately not the whole request: the description is trimmed and the
    address is absent. He decides whether to open it from the trade, the area
    and the money, and the exact address is not his until an offer is accepted.
    """

    id: int
    title: str
    #: Enough to judge, not the whole thing.
    excerpt: str
    trade: TradeOut
    city: ProviderCityOut
    urgency: Urgency
    budget_min_centimes: int | None
    budget_max_centimes: int | None
    offers_count: int
    photos_count: int
    created_at: datetime
    expires_at: datetime | None

    #: Set when he has already answered this one, so M4 says so rather than
    #: sending him to a form that turns out to be an edit.
    my_offer_id: int | None = None
    my_offer_price_centimes: int | None = None


class FeedRequestDetailOut(FeedRequestOut):
    """M5. Everything above plus what he needs to write a price."""

    description: str
    photos: list[RequestPhotoOut]

    #: What the platform will charge him **if the client accepts**. Stated
    #: before he sends, never taken now.
    lead_fee_centimes: int

    my_offer: MyOfferOut | None = None


class NewOfferIn(BaseModel):
    price_centimes: int = Field(gt=0)
    message: str | None = Field(default=None, max_length=MAX_MESSAGE)
    available_from: datetime | None = None


class CreditSummaryOut(ApiModel):
    """M3's loudest number, and what M4 and M5 gate on."""

    balance_centimes: int
    free_leads_left: int
    #: What one accepted offer costs him at the platform default.
    default_lead_fee_centimes: int
    #: False when the feed is closed to him until he tops up.
    can_take_work: bool
