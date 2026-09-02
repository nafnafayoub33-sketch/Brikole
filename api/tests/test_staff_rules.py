"""A3's refusals, with no database in sight."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.enums import Role, UserStatus
from app.core.errors import DomainError, ErrorCode
from app.core.staff import (
    MAX_SUSPENSION_DAYS,
    assert_not_last_admin,
    assert_not_self,
    assert_suspended,
    build_suspension,
    validate_new_staff_role,
    validate_reason,
    validate_role_change,
)

NOW = datetime(2026, 9, 2, 12, 0, 0)


def code(excinfo: pytest.ExceptionInfo[DomainError]) -> ErrorCode:
    return excinfo.value.code


class TestActingOnYourself:
    def test_an_admin_cannot_act_on_his_own_account(self):
        """Suspending yourself locks you out of the screen that would undo it."""
        with pytest.raises(DomainError) as excinfo:
            assert_not_self(7, 7)
        assert code(excinfo) is ErrorCode.SELF_ACTION_REFUSED

    def test_anybody_else_is_fine(self):
        assert_not_self(7, 8)


class TestTheLastAdmin:
    def test_the_last_active_admin_cannot_be_taken(self):
        """Two admins could otherwise suspend each other and leave nobody."""
        with pytest.raises(DomainError) as excinfo:
            assert_not_last_admin(
                target_role=Role.ADMIN,
                target_status=UserStatus.ACTIVE,
                other_active_admins=0,
            )
        assert code(excinfo) is ErrorCode.LAST_ADMIN

    def test_one_of_two_admins_can_be_taken(self):
        assert_not_last_admin(
            target_role=Role.ADMIN, target_status=UserStatus.ACTIVE, other_active_admins=1
        )

    def test_an_admin_who_is_already_suspended_is_not_holding_the_platform_up(self):
        assert_not_last_admin(
            target_role=Role.ADMIN,
            target_status=UserStatus.SUSPENDED,
            other_active_admins=0,
        )

    def test_the_guard_is_about_admins_only(self):
        assert_not_last_admin(
            target_role=Role.MODERATOR,
            target_status=UserStatus.ACTIVE,
            other_active_admins=0,
        )


class TestChangingARole:
    def test_a_client_can_be_made_a_moderator(self):
        assert (
            validate_role_change(
                current=Role.CLIENT, new=Role.MODERATOR, has_provider_profile=False
            )
            is Role.MODERATOR
        )

    def test_nobody_is_made_a_tradesman_from_a_dropdown(self):
        """A m3allem is an application with a CIN behind it — M1, then A2."""
        with pytest.raises(DomainError) as excinfo:
            validate_role_change(
                current=Role.CLIENT, new=Role.PROVIDER, has_provider_profile=False
            )
        assert code(excinfo) is ErrorCode.ROLE_NOT_ASSIGNABLE

    def test_a_tradesmans_role_is_locked_by_his_profile(self):
        """His offers, jobs and credit all hang off it."""
        with pytest.raises(DomainError) as excinfo:
            validate_role_change(
                current=Role.PROVIDER, new=Role.CLIENT, has_provider_profile=True
            )
        assert code(excinfo) is ErrorCode.PROVIDER_ROLE_LOCKED

    def test_a_profile_locks_the_role_even_when_the_role_says_otherwise(self):
        """Belt and braces: the profile is what the rest of the app reads."""
        with pytest.raises(DomainError) as excinfo:
            validate_role_change(
                current=Role.CLIENT, new=Role.ADMIN, has_provider_profile=True
            )
        assert code(excinfo) is ErrorCode.PROVIDER_ROLE_LOCKED

    def test_setting_the_role_somebody_already_has_is_a_conflict(self):
        with pytest.raises(DomainError) as excinfo:
            validate_role_change(
                current=Role.ADMIN, new=Role.ADMIN, has_provider_profile=False
            )
        assert code(excinfo) is ErrorCode.CONFLICT


class TestCreatingStaff:
    @pytest.mark.parametrize("role", [Role.MODERATOR, Role.ADMIN])
    def test_staff_are_created_here(self, role):
        assert validate_new_staff_role(role) is role

    @pytest.mark.parametrize("role", [Role.CLIENT, Role.PROVIDER])
    def test_everyone_else_arrives_on_their_own(self, role):
        with pytest.raises(DomainError) as excinfo:
            validate_new_staff_role(role)
        assert code(excinfo) is ErrorCode.ROLE_NOT_ASSIGNABLE


class TestSuspending:
    def test_a_suspension_ends_on_a_date(self):
        suspension = build_suspension(
            days=7, reason="Faux devis", now=NOW, may_suspend_permanently=True
        )
        assert suspension.until == NOW + timedelta(days=7)
        assert suspension.reason == "Faux devis"

    def test_permanent_is_an_admins_alone(self):
        """A moderator's ceiling is 48 hours, and it is drawn in three places."""
        with pytest.raises(DomainError) as excinfo:
            build_suspension(
                days=None, reason="Faux devis", now=NOW, may_suspend_permanently=False
            )
        assert code(excinfo) is ErrorCode.FORBIDDEN

        forever = build_suspension(
            days=None, reason="Faux devis", now=NOW, may_suspend_permanently=True
        )
        assert forever.until is None

    @pytest.mark.parametrize("days", [0, -1, MAX_SUSPENSION_DAYS + 1])
    def test_a_timed_suspension_stays_inside_a_year(self, days):
        with pytest.raises(DomainError) as excinfo:
            build_suspension(
                days=days, reason="Faux devis", now=NOW, may_suspend_permanently=True
            )
        assert code(excinfo) is ErrorCode.VALIDATION_FAILED

    def test_every_suspension_says_why(self):
        """The person is told, and so is the audit log."""
        with pytest.raises(DomainError) as excinfo:
            validate_reason("   ")
        assert code(excinfo) is ErrorCode.VALIDATION_FAILED

    def test_the_reason_is_trimmed(self):
        assert validate_reason("  Faux devis  ") == "Faux devis"


class TestReactivating:
    def test_only_a_suspended_account_can_be_reactivated(self):
        with pytest.raises(DomainError) as excinfo:
            assert_suspended(UserStatus.ACTIVE)
        assert code(excinfo) is ErrorCode.CONFLICT

    def test_a_suspended_one_passes(self):
        assert_suspended(UserStatus.SUSPENDED)
