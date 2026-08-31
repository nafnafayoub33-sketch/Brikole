"""Reports: what may be flagged, why, and what a moderator may do about it.

Framework-free. The boundary this module draws: a moderator dismisses, hides a
piece of content, warns, or suspends for 48 hours. Anything heavier — closing an
account for good — is an admin's decision, and there is deliberately no value
here that expresses it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MIN_DESCRIPTION = 0
MAX_DESCRIPTION = 1000


class ReportTarget(StrEnum):
    """What can be flagged. `provider_profile` is the shop window; `review` is
    one piece of text on it."""

    PROVIDER_PROFILE = "provider_profile"
    REVIEW = "review"


class ReportReason(StrEnum):
    SPAM = "spam"
    OFFENSIVE = "offensive"
    FAKE = "fake"
    WRONG_INFO = "wrong_info"
    OTHER = "other"


class ReportStatus(StrEnum):
    OPEN = "open"
    HANDLED = "handled"


class ReportOutcome(StrEnum):
    """What a moderator decided. Ordered by weight, and stopping short of the
    one he may not reach."""

    DISMISSED = "dismissed"
    CONTENT_HIDDEN = "content_hidden"
    WARNED = "warned"
    SUSPENDED = "suspended"


#: Hiding needs something to hide. A profile is not a piece of content: taking
#: a tradesman off the market is a suspension, and calling it "hidden" would
#: leave nothing on the record explaining why he vanished.
HIDEABLE: frozenset[ReportTarget] = frozenset({ReportTarget.REVIEW})

#: A moderator's suspension is temporary, always. Permanence is an admin's.
SUSPENSION_HOURS = 48


@dataclass(frozen=True, slots=True)
class NewReport:
    target_type: ReportTarget
    target_id: int
    reason: ReportReason
    description: str


def validate_report(
    *, target_type: str, target_id: int, reason: str, description: str | None
) -> NewReport:
    try:
        target = ReportTarget(target_type)
    except ValueError as error:
        raise ValueError("target_type") from error

    try:
        why = ReportReason(reason)
    except ValueError as error:
        raise ValueError("reason") from error

    if target_id <= 0:
        raise ValueError("target_id")

    cleaned = " ".join((description or "").split())
    if len(cleaned) > MAX_DESCRIPTION:
        raise ValueError("description")

    # "Other" with nothing written is a report a moderator cannot act on: every
    # other reason carries its own meaning, this one carries none.
    if why is ReportReason.OTHER and not cleaned:
        raise ValueError("description")

    return NewReport(
        target_type=target, target_id=target_id, reason=why, description=cleaned
    )


def can_hide(target_type: ReportTarget) -> bool:
    return target_type in HIDEABLE
