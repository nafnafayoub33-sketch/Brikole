"""Offers, as the client who asked for them reads them (C3)."""

from __future__ import annotations

from datetime import datetime

from app.core.enums import OfferStatus
from app.schemas.common import ApiModel
from app.schemas.provider import ProviderCityOut


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
