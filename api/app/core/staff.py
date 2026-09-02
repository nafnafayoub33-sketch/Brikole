"""A3 — the rules for changing somebody else's account.

This is the screen with the most power on the platform, so the refusals are
here, in one framework-free place, rather than spread across a router. Four of
them, and each one is a real way to break the product:

* An admin acting on his own account. Suspending yourself locks you out of the
  screen that would undo it.
* Taking the last admin. Two admins can otherwise suspend each other in turn
  and leave nobody who can approve a tradesman or change a setting again.
* Making somebody a tradesman from a dropdown. A m3allem is an application with
  a CIN and a trade behind it (M1, A2); a role set here would be a provider with
  no profile, invisible to every screen that expects one.
* Changing the role of someone who *has* that profile. His offers, jobs and
  credit all hang off it, and none of them survive him becoming a client.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.enums import Role, UserStatus
from app.core.errors import DomainError, ErrorCode

#: Roles an admin may hand out on A3. Client and provider are missing on
#: purpose: people arrive at those themselves.
ASSIGNABLE: frozenset[Role] = frozenset({Role.CLIENT, Role.MODERATOR, Role.ADMIN})

#: Roles an admin may create outright. A client account is made by the client.
CREATABLE: frozenset[Role] = frozenset({Role.MODERATOR, Role.ADMIN})

#: A suspension has to end somewhere a person can see. Longer than this is
#: what "permanent" is for, and permanent is a separate permission.
MAX_SUSPENSION_DAYS = 365

REASON_MAX = 500


@dataclass(frozen=True, slots=True)
class Suspension:
    """`until` is None for a permanent suspension — the model reads it that way."""

    until: datetime | None
    reason: str


def assert_not_self(actor_id: int, target_id: int) -> None:
    if actor_id == target_id:
        raise DomainError(ErrorCode.SELF_ACTION_REFUSED)


def assert_not_last_admin(
    *, target_role: Role, target_status: UserStatus, other_active_admins: int
) -> None:
    """The platform always keeps one admin who can still sign in.

    Counting *other* admins rather than all of them is the point: the caller
    passes the number that would remain, so this reads the same whether the
    action is a suspension or a demotion.

    Through A3 as it stands this cannot fire, and that is worth knowing rather
    than discovering: the caller is always an active admin, so either he is not
    the target — and is himself the admin who remains — or he is, and
    `assert_not_self` stopped him one line earlier. It is kept because the
    invariant is the platform's, not this router's: the day an account can be
    deleted, or a second path can suspend staff, this is the line that still
    holds.
    """
    if target_role is not Role.ADMIN:
        return
    if target_status is not UserStatus.ACTIVE:
        return
    if other_active_admins == 0:
        raise DomainError(ErrorCode.LAST_ADMIN)


def validate_role_change(*, current: Role, new: Role, has_provider_profile: bool) -> Role:
    """The role an admin may set, or the reason he may not."""
    if new is current:
        raise DomainError(ErrorCode.CONFLICT, role=current.value)

    if has_provider_profile or current is Role.PROVIDER:
        raise DomainError(ErrorCode.PROVIDER_ROLE_LOCKED)

    if new not in ASSIGNABLE:
        raise DomainError(ErrorCode.ROLE_NOT_ASSIGNABLE, role=new.value)

    return new


def validate_new_staff_role(role: Role) -> Role:
    if role not in CREATABLE:
        raise DomainError(ErrorCode.ROLE_NOT_ASSIGNABLE, role=role.value)
    return role


def validate_reason(reason: str) -> str:
    """Every suspension says why. The person is told, and so is the audit log."""
    cleaned = reason.strip()
    if not cleaned or len(cleaned) > REASON_MAX:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="reason", max_length=REASON_MAX)
    return cleaned


def build_suspension(
    *, days: int | None, reason: str, now: datetime, may_suspend_permanently: bool
) -> Suspension:
    """`days=None` means permanent, and only an admin may ask for it."""
    cleaned = validate_reason(reason)

    if days is None:
        if not may_suspend_permanently:
            raise DomainError(ErrorCode.FORBIDDEN)
        return Suspension(until=None, reason=cleaned)

    if days < 1 or days > MAX_SUSPENSION_DAYS:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="days", max_days=MAX_SUSPENSION_DAYS
        )

    return Suspension(until=now + timedelta(days=days), reason=cleaned)


def assert_suspended(status: UserStatus) -> None:
    """Reactivating an account nobody suspended is a bug in the caller."""
    if status is not UserStatus.SUSPENDED:
        raise DomainError(ErrorCode.CONFLICT, status=status.value)
