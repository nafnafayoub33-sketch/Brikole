"""A3 — an admin acting on somebody else's account.

Every method here changes another user's state, so every method here writes an
audit row in the same transaction as the change. That is not a convention this
file is trying to remember: the change and the row are always in the same
block, and the commit is at the end of both.

The refusals live in `core/staff.py`, framework-free and unit-tested without a
database. This layer's job is to fetch, to ask, and to record.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core import staff as rules
from app.core.enums import Role, UserStatus
from app.core.errors import DomainError, ErrorCode
from app.core.permissions import Permission, has_permission
from app.core.phone import normalise_phone
from app.core.security import hash_password, validate_password
from app.core.staff_work import Work, summarise
from app.core.temp_password import generate as generate_password
from app.models.base import utcnow
from app.models.dispute import Dispute
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.repositories.users import UserActivity, UserRepository
from app.services import audit
from app.services.audit import AuditAction


class StaffService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    # -- reading ---------------------------------------------------------

    def page(
        self,
        *,
        query: str | None,
        role: Role | None,
        status: UserStatus | None,
        page: int,
        per_page: int,
    ) -> tuple[list[User], int]:
        return self.users.page(
            query=query, role=role, status=status, page=page, per_page=per_page
        )

    def get(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if user is None or user.status is UserStatus.DELETED:
            raise DomainError(ErrorCode.NOT_FOUND)
        return user

    def activity(self, user: User) -> UserActivity:
        return self.users.activity(user)

    def roster(self) -> list[tuple[User, Work, datetime | None]]:
        """A9 — every moderator and admin, with what each of them has handled.

        The counts come out of the audit log rather than a column somebody has
        to remember to increment, so they are right by construction: a staff
        action that is not logged is a bug the whole product already has.
        """
        audit_log = AuditRepository(self.db)
        counts = audit_log.work_by_actor()
        last = audit_log.last_action_at()

        return [
            (person, summarise(counts.get(person.id, {})), last.get(person.id))
            for person in self.users.staff()
        ]

    def disputes(self, user: User) -> list[Dispute]:
        return self.users.disputes(user)

    # -- acting ----------------------------------------------------------

    def suspend(
        self,
        actor: User,
        user_id: int,
        *,
        days: int | None,
        reason: str,
        ip: str | None = None,
    ) -> User:
        target = self.get(user_id)
        rules.assert_not_self(actor.id, target.id)
        rules.assert_not_last_admin(
            target_role=target.role,
            target_status=target.status,
            other_active_admins=self.users.count_other_active_admins(target.id),
        )

        suspension = rules.build_suspension(
            days=days,
            reason=reason,
            now=utcnow(),
            may_suspend_permanently=has_permission(
                actor.role, Permission.SUSPEND_PERMANENT
            ),
        )

        before = _snapshot(target)
        target.status = UserStatus.SUSPENDED
        target.suspended_until = suspension.until
        target.suspension_reason = suspension.reason

        audit.record(
            self.db,
            actor=actor,
            action=AuditAction.USER_SUSPENDED,
            target_type="user",
            target_id=target.id,
            before=before,
            after=_snapshot(target),
            note=suspension.reason,
            ip=ip,
        )

        self.db.commit()
        self.db.refresh(target)
        return target

    def reactivate(self, actor: User, user_id: int, *, ip: str | None = None) -> User:
        target = self.get(user_id)
        rules.assert_not_self(actor.id, target.id)
        rules.assert_suspended(target.status)

        before = _snapshot(target)
        target.status = UserStatus.ACTIVE
        target.suspended_until = None
        target.suspension_reason = None
        # A suspension somebody just lifted should not be followed by a lockout
        # from failed attempts made while the account was shut.
        target.failed_login_attempts = 0
        target.locked_until = None

        audit.record(
            self.db,
            actor=actor,
            action=AuditAction.USER_REACTIVATED,
            target_type="user",
            target_id=target.id,
            before=before,
            after=_snapshot(target),
            ip=ip,
        )

        self.db.commit()
        self.db.refresh(target)
        return target

    def change_role(
        self, actor: User, user_id: int, *, role: Role, ip: str | None = None
    ) -> User:
        target = self.get(user_id)
        rules.assert_not_self(actor.id, target.id)

        new_role = rules.validate_role_change(
            current=target.role,
            new=role,
            has_provider_profile=target.provider_profile is not None,
        )
        # Demoting the last admin locks the platform exactly as suspending him
        # would, so it is the same guard.
        rules.assert_not_last_admin(
            target_role=target.role,
            target_status=target.status,
            other_active_admins=self.users.count_other_active_admins(target.id),
        )

        before = _snapshot(target)
        target.role = new_role

        audit.record(
            self.db,
            actor=actor,
            action=AuditAction.USER_ROLE_CHANGED,
            target_type="user",
            target_id=target.id,
            before=before,
            after=_snapshot(target),
            ip=ip,
        )

        self.db.commit()
        self.db.refresh(target)
        return target

    def reset_password(
        self, actor: User, user_id: int, *, ip: str | None = None
    ) -> str:
        """P6 — the reset the forgot-password screen promises.

        Returns the new password in plaintext, once. It is never stored in
        anything but its argon2 hash and never written to the audit log: the
        row records that a reset happened and who did it, which is the part
        that has to survive.

        The lockout goes with it. Somebody who has forgotten his password has
        almost always just proved it five times, so he is locked out for
        fifteen minutes — and a new password that still answers "too many
        attempts" is a second phone call.

        What this cannot do is end a session already open elsewhere: the tokens
        are signed, not stored, so nothing exists to revoke. A stolen account
        needs `suspend`, and that is what it is for.
        """
        target = self.get(user_id)
        rules.assert_not_self(actor.id, target.id)
        rules.assert_can_sign_in(target.status)

        password = generate_password()

        before = _lock(target)
        target.password_hash = hash_password(password)
        target.failed_login_attempts = 0
        target.locked_until = None

        audit.record(
            self.db,
            actor=actor,
            action=AuditAction.PASSWORD_RESET,
            target_type="user",
            target_id=target.id,
            before=before,
            after=_lock(target),
            ip=ip,
        )

        self.db.commit()
        return password

    def create_staff(
        self,
        actor: User,
        *,
        phone: str,
        full_name: str,
        password: str,
        role: Role,
        language: str = "ar",
        ip: str | None = None,
    ) -> User:
        """A moderator or an admin. Everything else registers itself."""
        wanted = rules.validate_new_staff_role(role)
        e164 = normalise_phone(phone)
        validate_password(password)

        if self.users.phone_exists(e164):
            raise DomainError(ErrorCode.PHONE_TAKEN)

        name = full_name.strip()
        if not name:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="full_name")

        created = self.users.add(
            phone=e164,
            password_hash=hash_password(password),
            full_name=name,
            role=wanted,
            language=language,
        )

        audit.record(
            self.db,
            actor=actor,
            action=AuditAction.STAFF_CREATED,
            target_type="user",
            target_id=created.id,
            after={"role": wanted.value, "phone": e164},
            ip=ip,
        )

        self.db.commit()
        self.db.refresh(created)
        return created


def _lock(user: User) -> dict[str, str | int | None]:
    """The lockout, before and after. The hash is not in here and must not be:
    an audit log holding password material is a second copy of the thing the
    hashing was for."""
    return {
        "failed_login_attempts": user.failed_login_attempts,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None,
    }


def _snapshot(user: User) -> dict[str, str | None]:
    """The fields that move, not the whole row: a diff nobody can read is a
    diff nobody will read."""
    return {
        "role": user.role.value,
        "status": user.status.value,
        "suspended_until": (
            user.suspended_until.isoformat() if user.suspended_until else None
        ),
    }
