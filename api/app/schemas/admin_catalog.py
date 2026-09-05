"""A6 — the two lists, as the admin edits them."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.catalog_rules import (
    MAX_LATITUDE,
    MAX_LEAD_FEE,
    MAX_LONGITUDE,
    MAX_NAME,
    MAX_SLUG,
    MAX_SORT_ORDER,
    MIN_LATITUDE,
    MIN_LEAD_FEE,
    MIN_LONGITUDE,
    MIN_SORT_ORDER,
)
from app.schemas.common import ApiModel


class UsageOut(ApiModel):
    """What points at this row. Shown beside the switch, because "this hides a
    trade 41 tradesmen work in" is the difference between a decision and a
    click."""

    providers: int
    requests: int
    jobs: int


class AdminTradeOut(ApiModel):
    id: int
    slug: str
    name_ar: str
    name_fr: str
    name_en: str
    icon: str
    #: Null means "use the platform default from A7", not "free".
    lead_fee_centimes: int | None
    sort_order: int
    is_active: bool
    usage: UsageOut


class AdminCityOut(ApiModel):
    id: int
    slug: str
    name_ar: str
    name_fr: str
    name_en: str
    latitude: float
    longitude: float
    is_active: bool
    usage: UsageOut


class CatalogOut(ApiModel):
    """Both lists in one response. A6 shows them side by side and neither is
    big enough to be worth two requests."""

    trades: list[AdminTradeOut]
    cities: list[AdminCityOut]


class _Names(BaseModel):
    """All three, always. A trade with no Arabic name renders as a blank row
    to this product's default audience."""

    name_ar: str = Field(min_length=1, max_length=MAX_NAME)
    name_fr: str = Field(min_length=1, max_length=MAX_NAME)
    name_en: str = Field(min_length=1, max_length=MAX_NAME)


class TradeIn(_Names):
    icon: str = Field(min_length=1, max_length=MAX_SLUG)
    lead_fee_centimes: int | None = Field(
        default=None, ge=MIN_LEAD_FEE, le=MAX_LEAD_FEE
    )
    sort_order: int = Field(default=100, ge=MIN_SORT_ORDER, le=MAX_SORT_ORDER)


class NewTradeIn(TradeIn):
    #: Only ever set here. It is in `/services/:slug` and in every link anybody
    #: has shared, so editing one turns all of them into a silent 404.
    slug: str = Field(min_length=1, max_length=MAX_SLUG)


class CityIn(_Names):
    latitude: float = Field(ge=MIN_LATITUDE, le=MAX_LATITUDE)
    longitude: float = Field(ge=MIN_LONGITUDE, le=MAX_LONGITUDE)


class NewCityIn(CityIn):
    slug: str = Field(min_length=1, max_length=MAX_SLUG)


class ActiveIn(BaseModel):
    is_active: bool
