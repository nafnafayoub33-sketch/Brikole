"""What an admin may put in the two lists everything else points at.

A6 edits the trades and the cities. Both are pointed at by requests, jobs,
offers and profiles, so the rules here are shaped by one fact: **nothing in
these lists is ever deleted.** A trade with four hundred jobs behind it cannot
vanish without taking the history with it, so the only removal is
deactivation — it leaves the rows alone and stops the trade being offered.

Framework-free, so "is this a valid slug" can be argued about without a
database.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.money import dirhams

#: Lowercase, digits and single hyphens. It goes in a URL (`/services/plombier`)
#: and into a filename or two, so it stays boring on purpose.
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

MAX_SLUG = 64
MAX_NAME = 120

#: The same bounds A7 puts on the platform default. A trade that overrides it
#: is still charging somebody real money.
MIN_LEAD_FEE = dirhams(1)
MAX_LEAD_FEE = dirhams(500)

MIN_SORT_ORDER = 0
MAX_SORT_ORDER = 9999

#: Real coordinates, not Moroccan ones. Bounding this to Morocco would be a
#: rule that has to be found and removed the day the product crosses a border,
#: and a city in the wrong hemisphere is visible on the map anyway.
MIN_LATITUDE, MAX_LATITUDE = -90.0, 90.0
MIN_LONGITUDE, MAX_LONGITUDE = -180.0, 180.0


@dataclass(frozen=True, slots=True)
class TradeFields:
    slug: str
    name_ar: str
    name_fr: str
    name_en: str
    icon: str
    lead_fee_centimes: int | None
    sort_order: int


@dataclass(frozen=True, slots=True)
class CityFields:
    slug: str
    name_ar: str
    name_fr: str
    name_en: str
    latitude: float
    longitude: float


def validate_slug(slug: str) -> str:
    """Raises `ValueError("slug")`.

    **Only ever checked on creation.** A slug is in `/services/:slug`, in
    whatever a tradesman has bookmarked, and in every link anybody has shared;
    editing one turns all of those into a 404 silently. Renaming a trade means
    editing its three names, which is what a reader actually sees.
    """
    cleaned = slug.strip().lower()
    if not cleaned or len(cleaned) > MAX_SLUG or not SLUG.match(cleaned):
        raise ValueError("slug")
    return cleaned


def _name(value: str, field: str) -> str:
    """Every language is mandatory.

    A trade with no Arabic name renders as a blank row to the default
    audience of this product. An empty string is not a translation somebody
    chose; it is one nobody got round to.
    """
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > MAX_NAME:
        raise ValueError(field)
    return cleaned


def _lead_fee(value: int | None) -> int | None:
    if value is None:
        return None
    # `bool` is an `int` in Python, and `True` is not a fee.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("lead_fee_centimes")
    if value < MIN_LEAD_FEE or value > MAX_LEAD_FEE:
        raise ValueError("lead_fee_centimes")
    return value


def validate_trade(
    *,
    slug: str,
    name_ar: str,
    name_fr: str,
    name_en: str,
    icon: str,
    lead_fee_centimes: int | None,
    sort_order: int,
) -> TradeFields:
    cleaned_icon = icon.strip()
    if not cleaned_icon or len(cleaned_icon) > MAX_SLUG:
        raise ValueError("icon")

    if sort_order < MIN_SORT_ORDER or sort_order > MAX_SORT_ORDER:
        raise ValueError("sort_order")

    return TradeFields(
        slug=validate_slug(slug),
        name_ar=_name(name_ar, "name_ar"),
        name_fr=_name(name_fr, "name_fr"),
        name_en=_name(name_en, "name_en"),
        icon=cleaned_icon,
        lead_fee_centimes=_lead_fee(lead_fee_centimes),
        sort_order=sort_order,
    )


def validate_city(
    *,
    slug: str,
    name_ar: str,
    name_fr: str,
    name_en: str,
    latitude: float,
    longitude: float,
) -> CityFields:
    if not MIN_LATITUDE <= latitude <= MAX_LATITUDE:
        raise ValueError("latitude")
    if not MIN_LONGITUDE <= longitude <= MAX_LONGITUDE:
        raise ValueError("longitude")

    return CityFields(
        slug=validate_slug(slug),
        name_ar=_name(name_ar, "name_ar"),
        name_fr=_name(name_fr, "name_fr"),
        name_en=_name(name_en, "name_en"),
        latitude=latitude,
        longitude=longitude,
    )
