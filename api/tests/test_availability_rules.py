"""Whether a tradesman is taking work, as arithmetic on two fields.

Nothing derived is stored, so the whole feature is this function being right.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.core.availability import MAX_AWAY_DAYS, is_available, validate_pause

TODAY = date(2026, 9, 5)


def available(accepting_work=True, back_on=None):
    return is_available(accepting_work=accepting_work, back_on=back_on, today=TODAY)


class TestWhetherHeIsAvailable:
    def test_taking_work_is_available(self):
        assert available() is True

    def test_a_pause_with_no_date_stays_paused(self):
        assert available(accepting_work=False) is False

    def test_a_pause_that_has_not_ended_is_still_a_pause(self):
        assert available(accepting_work=False, back_on=TODAY + timedelta(days=1)) is False

    def test_a_pause_ends_on_the_day_he_said(self):
        """He set the date, and the date is the promise — whatever the switch
        still says."""
        assert available(accepting_work=False, back_on=TODAY) is True

    def test_a_date_already_gone_ends_it_too(self):
        assert available(accepting_work=False, back_on=TODAY - timedelta(days=30)) is True

    def test_a_stale_date_never_takes_away_an_active_switch(self):
        """Turning the switch back on wins over anything left in the date."""
        assert available(accepting_work=True, back_on=TODAY + timedelta(days=9)) is True


class TestTheReturnDate:
    def test_no_date_is_a_pause_until_he_says_otherwise(self):
        assert validate_pause(back_on=None, today=TODAY) is None

    def test_tomorrow_is_fine(self):
        wanted = TODAY + timedelta(days=1)
        assert validate_pause(back_on=wanted, today=TODAY) == wanted

    @pytest.mark.parametrize("offset", [0, -1, -365])
    def test_a_date_already_gone_is_refused(self, offset):
        """A pause that ends before it starts. He meant a date, so he is asked
        for one rather than quietly not paused."""
        with pytest.raises(ValueError, match="back_on"):
            validate_pause(back_on=TODAY + timedelta(days=offset), today=TODAY)

    def test_the_far_edge_is_allowed(self):
        wanted = TODAY + timedelta(days=MAX_AWAY_DAYS)
        assert validate_pause(back_on=wanted, today=TODAY) == wanted

    def test_further_than_a_year_is_leaving_not_a_holiday(self):
        with pytest.raises(ValueError, match="back_on"):
            validate_pause(back_on=TODAY + timedelta(days=MAX_AWAY_DAYS + 1), today=TODAY)
