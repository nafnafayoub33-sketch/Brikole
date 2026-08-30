"""The top-up bounds, without a database."""

from __future__ import annotations

import pytest

from app.core.money import dirhams
from app.core.topup import MAX_REFERENCE, leads_bought, validate_topup


def test_a_reference_is_tidied_and_kept():
    topup = validate_topup(amount_centimes=dirhams(500), reference="  TRF  99 12  ")
    assert topup.reference == "TRF 99 12"
    assert topup.amount_centimes == dirhams(500)


@pytest.mark.parametrize("reference", [None, "", "   "])
def test_a_missing_reference_is_refused(reference):
    """It is what an admin types into a bank statement search. Without it the
    approval screen is a list of claims nobody can check."""
    with pytest.raises(ValueError):
        validate_topup(amount_centimes=dirhams(500), reference=reference)


def test_an_overlong_reference_is_refused():
    with pytest.raises(ValueError):
        validate_topup(amount_centimes=dirhams(500), reference="x" * (MAX_REFERENCE + 1))


@pytest.mark.parametrize("amount", [0, dirhams(49), dirhams(20_001)])
def test_an_amount_outside_the_bounds_is_refused(amount):
    with pytest.raises(ValueError):
        validate_topup(amount_centimes=amount, reference="TRF1")


def test_an_amount_is_shown_as_the_jobs_it_buys():
    """"500 DH" means nothing to a tradesman deciding how much to transfer."""
    assert leads_bought(dirhams(500), dirhams(10)) == 50
    assert leads_bought(dirhams(95), dirhams(10)) == 9


def test_a_zero_fee_buys_no_leads_rather_than_dividing_by_zero():
    assert leads_bought(dirhams(500), 0) == 0
