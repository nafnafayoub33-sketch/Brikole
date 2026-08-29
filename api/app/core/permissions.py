"""Who may do what.

The single source of truth for the four roles. The API asks this module; the
web app asks the same shape of question over `/auth/me` so a screen never has
to hardcode a role name.

The rule that matters most: a moderator resolves disputes and sees **nothing**
about money. That separation is the entire reason the role is not just a weaker
admin, and it is enforced here rather than remembered in each router.
"""

from __future__ import annotations

from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode

#: Roles a stranger may pick at registration. Staff accounts are made by admins.
SELF_REGISTERABLE: frozenset[Role] = frozenset({Role.CLIENT, Role.PROVIDER})

STAFF: frozenset[Role] = frozenset({Role.MODERATOR, Role.ADMIN})


class Permission:
    """Named capabilities. Strings, so `/auth/me` can ship them to the client."""

    POST_REQUEST = "request.post"
    SEND_OFFER = "offer.send"
    ACCEPT_OFFER = "offer.accept"

    READ_OWN_DISPUTES = "dispute.read.own"
    READ_ALL_DISPUTES = "dispute.read.all"
    RESOLVE_DISPUTE = "dispute.resolve"
    REFUND_LEAD_FEE = "dispute.refund_lead_fee"

    SUSPEND_TEMPORARY = "user.suspend.temporary"
    SUSPEND_PERMANENT = "user.suspend.permanent"
    CHANGE_ROLE = "user.role.change"
    APPROVE_PROVIDER = "provider.approve"

    READ_OWN_CREDIT = "credit.read.own"
    READ_ALL_CREDIT = "credit.read.all"
    APPROVE_TOPUP = "topup.approve"

    MANAGE_CATALOG = "catalog.manage"
    MANAGE_SETTINGS = "settings.manage"
    READ_AUDIT_LOG = "audit.read"
    READ_STATS = "stats.read"


_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.CLIENT: frozenset(
        {
            Permission.POST_REQUEST,
            Permission.ACCEPT_OFFER,
            Permission.READ_OWN_DISPUTES,
        }
    ),
    Role.PROVIDER: frozenset(
        {
            Permission.SEND_OFFER,
            Permission.READ_OWN_DISPUTES,
            Permission.READ_OWN_CREDIT,
        }
    ),
    Role.MODERATOR: frozenset(
        {
            Permission.READ_ALL_DISPUTES,
            Permission.RESOLVE_DISPUTE,
            Permission.REFUND_LEAD_FEE,
            Permission.SUSPEND_TEMPORARY,
        }
    ),
    Role.ADMIN: frozenset(
        {
            Permission.READ_ALL_DISPUTES,
            Permission.RESOLVE_DISPUTE,
            Permission.REFUND_LEAD_FEE,
            Permission.SUSPEND_TEMPORARY,
            Permission.SUSPEND_PERMANENT,
            Permission.CHANGE_ROLE,
            Permission.APPROVE_PROVIDER,
            Permission.READ_ALL_CREDIT,
            Permission.APPROVE_TOPUP,
            Permission.MANAGE_CATALOG,
            Permission.MANAGE_SETTINGS,
            Permission.READ_AUDIT_LOG,
            Permission.READ_STATS,
        }
    ),
}


def permissions_for(role: Role) -> frozenset[str]:
    return _PERMISSIONS[role]


def has_permission(role: Role, permission: str) -> bool:
    return permission in _PERMISSIONS[role]


def require_permission(role: Role, permission: str) -> None:
    if not has_permission(role, permission):
        raise DomainError(ErrorCode.FORBIDDEN, permission=permission, role=role.value)


def require_role(role: Role, *allowed: Role) -> None:
    if role not in allowed:
        raise DomainError(
            ErrorCode.FORBIDDEN,
            role=role.value,
            allowed=[r.value for r in allowed],
        )


def assert_self_registerable(role: Role) -> Role:
    """Registration accepts `client` and `provider`. Nothing else, ever."""
    if role not in SELF_REGISTERABLE:
        raise DomainError(ErrorCode.ROLE_NOT_SELF_REGISTERABLE, role=role.value)
    return role


def home_path(role: Role) -> str:
    """Where a signed-in user of this role belongs. Mirrored in the web router."""
    return {
        Role.CLIENT: "/client/requests",
        Role.PROVIDER: "/pro",
        Role.MODERATOR: "/mod/disputes",
        Role.ADMIN: "/admin",
    }[role]
