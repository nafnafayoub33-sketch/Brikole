"""The dispute rules, without a database."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.dispute import (
    MAX_EVIDENCE,
    at_fault_party,
    is_stale,
    refund_allowed,
    validate_dispute,
    within_window,
)
from app.core.enums import DisputeReason, DisputeVerdict

NOW = datetime(2026, 8, 30, 12, 0)


def test_a_description_is_tidied_and_kept():
    dispute = validate_dispute(
        reason=DisputeReason.NO_SHOW,
        description="  Il n'est   jamais venu, j'ai attendu toute la journée.  ",
    )
    assert dispute.description == "Il n'est jamais venu, j'ai attendu toute la journée."


def test_a_description_too_short_to_judge_is_refused():
    with pytest.raises(ValueError):
        validate_dispute(reason=DisputeReason.NO_SHOW, description="pas venu")


def test_duplicate_evidence_is_collapsed():
    dispute = validate_dispute(
        reason=DisputeReason.DAMAGE,
        description="Il a cassé le lavabo en démontant le siphon, photos jointes.",
        evidence_paths=["a.jpg", "a.jpg", "b.jpg", ""],
    )
    assert dispute.evidence_paths == ("a.jpg", "b.jpg")


def test_too_much_evidence_is_refused():
    with pytest.raises(ValueError):
        validate_dispute(
            reason=DisputeReason.DAMAGE,
            description="Il a cassé le lavabo en démontant le siphon, photos jointes.",
            evidence_paths=[f"{index}.jpg" for index in range(MAX_EVIDENCE + 1)],
        )


def test_the_window_runs_from_when_the_work_finished():
    """Not from confirmation: a client who never confirms would otherwise hold
    the window open forever."""
    assert within_window(NOW - timedelta(days=6), NOW, days=7)
    assert not within_window(NOW - timedelta(days=8), NOW, days=7)


def test_work_still_in_progress_has_no_clock_yet():
    assert within_window(None, NOW, days=7)


def test_only_a_client_at_fault_returns_the_lead_fee():
    """The fee bought a real introduction. It comes back when the person who
    wasted it was on the other side — not as a way of splitting the difference."""
    assert refund_allowed(DisputeVerdict.CLIENT_AT_FAULT)
    assert not refund_allowed(DisputeVerdict.PROVIDER_AT_FAULT)
    assert not refund_allowed(DisputeVerdict.NO_FAULT)


def test_no_fault_blames_nobody():
    assert at_fault_party(DisputeVerdict.CLIENT_AT_FAULT) == "client"
    assert at_fault_party(DisputeVerdict.PROVIDER_AT_FAULT) == "provider"
    assert at_fault_party(DisputeVerdict.NO_FAULT) is None


def test_a_case_nobody_picked_up_in_two_days_is_flagged():
    assert is_stale(NOW - timedelta(hours=49), NOW)
    assert not is_stale(NOW - timedelta(hours=47), NOW)
