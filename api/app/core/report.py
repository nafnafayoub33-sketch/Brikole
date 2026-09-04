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
    #: Filed by the platform, not by a person: this tradesman keeps trying to
    #: hand his number to clients in the chat. See `should_flag_contact_sharing`.
    CONTACT_SHARING = "contact_sharing"


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

#: How many *different clients* a tradesman may try to hand his number to
#: before staff are told about him. One is a man answering a question. Ten is
#: a business being run off the back of the platform.
CONTACT_FLAG_THRESHOLD = 10


def should_flag_contact_sharing(
    *, distinct_clients: int, threshold: int, already_open: bool
) -> bool:
    """Whether this attempt is the one that puts him in front of staff.

    Counted in **clients, not messages**. A tradesman who writes his number
    four times to one client who is not reading is being persistent, and
    counting messages would make persistence look like a pattern. The pattern
    that matters is the same move made to stranger after stranger.

    An open flag suppresses the next one. Staff are looking at him already,
    and a queue with the same man in it forty times is a queue nobody reads.
    """
    return distinct_clients >= threshold and not already_open


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
