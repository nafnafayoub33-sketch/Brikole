"""What may be reported, and what a moderator may do about it."""

from __future__ import annotations

import pytest

from app.core.report import (
    MAX_DESCRIPTION,
    ReportOutcome,
    ReportTarget,
    can_hide,
    validate_report,
)


def base(**overrides):
    payload = {
        "target_type": "review",
        "target_id": 7,
        "reason": "offensive",
        "description": "  Insultes   dans le commentaire. ",
    }
    payload.update(overrides)
    return validate_report(**payload)


def test_a_description_is_tidied_and_kept():
    assert base().description == "Insultes dans le commentaire."


@pytest.mark.parametrize("target", ["review", "provider_profile"])
def test_both_targets_are_accepted(target):
    assert base(target_type=target).target_type == ReportTarget(target)


def test_an_unknown_target_is_refused():
    with pytest.raises(ValueError):
        base(target_type="job")


def test_an_unknown_reason_is_refused():
    with pytest.raises(ValueError):
        base(reason="because")


def test_other_with_nothing_written_is_refused():
    """Every other reason carries its own meaning; this one carries none."""
    with pytest.raises(ValueError):
        base(reason="other", description="   ")

    assert base(reason="other", description="Il se fait passer pour un autre.")


def test_a_named_reason_needs_no_description():
    assert base(reason="spam", description=None).description == ""


def test_an_overlong_description_is_refused():
    with pytest.raises(ValueError):
        base(description="x" * (MAX_DESCRIPTION + 1))


def test_only_a_review_can_be_hidden():
    """Taking a tradesman off the market is a suspension. Calling it "hidden"
    would leave nothing on the record saying why he went."""
    assert can_hide(ReportTarget.REVIEW)
    assert not can_hide(ReportTarget.PROVIDER_PROFILE)


def test_a_moderator_has_no_outcome_that_closes_an_account():
    """The ceiling is drawn in the vocabulary itself, not remembered in code."""
    assert {outcome.value for outcome in ReportOutcome} == {
        "dismissed",
        "content_hidden",
        "warned",
        "suspended",
    }
