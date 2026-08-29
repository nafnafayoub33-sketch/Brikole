"""Moroccan phone numbers.

One stored format, E.164 (`+212XXXXXXXXX`), so `0612345678`, `+212612345678`
and `00212 612-345-678` are the same account and never three.
"""

from __future__ import annotations

import re

from app.core.errors import DomainError, ErrorCode

COUNTRY_CODE = "212"
E164_LENGTH = 13  # "+212" + 9 digits

# Mobile prefixes are 6 and 7; landlines are 5. All are 9 digits nationally.
_NATIONAL = re.compile(r"^[567]\d{8}$")
_SEPARATORS = re.compile(r"[\s\-().]")


def normalise_phone(raw: str) -> str:
    """Return the number as `+212XXXXXXXXX`, or raise `PHONE_INVALID`.

    Accepts the four ways a Moroccan number is normally typed: with the national
    leading zero, with the country code, with `00` instead of `+`, and already
    in E.164.
    """
    if not raw:
        raise DomainError(ErrorCode.PHONE_INVALID)

    digits = _SEPARATORS.sub("", raw.strip())

    if digits.startswith("+"):
        digits = digits[1:]
    elif digits.startswith("00"):
        digits = digits[2:]

    if not digits.isdigit():
        raise DomainError(ErrorCode.PHONE_INVALID)

    if digits.startswith(COUNTRY_CODE):
        national = digits[len(COUNTRY_CODE) :]
    elif digits.startswith("0"):
        national = digits[1:]
    else:
        national = digits

    if not _NATIONAL.match(national):
        raise DomainError(ErrorCode.PHONE_INVALID)

    return f"+{COUNTRY_CODE}{national}"


def is_valid_phone(raw: str) -> bool:
    try:
        normalise_phone(raw)
    except DomainError:
        return False
    return True


def national_format(e164: str) -> str:
    """`+212612345678` → `0612345678`, for display only."""
    if not e164.startswith(f"+{COUNTRY_CODE}"):
        return e164
    return "0" + e164[len(COUNTRY_CODE) + 1 :]
