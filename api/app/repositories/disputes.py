"""The dispute queue, and the history a moderator judges against."""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import DisputeStatus, DisputeVerdict, Role
from app.models.dispute import Dispute
from app.models.job import Job
from app.models.provider import ProviderProfile
from app.models.user import User


class DisputeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, dispute_id: int) -> Dispute | None:
        return self.db.execute(
            select(Dispute)
            .where(Dispute.id == dispute_id)
            .options(selectinload(Dispute.messages))
        ).scalar_one_or_none()

    def for_job(self, job_id: int) -> Dispute | None:
        """One live dispute per job. A second is the same argument twice."""
        return self.db.execute(
            select(Dispute)
            .where(Dispute.job_id == job_id, Dispute.status != DisputeStatus.RESOLVED)
            .order_by(Dispute.id.desc())
        ).scalars().first()

    def queue(
        self, condition: ColumnElement[bool], *, page: int = 1, per_page: int = 20
    ) -> tuple[list[Dispute], int]:
        base = select(Dispute).where(condition)
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        rows = list(
            self.db.execute(
                # Oldest first: it is a queue, and two people are waiting on it.
                base.order_by(Dispute.created_at.asc(), Dispute.id.asc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            ).scalars()
        )
        return rows, total

    def mine(self, user_id: int, *, page: int = 1, per_page: int = 20) -> tuple[list[Dispute], int]:
        base = select(Dispute).where(
            (Dispute.opened_by_id == user_id) | (Dispute.against_id == user_id)
        )
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        rows = list(
            self.db.execute(
                base.order_by(Dispute.created_at.desc(), Dispute.id.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            ).scalars()
        )
        return rows, total

    def job_for(self, dispute: Dispute) -> Job:
        return self.db.execute(select(Job).where(Job.id == dispute.job_id)).scalar_one()

    def profile_for_user(self, user_id: int) -> ProviderProfile | None:
        return self.db.execute(
            select(ProviderProfile).where(ProviderProfile.user_id == user_id)
        ).scalar_one_or_none()

    def disputes_lost(self, user_id: int, role: Role) -> int:
        """How often this person has already been found at fault.

        The number a moderator actually wants beside a name: one complaint is
        noise, a pattern is a decision.
        """
        blamed = (
            DisputeVerdict.CLIENT_AT_FAULT
            if role is Role.CLIENT
            else DisputeVerdict.PROVIDER_AT_FAULT
        )
        return self.db.execute(
            select(func.count())
            .select_from(Dispute)
            .where(
                Dispute.status == DisputeStatus.RESOLVED,
                Dispute.verdict == blamed,
                (Dispute.opened_by_id == user_id) | (Dispute.against_id == user_id),
            )
        ).scalar_one()

    def user(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)
