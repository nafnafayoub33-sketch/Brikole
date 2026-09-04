"""Paid placement, as arithmetic.

The interesting cases are all about time: what a renewal does to days he has
already paid for, and what an expired boost is worth.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.boost import BOOST_DAYS, BoostRefused, buy, is_active
from app.core.money import dirhams

NOW = datetime(2026, 9, 4, 12, 0, 0)
PRICE = dirhams(20)
FUNDED = dirhams(100)


def bought(boosted_until=None, balance=FUNDED):
    return buy(
        boosted_until=boosted_until,
        balance_centimes=balance,
        price_centimes=PRICE,
        now=NOW,
    )


class TestWhatItCosts:
    def test_the_price_comes_out_of_the_balance(self):
        result = bought(balance=FUNDED)
        assert result.price_centimes == PRICE
        assert result.balance_after_centimes == dirhams(80)

    def test_exactly_enough_is_enough(self):
        assert bought(balance=PRICE).balance_after_centimes == 0

    def test_a_dirham_short_is_refused(self):
        """This one really does refuse, where the lead fee does not: nobody is
        waiting on a boost, so he is told to top up rather than put into debt
        for something he chose."""
        with pytest.raises(BoostRefused):
            bought(balance=PRICE - dirhams(1))


class TestHowLongItLasts:
    def test_a_first_boost_runs_from_today(self):
        assert bought().expires_at == NOW + timedelta(days=BOOST_DAYS)

    def test_renewing_early_keeps_the_days_he_already_paid_for(self):
        """He renews on the 25th of a month he bought on the 1st. Restarting
        from today would quietly take five days off him, and he would find out
        by counting."""
        five_left = NOW + timedelta(days=5)
        assert bought(boosted_until=five_left).expires_at == five_left + timedelta(
            days=BOOST_DAYS
        )

    def test_a_lapsed_boost_does_not_backdate_the_new_one(self):
        """Buying again in March must not spend days in February."""
        lapsed = NOW - timedelta(days=10)
        assert bought(boosted_until=lapsed).expires_at == NOW + timedelta(days=BOOST_DAYS)

    def test_the_moment_it_expires_it_is_over(self):
        assert is_active(NOW, NOW) is False
        assert is_active(NOW + timedelta(seconds=1), NOW) is True
        assert is_active(None, NOW) is False

    def test_a_month_is_thirty_days_in_every_month(self):
        """Calendar months would make February cheaper than March for no
        reason a tradesman could be told."""
        february = datetime(2026, 2, 1, 9, 0, 0)
        result = buy(
            boosted_until=None,
            balance_centimes=dirhams(100),
            price_centimes=PRICE,
            now=february,
        )
        assert (result.expires_at - february).days == BOOST_DAYS
