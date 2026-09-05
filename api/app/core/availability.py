"""Whether a tradesman is taking work, and until when he is not.

The problem this exists for: a plumber on holiday keeps appearing in search,
keeps being asked, and keeps not answering — which costs him his rating and
costs three clients a day each. A switch he can turn off fixes that, and a
switch he forgets to turn back on creates the opposite problem, so the pause
carries a date and lifts itself.

**Nothing derived is stored.** `accepting_work` and `back_on` are exactly what
he typed; whether he is available *right now* is computed from them wherever it
is needed. A stored answer would drift out of date the moment the return date
passed, which is the same bug class as a boost that never expires.

**What a pause does and does not do.** It takes him out of search and out of
the trade counts, so no client finds him. It does not close his own feed: the
requests he can see are the likeliest reason he comes back early, and hiding
them makes a pause feel like a punishment. He can still take work he finds
himself — one sentence, no strange interactions.
"""

from __future__ import annotations

from datetime import date, timedelta

#: How far ahead a return date may be. Longer than this is not a holiday, it
#: is leaving — and leaving is a pause with no date on it.
MAX_AWAY_DAYS = 365


def is_available(*, accepting_work: bool, back_on: date | None, today: date) -> bool:
    """Whether clients should be able to find him today.

    A pause with a date that has passed is over, whatever the switch still
    says: he set the date, and the date is the promise.
    """
    if accepting_work:
        return True
    return back_on is not None and back_on <= today


def validate_pause(*, back_on: date | None, today: date) -> date | None:
    """The return date on a pause, or `None` for "until I say otherwise".

    Raises `ValueError("back_on")`.
    """
    if back_on is None:
        return None

    if back_on <= today:
        # A date already gone is a pause that ends before it starts. He meant
        # a date, so he is asked for one rather than quietly not paused.
        raise ValueError("back_on")

    if back_on > today + timedelta(days=MAX_AWAY_DAYS):
        raise ValueError("back_on")

    return back_on
