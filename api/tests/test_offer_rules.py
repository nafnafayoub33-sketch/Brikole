"""The offer bounds and the credit guard, without a database."""

from __future__ import annotations

import pytest

from app.core.money import dirhams
from app.core.offer import MAX_MESSAGE, can_send_offer, validate_offer


def test_a_price_is_tidied_and_kept():
    offer = validate_offer(price_centimes=dirhams(250), message="  Je passe   demain. ")
    assert offer.price_centimes == dirhams(250)
    assert offer.message == "Je passe demain."


def test_no_message_is_fine():
    assert validate_offer(price_centimes=dirhams(250), message=None).message == ""


@pytest.mark.parametrize("price", [0, dirhams(1), dirhams(19), dirhams(200_001)])
def test_a_price_outside_the_bounds_is_refused(price):
    """1 DH is not a price, it is a way to sit top of a list sorted by price."""
    with pytest.raises(ValueError):
        validate_offer(price_centimes=price, message=None)


def test_an_overlong_message_is_refused():
    with pytest.raises(ValueError):
        validate_offer(price_centimes=dirhams(250), message="x" * (MAX_MESSAGE + 1))


def test_a_free_lead_is_enough_to_offer_with_no_money():
    assert can_send_offer(free_leads_left=1, balance_centimes=0, fee_centimes=dirhams(10))


def test_exactly_the_fee_is_enough():
    assert can_send_offer(
        free_leads_left=0, balance_centimes=dirhams(10), fee_centimes=dirhams(10)
    )


def test_a_dirham_short_is_not():
    assert not can_send_offer(
        free_leads_left=0, balance_centimes=dirhams(9), fee_centimes=dirhams(10)
    )


def test_a_debt_does_not_let_him_offer_again():
    """He went negative when a client accepted. He offers again once he tops up."""
    assert not can_send_offer(
        free_leads_left=0, balance_centimes=-dirhams(10), fee_centimes=dirhams(10)
    )
