"""Every query about users. Nothing else writes SQL against them."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.account import LIVE_DISPUTES, LIVE_JOBS
from app.core.enums import JobStatus, Role, UserStatus
from app.models.dispute import Dispute
from app.models.job import Job, Review
from app.models.offer import Offer
from app.models.request import ServiceRequest
from app.models.system import AuditLog
from app.models.user import User

#: Anything this module counts rows of.
Counted = ServiceRequest | Job | Review | Offer | Dispute | AuditLog


@dataclass(frozen=True, slots=True)
class UserActivity:
    """A3. What one account has done, both sides of the marketplace."""

    requests_posted: int
    jobs_hired: int
    spent_centimes: int
    reviews_written: int
    offers_sent: int
    jobs_worked: int
    disputes_opened: int
    disputes_against: int
    #: Rows this person wrote into the audit log. Zero for everyone but staff.
    staff_actions: int


@dataclass(frozen=True, slots=True)
class Commitments:
    """C7. What somebody else is still relying on this account for.

    Counted across both sides at once, because a client and a tradesman are the
    same row: the man closing his account may be halfway through a job he is
    doing *and* one he is paying for.
    """

    live_jobs: int
    live_disputes: int


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.provider_profile))
            .where(User.id == user_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_phone(self, phone: str) -> User | None:
        """`phone` must already be E.164 — callers normalise at the edge."""
        stmt = (
            select(User)
            .options(selectinload(User.provider_profile))
            .where(User.phone == phone)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def phone_exists(self, phone: str) -> bool:
        stmt = select(User.id).where(User.phone == phone).limit(1)
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def add(
        self,
        *,
        phone: str,
        password_hash: str,
        full_name: str,
        role: Role,
        language: str = "ar",
        status: UserStatus = UserStatus.ACTIVE,
        city_id: int | None = None,
    ) -> User:
        user = User(
            phone=phone,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            language=language,
            status=status,
            city_id=city_id,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def record_failed_login(self, user: User, *, locked_until: datetime | None) -> None:
        user.failed_login_attempts += 1
        if locked_until is not None:
            user.locked_until = locked_until
            # The lock has been applied; the next attempt starts a fresh count.
            user.failed_login_attempts = 0

    def record_successful_login(self, user: User, *, now: datetime) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now

    # -- A3: the admin's view of everyone --------------------------------

    def page(
        self,
        *,
        query: str | None = None,
        role: Role | None = None,
        status: UserStatus | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> tuple[list[User], int]:
        """Search by name or phone, narrowed by role and status.

        Deleted accounts stay out unless they are asked for by name: the list
        is a working queue, not an archive.
        """
        stmt = select(User).options(selectinload(User.provider_profile))

        if query:
            stmt = stmt.where(_matches(query))
        if role is not None:
            stmt = stmt.where(User.role == role)
        if status is not None:
            stmt = stmt.where(User.status == status)
        else:
            stmt = stmt.where(User.status != UserStatus.DELETED)

        total = int(
            self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        )

        rows = list(
            self.db.execute(
                stmt.order_by(User.created_at.desc(), User.id.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            .scalars()
            .all()
        )
        return rows, total

    def staff(self) -> list[User]:
        """Every moderator and admin, including suspended ones.

        A9 is where a suspension is undone, so it is the one list that cannot
        filter them out. Deleted accounts stay out: they are gone, not off.
        """
        return list(
            self.db.execute(
                select(User)
                .where(
                    User.role.in_([Role.MODERATOR, Role.ADMIN]),
                    User.status != UserStatus.DELETED,
                )
                .order_by(User.role, User.full_name, User.id)
            )
            .scalars()
            .all()
        )

    def count_other_active_admins(self, user_id: int) -> int:
        """How many admins would still be able to sign in without this one."""
        return int(
            self.db.execute(
                select(func.count())
                .select_from(User)
                .where(
                    User.id != user_id,
                    User.role == Role.ADMIN,
                    User.status == UserStatus.ACTIVE,
                )
            ).scalar_one()
        )

    def activity(self, user: User) -> UserActivity:
        """What this account has actually done, counted at read time.

        A client and a tradesman are the same row in `users`, so both sides are
        counted for everyone: the ones that do not apply come back zero, and a
        zero is a fact the screen can show rather than a field it has to guess
        whether to render.
        """
        profile_id = user.provider_profile.id if user.provider_profile else None

        return UserActivity(
            requests_posted=self._count(
                ServiceRequest, ServiceRequest.client_id == user.id
            ),
            jobs_hired=self._count(Job, Job.client_id == user.id),
            spent_centimes=int(
                self.db.execute(
                    select(func.coalesce(func.sum(Job.agreed_price_centimes), 0)).where(
                        Job.client_id == user.id, Job.status == JobStatus.CONFIRMED
                    )
                ).scalar_one()
            ),
            reviews_written=self._count(Review, Review.author_id == user.id),
            offers_sent=(
                self._count(Offer, Offer.provider_id == profile_id) if profile_id else 0
            ),
            jobs_worked=(
                self._count(Job, Job.provider_id == profile_id) if profile_id else 0
            ),
            disputes_opened=self._count(Dispute, Dispute.opened_by_id == user.id),
            disputes_against=self._count(Dispute, Dispute.against_id == user.id),
            staff_actions=self._count(AuditLog, AuditLog.actor_id == user.id),
        )

    def commitments(self, user: User) -> Commitments:
        """What is unfinished, either side of this account.

        `LIVE_JOBS` and `LIVE_DISPUTES` are in `core.account` beside the rule
        that reads them, so "what counts as unfinished" is defined once and the
        screen and the refusal cannot drift apart.
        """
        profile_id = user.provider_profile.id if user.provider_profile else None

        sides: list[ColumnElement[bool]] = [Job.client_id == user.id]
        if profile_id is not None:
            sides.append(Job.provider_id == profile_id)

        return Commitments(
            live_jobs=self._count(Job, and_(Job.status.in_(LIVE_JOBS), or_(*sides))),
            live_disputes=self._count(
                Dispute,
                and_(
                    Dispute.status.in_(LIVE_DISPUTES),
                    or_(
                        Dispute.opened_by_id == user.id,
                        Dispute.against_id == user.id,
                    ),
                ),
            ),
        )

    def disputes(self, user: User, *, limit: int = 20) -> list[Dispute]:
        """Both sides of every argument this person is in, newest first."""
        return list(
            self.db.execute(
                select(Dispute)
                .where(
                    or_(Dispute.opened_by_id == user.id, Dispute.against_id == user.id)
                )
                .order_by(Dispute.created_at.desc(), Dispute.id.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def _count(self, model: type[Counted], condition: ColumnElement[bool]) -> int:
        return int(
            self.db.execute(
                select(func.count()).select_from(model).where(condition)
            ).scalar_one()
        )


def _matches(query: str) -> ColumnElement[bool]:
    """A name or a phone, from one box.

    Phones are stored E.164 and typed nationally, so `0612…` has to find
    `+212612…`: the leading zero becomes the country code before matching.
    `%` and `_` are escaped so a stray underscore is not quietly a wildcard.
    """
    needle = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{needle}%"

    clauses = [
        User.full_name.like(pattern, escape="\\"),
        User.phone.like(pattern, escape="\\"),
    ]

    digits = needle.lstrip("+")
    if digits.startswith("0") and digits[1:].isdigit():
        clauses.append(User.phone.like(f"%+212{digits[1:]}%", escape="\\"))

    return or_(*clauses)
