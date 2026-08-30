"""What a job request must say before a tradesman can price it.

Framework-free: the same rules the wizard shows step by step and the API
enforces on submit, in one place, so the form and the server cannot disagree
about what "enough to quote on" means.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import Urgency
from app.core.errors import DomainError, ErrorCode
from app.core.money import MAX_AMOUNT_CENTIMES
from app.core.policy import MAX_REQUEST_PHOTOS

MIN_TITLE = 5
MAX_TITLE = 160

#: Long enough that somebody can price it without a phone call. "Fuite" is not
#: a request; "fuite sous l'évier depuis hier, l'eau coule quand j'ouvre" is.
MIN_DESCRIPTION = 20
MAX_DESCRIPTION = 2000

MIN_ADDRESS = 3
MAX_ADDRESS = 255


@dataclass(frozen=True, slots=True)
class NewRequest:
    trade_id: int
    city_id: int
    title: str
    description: str
    address: str
    latitude: float | None
    longitude: float | None
    urgency: Urgency
    budget_min_centimes: int | None
    budget_max_centimes: int | None
    photo_paths: tuple[str, ...]


def validate_request(
    *,
    trade_id: int,
    city_id: int,
    title: str,
    description: str,
    address: str,
    latitude: float | None,
    longitude: float | None,
    urgency: Urgency,
    budget_min_centimes: int | None,
    budget_max_centimes: int | None,
    photo_paths: list[str],
) -> NewRequest:
    if trade_id <= 0:
        raise _invalid("trade_id")
    if city_id <= 0:
        raise _invalid("city_id")

    clean_title = " ".join(title.split())
    if not MIN_TITLE <= len(clean_title) <= MAX_TITLE:
        raise _invalid("title", min=MIN_TITLE, max=MAX_TITLE)

    clean_description = description.strip()
    if not MIN_DESCRIPTION <= len(clean_description) <= MAX_DESCRIPTION:
        raise _invalid("description", min=MIN_DESCRIPTION, max=MAX_DESCRIPTION)

    clean_address = " ".join(address.split())
    if not MIN_ADDRESS <= len(clean_address) <= MAX_ADDRESS:
        raise _invalid("address", min=MIN_ADDRESS, max=MAX_ADDRESS)

    if latitude is not None and not -90 <= latitude <= 90:
        raise _invalid("latitude")
    if longitude is not None and not -180 <= longitude <= 180:
        raise _invalid("longitude")

    for field, amount in (
        ("budget_min_centimes", budget_min_centimes),
        ("budget_max_centimes", budget_max_centimes),
    ):
        if amount is not None and not 0 < amount <= MAX_AMOUNT_CENTIMES:
            raise _invalid(field)

    # A budget that reads high-to-low is a typo, and quoting against it would
    # be guessing which number the client meant.
    if (
        budget_min_centimes is not None
        and budget_max_centimes is not None
        and budget_min_centimes > budget_max_centimes
    ):
        raise _invalid("budget_max_centimes")

    unique_photos = tuple(dict.fromkeys(photo_paths))
    if len(unique_photos) > MAX_REQUEST_PHOTOS:
        raise _invalid("photo_paths", max=MAX_REQUEST_PHOTOS)

    return NewRequest(
        trade_id=trade_id,
        city_id=city_id,
        title=clean_title,
        description=clean_description,
        address=clean_address,
        latitude=latitude,
        longitude=longitude,
        urgency=urgency,
        budget_min_centimes=budget_min_centimes,
        budget_max_centimes=budget_max_centimes,
        photo_paths=unique_photos,
    )


def _invalid(field: str, **details: int) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, **details)
