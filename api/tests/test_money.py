"""Money is integer centimes, and the ledger never goes negative."""

import pytest

from app.core.errors import DomainError, ErrorCode
from app.core.money import (
    MAX_AMOUNT_CENTIMES,
    can_afford,
    credit,
    debit,
    dirhams,
    validate_amount,
)


def test_dirhams_to_centimes():
    assert dirhams(30) == 3000
    assert dirhams(1) == 100
    assert dirhams(0) == 0


@pytest.mark.parametrize("bad", [-1, 0, MAX_AMOUNT_CENTIMES + 1, True, 12.5, "100"])
def test_validate_amount_refuses_nonsense(bad):
    with pytest.raises(DomainError) as exc:
        validate_amount(bad)
    assert exc.value.code is ErrorCode.AMOUNT_INVALID


def test_zero_is_allowed_only_when_asked_for():
    assert validate_amount(0, allow_zero=True) == 0


def test_debit_refuses_to_go_negative():
    assert debit(5000, 1000) == 4000
    with pytest.raises(DomainError) as exc:
        debit(500, 1000)
    assert exc.value.code is ErrorCode.INSUFFICIENT_CREDIT
    # The details are what the screen needs to explain the refusal.
    assert exc.value.details == {"balance_centimes": 500, "required_centimes": 1000}


def test_credit_adds():
    assert credit(0, 10_000) == 10_000


def test_a_free_lead_beats_an_empty_balance():
    assert can_afford(balance_centimes=0, fee_centimes=1000, free_leads=1) is True
    assert can_afford(balance_centimes=0, fee_centimes=1000, free_leads=0) is False
    assert can_afford(balance_centimes=1000, fee_centimes=1000, free_leads=0) is True
    assert can_afford(balance_centimes=999, fee_centimes=1000, free_leads=0) is False
