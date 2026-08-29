"""Trades and cities, as the public sees them."""

from __future__ import annotations

from app.schemas.common import ApiModel


class TradeOut(ApiModel):
    id: int
    slug: str
    name_ar: str
    name_fr: str
    name_en: str
    icon: str
    sort_order: int
    #: Approved tradesmen working in this trade — within `city_id` when the
    #: caller passed one. Zero is a real answer and the grid says so.
    providers_count: int = 0


class CityOut(ApiModel):
    id: int
    slug: str
    name_ar: str
    name_fr: str
    name_en: str
    latitude: float
    longitude: float
