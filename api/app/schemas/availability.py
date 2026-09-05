"""Whether a tradesman is taking work.

Its own module because both sides read it: P3 shows a client when somebody is
back, and M8 shows the tradesman what he set. Putting it in `schemas/pro.py`
would make the public profile import the tradesman's own.
"""

from __future__ import annotations

from datetime import date

from app.schemas.common import ApiModel


class AvailabilityOut(ApiModel):
    #: What he typed.
    accepting_work: bool
    #: When a pause lifts. Null on an open-ended one.
    back_on: date | None
    #: Whether clients can find him *today* — the status folded in, so a
    #: pending applicant reads as unavailable however his switch is set.
    #: Computed, never stored: a stored answer goes stale the moment the
    #: return date passes.
    is_available: bool
