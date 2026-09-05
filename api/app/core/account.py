"""What a person may change about their own account, and when they may leave.

C7, M11 and D4 are the same screen for three different roles, so the rules are
in one place. Two of them are worth stating out loud:

* **The phone number is not editable.** It is the identity — it is what signs
  him in, what an admin asks for on the P6 call, and what the platform means by
  "this person". Changing it is taking over an account, and there is no reason
  a person needs it that a new registration does not serve better.
* **Leaving is refused while work is live.** A tradesman is on his way to a
  house; a client is owed a job he has paid nothing for yet. Deleting either
  side mid-job leaves the other holding a row that points at nobody.
"""

from __future__ import annotations

from app.core.enums import DisputeStatus, JobStatus
from app.core.errors import DomainError, ErrorCode

MIN_NAME = 2
MAX_NAME = 120

LANGUAGES = ("ar", "fr", "en")

#: A job that has not finished. `DONE` is in here on purpose: the tradesman has
#: said he is finished and the client has not confirmed it, which is exactly the
#: moment a disappearing account does the most damage — the review, the credit
#: and the dispute window all still hang off it.
LIVE_JOBS = frozenset({JobStatus.ASSIGNED, JobStatus.IN_PROGRESS, JobStatus.DONE})

#: A dispute nobody has ruled on. Deleting an account mid-dispute deletes one
#: side's case, and the moderator is left with half a story.
LIVE_DISPUTES = frozenset({DisputeStatus.OPEN, DisputeStatus.CLAIMED})


def validate_name(value: str) -> str:
    """Collapse the whitespace, then insist on something left."""
    cleaned = " ".join(value.split())
    if not (MIN_NAME <= len(cleaned) <= MAX_NAME):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="full_name")
    return cleaned


def validate_language(value: str) -> str:
    if value not in LANGUAGES:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="language")
    return value


def can_delete(*, live_jobs: int, live_disputes: int) -> bool:
    """Whether the account may close. The screen reads this answer rather than
    recomputing it, so the button and the refusal cannot drift apart."""
    return live_jobs == 0 and live_disputes == 0


def assert_can_delete(*, live_jobs: int, live_disputes: int) -> None:
    """Refuse to close an account that somebody else is still relying on.

    Names one blocker rather than listing both: finishing the job usually
    clears the dispute too, and telling somebody two things are wrong when one
    action fixes both is noise.
    """
    if live_jobs:
        raise DomainError(ErrorCode.CONFLICT, blocker="jobs", count=live_jobs)
    if live_disputes:
        raise DomainError(ErrorCode.CONFLICT, blocker="disputes", count=live_disputes)
