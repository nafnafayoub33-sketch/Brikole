"""The rule that decides when a tradesman stops being a man answering a
question and starts being a pattern staff should look at.

Framework-free, so the threshold can be argued about without a database.
"""

from __future__ import annotations

import pytest

from app.core.report import CONTACT_FLAG_THRESHOLD, should_flag_contact_sharing


def flag(clients, *, threshold=CONTACT_FLAG_THRESHOLD, already_open=False):
    return should_flag_contact_sharing(
        distinct_clients=clients, threshold=threshold, already_open=already_open
    )


@pytest.mark.parametrize("clients", [0, 1, 2, 9])
def test_below_the_line_nobody_is_told(clients):
    """One client is a man answering a question he was asked. Nine is a habit
    the platform can live with — it is losing nothing it had."""
    assert flag(clients) is False


@pytest.mark.parametrize("clients", [10, 11, 200])
def test_at_and_past_the_line_staff_hear_about_it(clients):
    assert flag(clients) is True


def test_an_open_flag_suppresses_the_next_one():
    """Staff are already looking at him. A queue with the same man in it forty
    times is a queue nobody reads."""
    assert flag(50, already_open=True) is False


def test_the_threshold_is_the_admins_to_move():
    assert flag(3, threshold=3) is True
    assert flag(3, threshold=4) is False


def test_a_threshold_of_one_still_needs_an_attempt():
    """Zero clients is not a flag at any setting — there is nothing to look at."""
    assert flag(0, threshold=1) is False
