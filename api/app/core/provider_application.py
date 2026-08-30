"""What a tradesman must supply before an admin can judge his application.

Framework-free and testable without a database: the same rules the form shows
and the API enforces, in one place, so the two cannot drift into disagreeing
about what "complete" means.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import DomainError, ErrorCode
from app.core.money import MAX_AMOUNT_CENTIMES
from app.core.policy import MAX_PORTFOLIO_PHOTOS, MAX_RADIUS_KM

MIN_TRADES = 1
MAX_TRADES = 5

MIN_RADIUS_KM = 1
MAX_YEARS_EXPERIENCE = 70

MAX_HEADLINE = 160
MAX_BIO = 2000

#: Long enough to say something, short enough that nobody writes an essay to
#: get past a form.
MIN_BIO = 20


@dataclass(frozen=True, slots=True)
class ProviderApplication:
    trade_ids: tuple[int, ...]
    city_id: int
    radius_km: int
    headline: str
    bio: str
    years_experience: int
    starting_price_centimes: int | None
    avatar_path: str | None
    id_card_path: str
    photo_paths: tuple[str, ...]


def validate_application(
    *,
    trade_ids: list[int],
    city_id: int,
    radius_km: int,
    headline: str | None,
    bio: str,
    years_experience: int,
    starting_price_centimes: int | None,
    avatar_path: str | None,
    id_card_path: str | None,
    photo_paths: list[str],
) -> ProviderApplication:
    """Normalise and check, or raise with the field that failed."""
    unique_trades = tuple(dict.fromkeys(trade_ids))
    if not MIN_TRADES <= len(unique_trades) <= MAX_TRADES:
        raise _invalid("trade_ids", min=MIN_TRADES, max=MAX_TRADES)

    if city_id <= 0:
        raise _invalid("city_id")

    if not MIN_RADIUS_KM <= radius_km <= MAX_RADIUS_KM:
        raise _invalid("radius_km", min=MIN_RADIUS_KM, max=MAX_RADIUS_KM)

    clean_headline = " ".join((headline or "").split())
    if not clean_headline or len(clean_headline) > MAX_HEADLINE:
        raise _invalid("headline", max=MAX_HEADLINE)

    clean_bio = bio.strip()
    if not MIN_BIO <= len(clean_bio) <= MAX_BIO:
        raise _invalid("bio", min=MIN_BIO, max=MAX_BIO)

    if not 0 <= years_experience <= MAX_YEARS_EXPERIENCE:
        raise _invalid("years_experience", max=MAX_YEARS_EXPERIENCE)

    if starting_price_centimes is not None and not (
        0 < starting_price_centimes <= MAX_AMOUNT_CENTIMES
    ):
        raise _invalid("starting_price_centimes")

    # The identity document is the whole point of the review an admin does.
    # Everything else can be corrected later; an application without it cannot
    # be judged at all.
    if not id_card_path:
        raise _invalid("id_card_path")

    unique_photos = tuple(dict.fromkeys(photo_paths))
    if len(unique_photos) > MAX_PORTFOLIO_PHOTOS:
        raise _invalid("photo_paths", max=MAX_PORTFOLIO_PHOTOS)

    return ProviderApplication(
        trade_ids=unique_trades,
        city_id=city_id,
        radius_km=radius_km,
        headline=clean_headline,
        bio=clean_bio,
        years_experience=years_experience,
        starting_price_centimes=starting_price_centimes,
        avatar_path=avatar_path or None,
        id_card_path=id_card_path,
        photo_paths=unique_photos,
    )


def _invalid(field: str, **details: int) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, **details)
