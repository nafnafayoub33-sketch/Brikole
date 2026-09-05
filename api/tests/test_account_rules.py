"""The rules behind C7, M11 and D4, without a database."""

from __future__ import annotations

import pytest

from app.core.account import (
    LIVE_DISPUTES,
    LIVE_JOBS,
    assert_can_delete,
    can_delete,
    validate_language,
    validate_name,
)
from app.core.enums import DisputeStatus, JobStatus
from app.core.errors import DomainError


class TestTheName:
    def test_it_collapses_the_whitespace(self) -> None:
        assert validate_name("  Youssef   El  Alami ") == "Youssef El Alami"

    @pytest.mark.parametrize("value", ["", "   ", "\n", "Y"])
    def test_nothing_left_is_refused(self, value: str) -> None:
        with pytest.raises(DomainError):
            validate_name(value)

    def test_a_name_longer_than_the_column_is_refused(self) -> None:
        with pytest.raises(DomainError):
            validate_name("a" * 200)


class TestTheLanguage:
    @pytest.mark.parametrize("value", ["ar", "fr", "en"])
    def test_the_three_the_app_speaks(self, value: str) -> None:
        assert validate_language(value) == value

    @pytest.mark.parametrize("value", ["es", "AR", "", "ar-MA"])
    def test_anything_else_is_refused(self, value: str) -> None:
        with pytest.raises(DomainError):
            validate_language(value)


class TestLeaving:
    def test_a_clean_account_may_go(self) -> None:
        assert_can_delete(live_jobs=0, live_disputes=0)

    @pytest.mark.parametrize(
        ("jobs", "disputes", "allowed"),
        [(0, 0, True), (1, 0, False), (0, 1, False), (2, 3, False)],
    )
    def test_the_predicate_and_the_refusal_agree(
        self, jobs: int, disputes: int, allowed: bool
    ) -> None:
        """The screen reads `can_delete` and the endpoint raises from
        `assert_can_delete`. A button that is offered and then refused is the
        bug this pins down."""
        assert can_delete(live_jobs=jobs, live_disputes=disputes) is allowed

        if allowed:
            assert_can_delete(live_jobs=jobs, live_disputes=disputes)
        else:
            with pytest.raises(DomainError):
                assert_can_delete(live_jobs=jobs, live_disputes=disputes)

    def test_a_job_holds_him_and_says_so(self) -> None:
        with pytest.raises(DomainError) as caught:
            assert_can_delete(live_jobs=2, live_disputes=0)
        assert caught.value.details["blocker"] == "jobs"

    def test_a_dispute_holds_him_too(self) -> None:
        with pytest.raises(DomainError) as caught:
            assert_can_delete(live_jobs=0, live_disputes=1)
        assert caught.value.details["blocker"] == "disputes"

    def test_the_job_is_named_first_when_both_hold_him(self) -> None:
        """One blocker at a time. Telling somebody two things are wrong when
        finishing the job clears both is noise."""
        with pytest.raises(DomainError) as caught:
            assert_can_delete(live_jobs=1, live_disputes=1)
        assert caught.value.details["blocker"] == "jobs"


class TestWhatCountsAsUnfinished:
    def test_a_job_the_client_has_not_confirmed_is_live(self) -> None:
        """The moment a disappearing account does the most damage: the review,
        the credit and the dispute window all still hang off it."""
        assert JobStatus.DONE in LIVE_JOBS

    @pytest.mark.parametrize("status", [JobStatus.CONFIRMED, JobStatus.CANCELLED])
    def test_a_finished_job_is_not(self, status: JobStatus) -> None:
        assert status not in LIVE_JOBS

    def test_a_claimed_dispute_is_still_live(self) -> None:
        """A moderator holding it is not a moderator who has ruled on it."""
        assert DisputeStatus.CLAIMED in LIVE_DISPUTES
        assert DisputeStatus.RESOLVED not in LIVE_DISPUTES
