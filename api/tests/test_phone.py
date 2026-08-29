"""Moroccan numbers normalise to exactly one stored form."""

import pytest

from app.core.errors import DomainError, ErrorCode
from app.core.phone import is_valid_phone, national_format, normalise_phone


@pytest.mark.parametrize(
    "raw",
    [
        "0612345678",
        "+212612345678",
        "212612345678",
        "00212612345678",
        "06 12 34 56 78",
        "06-12-34-56-78",
        "+212 612-345-678",
        "  0612345678  ",
        "(0612) 345-678",
    ],
)
def test_every_way_of_typing_one_number_gives_one_account(raw):
    assert normalise_phone(raw) == "+212612345678"


@pytest.mark.parametrize("prefix", ["5", "6", "7"])
def test_landline_and_both_mobile_prefixes_are_accepted(prefix):
    assert normalise_phone(f"0{prefix}12345678") == f"+212{prefix}12345678"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "0612345",          # too short
        "06123456789",      # too long
        "0812345678",       # 8 is not a Moroccan prefix
        "0012345678",
        "+33612345678",     # French
        "abcdefghij",
        "+212",
        "612345678a",
    ],
)
def test_rubbish_is_refused(raw):
    with pytest.raises(DomainError) as exc:
        normalise_phone(raw)
    assert exc.value.code is ErrorCode.PHONE_INVALID
    assert not is_valid_phone(raw)


def test_national_format_is_for_display_only():
    assert national_format("+212612345678") == "0612345678"
    # Anything not E.164 is handed back untouched rather than mangled.
    assert national_format("0612345678") == "0612345678"
