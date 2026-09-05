"""Reading the audit log. Nothing here writes or deletes — see `services/audit`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.system import AuditLog
from app.models.user import User


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def page(
        self,
        *,
        actor_id: int | None = None,
        action: str | None = None,
        target_type: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[tuple[AuditLog, User | None]], int]:
        stmt = select(AuditLog)
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if target_type:
            stmt = stmt.where(AuditLog.target_type == target_type)

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        rows = self.db.execute(
            stmt.add_columns(User)
            # Outer join: a deleted actor must not take his own record with him.
            .join(User, User.id == AuditLog.actor_id, isouter=True)
            # Newest first — an audit log is read from the top when something
            # has just happened.
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()

        return [(entry, actor) for entry, actor in rows], total

    def work_by_actor(self) -> dict[int, dict[str, int]]:
        """Every staff action ever taken, counted per person and per action.

        One grouped query for the whole roster rather than one per row: A9 is
        a short list, but the log behind it is not, and a query per staff
        member is a screen that gets slower every month it runs.
        """
        rows = self.db.execute(
            select(AuditLog.actor_id, AuditLog.action, func.count())
            .where(AuditLog.actor_id.is_not(None))
            .group_by(AuditLog.actor_id, AuditLog.action)
        ).all()

        counts: dict[int, dict[str, int]] = {}
        for actor_id, action, count in rows:
            if actor_id is not None:
                counts.setdefault(actor_id, {})[action] = count
        return counts

    def last_action_at(self) -> dict[int, datetime]:
        """When each person last did anything.

        The one number that answers "is this moderator still working here",
        which `last_login_at` does not: signing in and doing nothing is the
        case worth telling apart.
        """
        rows = self.db.execute(
            select(AuditLog.actor_id, func.max(AuditLog.created_at))
            .where(AuditLog.actor_id.is_not(None))
            .group_by(AuditLog.actor_id)
        ).all()
        return {actor_id: when for actor_id, when in rows if actor_id is not None}

    def distinct_actions(self) -> list[str]:
        return [
            str(value)
            for value in self.db.execute(
                select(AuditLog.action).distinct().order_by(AuditLog.action)
            ).scalars()
        ]

    def distinct_target_types(self) -> list[str]:
        return [
            str(value)
            for value in self.db.execute(
                select(AuditLog.target_type).distinct().order_by(AuditLog.target_type)
            ).scalars()
        ]
