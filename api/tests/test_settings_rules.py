"""What A7 may set a platform setting to, without a database."""

from __future__ import annotations

import pytest

from app.core.money import dirhams
from app.core.policy import SettingKey
from app.core.settings_rules import MAX_BANK_FIELD, validate_setting


def test_a_lead_fee_inside_the_bounds_is_kept():
    assert validate_setting(SettingKey.DEFAULT_LEAD_FEE, dirhams(15)) == dirhams(15)


@pytest.mark.parametrize("amount", [0, -dirhams(1), dirhams(501)])
def test_a_lead_fee_outside_the_bounds_is_refused(amount):
    """Zero makes the business free, and it is one mistyped digit away."""
    with pytest.raises(ValueError):
        validate_setting(SettingKey.DEFAULT_LEAD_FEE, amount)


def test_a_request_cap_of_zero_would_make_the_product_unusable():
    with pytest.raises(ValueError):
        validate_setting(SettingKey.MAX_OPEN_REQUESTS_PER_CLIENT, 0)


def test_true_is_not_a_number():
    """`bool` is an `int` in Python, and `True` is not a lead fee."""
    with pytest.raises(ValueError):
        validate_setting(SettingKey.DEFAULT_LEAD_FEE, True)


def test_free_leads_may_be_zero_because_that_is_a_real_policy():
    assert validate_setting(SettingKey.FREE_LEADS_NEW_PROVIDER, 0) == 0


def test_maintenance_mode_takes_only_a_flag():
    assert validate_setting(SettingKey.MAINTENANCE_MODE, True) is True
    with pytest.raises(ValueError):
        validate_setting(SettingKey.MAINTENANCE_MODE, 1)


def test_bank_details_are_tidied_field_by_field():
    value = validate_setting(
        SettingKey.BANK_TRANSFER,
        {
            "bank_name": "  Attijariwafa   Bank ",
            "account_holder": "Brikole SARL",
            "rib": "007 780 0001234567890123 45",
            "instructions": "",
        },
    )
    assert value["bank_name"] == "Attijariwafa Bank"
    assert value["instructions"] == ""


def test_empty_bank_details_are_a_legitimate_state():
    """M9 says "not filled in yet" rather than showing blanks to transfer into."""
    value = validate_setting(SettingKey.BANK_TRANSFER, {})
    assert value == {"bank_name": "", "account_holder": "", "rib": "", "instructions": ""}


def test_an_overlong_bank_field_is_refused():
    with pytest.raises(ValueError):
        validate_setting(
            SettingKey.BANK_TRANSFER, {"rib": "x" * (MAX_BANK_FIELD + 1)}
        )


def test_a_key_a7_does_not_own_is_refused():
    with pytest.raises(ValueError):
        validate_setting("something_else", 1)
