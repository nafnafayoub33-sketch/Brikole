"""The four roles, and the separation the moderator role exists for."""

import pytest

from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode
from app.core.permissions import (
    SELF_REGISTERABLE,
    Permission,
    assert_self_registerable,
    has_permission,
    home_path,
    permissions_for,
    require_permission,
    require_role,
)


def test_only_client_and_provider_can_be_self_registered():
    assert frozenset({Role.CLIENT, Role.PROVIDER}) == SELF_REGISTERABLE
    assert assert_self_registerable(Role.CLIENT) is Role.CLIENT
    assert assert_self_registerable(Role.PROVIDER) is Role.PROVIDER

    for staff in (Role.MODERATOR, Role.ADMIN):
        with pytest.raises(DomainError) as exc:
            assert_self_registerable(staff)
        assert exc.value.code is ErrorCode.ROLE_NOT_SELF_REGISTERABLE


def test_a_moderator_never_sees_money():
    """The whole reason the role is not simply a weaker admin."""
    money = {
        Permission.READ_ALL_CREDIT,
        Permission.APPROVE_TOPUP,
        Permission.READ_STATS,
    }
    assert money.isdisjoint(permissions_for(Role.MODERATOR))
    assert money.issubset(permissions_for(Role.ADMIN))


def test_a_moderator_can_arbitrate_and_refund_the_lead_fee():
    for permission in (
        Permission.READ_ALL_DISPUTES,
        Permission.RESOLVE_DISPUTE,
        Permission.REFUND_LEAD_FEE,
        Permission.SUSPEND_TEMPORARY,
    ):
        assert has_permission(Role.MODERATOR, permission)


def test_a_moderator_cannot_suspend_permanently_or_change_a_role():
    assert not has_permission(Role.MODERATOR, Permission.SUSPEND_PERMANENT)
    assert not has_permission(Role.MODERATOR, Permission.CHANGE_ROLE)
    assert not has_permission(Role.MODERATOR, Permission.APPROVE_PROVIDER)


def test_an_admin_has_everything_a_moderator_has():
    assert permissions_for(Role.MODERATOR).issubset(permissions_for(Role.ADMIN))


def test_clients_and_providers_have_no_staff_powers():
    for role in (Role.CLIENT, Role.PROVIDER):
        assert not has_permission(role, Permission.READ_ALL_DISPUTES)
        assert not has_permission(role, Permission.MANAGE_SETTINGS)
        assert not has_permission(role, Permission.APPROVE_PROVIDER)


def test_a_client_cannot_send_an_offer_and_a_provider_cannot_accept_one():
    assert has_permission(Role.CLIENT, Permission.POST_REQUEST)
    assert not has_permission(Role.CLIENT, Permission.SEND_OFFER)
    assert has_permission(Role.PROVIDER, Permission.SEND_OFFER)
    assert not has_permission(Role.PROVIDER, Permission.ACCEPT_OFFER)


def test_require_permission_reports_what_was_missing():
    with pytest.raises(DomainError) as exc:
        require_permission(Role.CLIENT, Permission.MANAGE_SETTINGS)
    assert exc.value.code is ErrorCode.FORBIDDEN
    assert exc.value.details["permission"] == Permission.MANAGE_SETTINGS
    assert exc.value.details["role"] == "client"


def test_require_role():
    require_role(Role.ADMIN, Role.ADMIN, Role.MODERATOR)
    with pytest.raises(DomainError) as exc:
        require_role(Role.CLIENT, Role.ADMIN)
    assert exc.value.code is ErrorCode.FORBIDDEN


def test_every_role_has_a_home():
    assert {home_path(r) for r in Role} == {
        "/client/requests",
        "/pro",
        "/mod/disputes",
        "/admin",
    }
