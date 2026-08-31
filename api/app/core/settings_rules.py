"""What an admin may set a platform setting to.

A7 is the one screen that can change how the whole product behaves, so every
value it accepts is bounded here rather than trusted. A lead fee of zero makes
the business free; a request cap of zero makes the product unusable; and both
are one mistyped digit away on a form.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.money import dirhams
from app.core.policy import SettingKey


@dataclass(frozen=True, slots=True)
class Bound:
    minimum: int
    maximum: int


#: Inclusive bounds for the numeric settings. Wide enough to run the business
#: differently, narrow enough that a slip does not take it down.
NUMERIC_BOUNDS: dict[str, Bound] = {
    SettingKey.DEFAULT_LEAD_FEE: Bound(dirhams(1), dirhams(500)),
    SettingKey.FREE_LEADS_NEW_PROVIDER: Bound(0, 500),
    SettingKey.MAX_OPEN_REQUESTS_PER_CLIENT: Bound(1, 50),
    SettingKey.OFFER_EXPIRY_DAYS: Bound(1, 90),
    SettingKey.REQUEST_EXPIRY_DAYS: Bound(1, 365),
    SettingKey.AUTO_CONFIRM_DAYS: Bound(1, 60),
    SettingKey.DISPUTE_WINDOW_DAYS: Bound(1, 90),
    SettingKey.DEFAULT_RADIUS_KM: Bound(1, 100),
}

BANK_FIELDS = ("bank_name", "account_holder", "rib", "instructions")
MAX_BANK_FIELD = 200
MAX_INSTRUCTIONS = 500

#: Keys A7 is allowed to touch at all. Anything else is a bug or an attempt.
EDITABLE: frozenset[str] = frozenset(NUMERIC_BOUNDS) | {
    SettingKey.BANK_TRANSFER,
    SettingKey.MAINTENANCE_MODE,
}


def validate_setting(key: str, value: Any) -> Any:
    """Return the value to store, or raise `ValueError(key)`."""
    if key not in EDITABLE:
        raise ValueError(key)

    if key == SettingKey.MAINTENANCE_MODE:
        if not isinstance(value, bool):
            raise ValueError(key)
        return value

    if key == SettingKey.BANK_TRANSFER:
        return _validate_bank(key, value)

    # `bool` is an `int` in Python, and `True` is not a lead fee.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(key)

    bound = NUMERIC_BOUNDS[key]
    if value < bound.minimum or value > bound.maximum:
        raise ValueError(key)
    return value


def _validate_bank(key: str, value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(key)

    cleaned: dict[str, str] = {}
    for field in BANK_FIELDS:
        raw = value.get(field, "")
        if not isinstance(raw, str):
            raise ValueError(key)
        # Whitespace is collapsed but not stripped to nothing: an empty bank
        # panel is a legitimate state, and M9 says so rather than showing blanks.
        text = " ".join(raw.split())
        limit = MAX_INSTRUCTIONS if field == "instructions" else MAX_BANK_FIELD
        if len(text) > limit:
            raise ValueError(key)
        cleaned[field] = text

    return cleaned
