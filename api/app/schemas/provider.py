"""Tradesmen, as a client browsing the home page sees them."""

from __future__ import annotations

from datetime import datetime

from app.core.enums import ProviderStatus
from app.schemas.availability import AvailabilityOut
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

    #: He paid for this position. Sent so the card can say so — placement a
    #: reader cannot see the reason for is a lie by omission, and it costs the
    #: platform nothing to be straight about it.
    is_boosted: bool = False


class ProviderPhotoOut(ApiModel):
    id: int
    url: str


class ProviderProfileOut(ProviderCardOut):
    """The card, plus everything P3 shows that a grid has no room for."""

    bio: str
    radius_km: int
    #: Whether he is taking work, and when he is back if he is not. A grid
    #: never shows a paused tradesman, but his own page opens — and telling a
    #: client "back on the 20th" beats letting him write into the void.
    availability: AvailabilityOut
    member_since: datetime

    #: How many reviews gave each score, 1 through 5. The bar chart on P3 reads
    #: straight off it, and a rating with no distribution behind it is a number
    #: nobody can check.
    rating_breakdown: dict[int, int]

    photos: list[ProviderPhotoOut]


class ReviewAuthorOut(ApiModel):
    #: First name and last initial. A review is public; a full name need not be.
    display_name: str
    city: ProviderCityOut | None


class ReviewOut(ApiModel):
    id: int
    rating: int
    comment: str | None
    created_at: datetime

    #: The tradesman answers once. Shown under the review it answers.
    reply: str | None
    replied_at: datetime | None

    author: ReviewAuthorOut
    trade: TradeOut | None
