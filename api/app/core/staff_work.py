"""A9 — what a moderator or an admin has actually done.

Every staff action already lands in `audit_log`, so the work is countable
without a second table. What is *not* obvious from the log is what the counts
mean: fifteen action strings is a list, six kinds of work is an answer to
"what does this person do here".

The grouping is a product decision — these are the jobs the platform has —
so it lives here, framework-free, rather than in a router or a screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.audit_actions import AuditAction


class WorkKind(StrEnum):
    """The six things staff spend their time on."""

    #: A2 — letting a tradesman onto the platform, or not.
    APPROVALS = "approvals"
    #: D1 — arbitrating between two people who disagree.
    DISPUTES = "disputes"
    #: D3 — flagged content and flagged people.
    REPORTS = "reports"
    #: A5 — confirming a bank transfer landed. The only work that moves money.
    MONEY = "money"
    #: A3 and A9 — suspending, reactivating, changing a role, resetting a
    #: password, adding staff.
    ACCOUNTS = "accounts"
    #: A4, A6, A7 — the settings, the catalogue, a cancelled request.
    PLATFORM = "platform"


#: Which action counts as which kind. An action missing from here is counted
#: in the total and in nothing else, which is the right failure: a new action
#: shows up as work done before anybody remembers to classify it.
KINDS: dict[str, WorkKind] = {
    AuditAction.PROVIDER_APPROVED: WorkKind.APPROVALS,
    AuditAction.PROVIDER_REJECTED: WorkKind.APPROVALS,
    AuditAction.DISPUTE_RESOLVED: WorkKind.DISPUTES,
    AuditAction.REPORT_HANDLED: WorkKind.REPORTS,
    AuditAction.TOPUP_APPROVED: WorkKind.MONEY,
    AuditAction.TOPUP_REJECTED: WorkKind.MONEY,
    AuditAction.USER_SUSPENDED: WorkKind.ACCOUNTS,
    AuditAction.USER_REACTIVATED: WorkKind.ACCOUNTS,
    AuditAction.USER_ROLE_CHANGED: WorkKind.ACCOUNTS,
    AuditAction.PASSWORD_RESET: WorkKind.ACCOUNTS,
    AuditAction.STAFF_CREATED: WorkKind.ACCOUNTS,
    AuditAction.SETTING_CHANGED: WorkKind.PLATFORM,
    AuditAction.REQUEST_CANCELLED: WorkKind.PLATFORM,
    AuditAction.TRADE_CREATED: WorkKind.PLATFORM,
    AuditAction.TRADE_UPDATED: WorkKind.PLATFORM,
    AuditAction.CITY_CREATED: WorkKind.PLATFORM,
    AuditAction.CITY_UPDATED: WorkKind.PLATFORM,
}


@dataclass(frozen=True, slots=True)
class Work:
    """One person's record, as A9 reads it."""

    total: int
    by_kind: dict[WorkKind, int]


def summarise(counts: dict[str, int]) -> Work:
    """Turn a count per action into a count per kind of work.

    Every kind is present even at zero. A moderator who has never touched a
    dispute is a fact worth seeing, and a screen that has to decide whether to
    render a row is a screen with a hole in it.
    """
    by_kind = {kind: 0 for kind in WorkKind}
    total = 0

    for action, count in counts.items():
        total += count
        kind = KINDS.get(action)
        if kind is not None:
            by_kind[kind] += count

    return Work(total=total, by_kind=by_kind)
