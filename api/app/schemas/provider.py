"""Tradesmen, as a client browsing the home page sees them."""

from __future__ import annotations

from app.core.enums import ProviderStatus
from app.schemas.catalog import TradeOut
from app.schemas.common import ApiModel


class ProviderCityOut(ApiModel):
    id: int
    slug: str
    name_ar: str
    name_fr: str
    name_en: str


class ProviderCardOut(ApiModel):
    """One card in the grid.

    Everything on it is something a client decides with: who, where, what he
    does, how he has been rated, and — when he has said so — what he starts at.
    """

    id: int
    full_name: str
    avatar_url: str | None
    headline: str | None
    status: ProviderStatus

    city: ProviderCityOut
    trades: list[TradeOut]

    rating_avg: float
    rating_count: int
    jobs_done: int
    years_experience: int

    #: Null when he would rather quote per job. The card omits it rather than
    #: inventing a number.
    starting_price_centimes: int | None
