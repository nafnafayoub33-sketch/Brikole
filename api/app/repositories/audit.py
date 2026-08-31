"""Reading the audit log. Nothing here writes or deletes — see `services/audit`."""

from __future__ import annotations

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
