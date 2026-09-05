"""A9 — turning a log of actions into an answer about a person.

Framework-free: what counts as which kind of work is a product decision, and
it should be arguable without a database.
"""

from __future__ import annotations

from app.core.audit_actions import AuditAction
from app.core.staff_work import KINDS, WorkKind, summarise


def test_nothing_handled_is_six_zeroes_and_not_an_empty_dict():
    """A moderator who has never touched a dispute is a fact worth seeing, and
    a screen that has to decide whether to render a row has a hole in it."""
    work = summarise({})

    assert work.total == 0
    assert work.by_kind == {kind: 0 for kind in WorkKind}


def test_actions_land_in_their_kind():
    work = summarise(
        {
            AuditAction.PROVIDER_APPROVED: 4,
            AuditAction.PROVIDER_REJECTED: 1,
            AuditAction.DISPUTE_RESOLVED: 3,
            AuditAction.TOPUP_APPROVED: 2,
        }
    )

    assert work.by_kind[WorkKind.APPROVALS] == 5
    assert work.by_kind[WorkKind.DISPUTES] == 3
    assert work.by_kind[WorkKind.MONEY] == 2
    assert work.by_kind[WorkKind.REPORTS] == 0
    assert work.total == 10


def test_an_unclassified_action_still_counts_as_work():
    """The right failure. A new action shows up in the total the day it is
    added, rather than the day somebody remembers to classify it — and the
    gap between the total and the kinds is what makes it noticeable."""
    work = summarise({"something.new": 7, AuditAction.REPORT_HANDLED: 1})

    assert work.total == 8
    assert sum(work.by_kind.values()) == 1


def test_every_action_the_platform_writes_has_a_kind():
    """The guard on the test above: unclassified is a safe *failure*, not a
    state anything should ship in."""
    declared = {
        value
        for name, value in vars(AuditAction).items()
        if not name.startswith("_") and isinstance(value, str)
    }
    assert declared - set(KINDS) == set()
