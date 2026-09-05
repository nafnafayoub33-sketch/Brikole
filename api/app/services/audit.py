"""The record of what staff did to whom.

`AuditAction` is re-exported here so every existing call site keeps working;
it lives in `core` because A9 groups the actions into kinds of work, and a
rule in `core` must not have to reach into a service to know what they are.

`CLAUDE.md` puts it plainly: every admin or moderator action that changes
another user's state writes a row here, no exceptions. So the write lives next
to the change rather than being remembered at each call site — a helper that is
easier to call than to skip.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.audit_actions import AuditAction
from app.models.base import utcnow
from app.models.system import AuditLog
from app.models.user import User

__all__ = ["AuditAction", "record"]


def record(
    db: Session,
    *,
    actor: User,
    action: str,
    target_type: str,
    target_id: int | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    note: str | None = None,
    ip: str | None = None,
) -> AuditLog:
    """Append one row. `before` and `after` hold the fields that moved, not
    whole rows — a diff nobody can read is a diff nobody will read."""
    entry = AuditLog(
        actor_id=actor.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before=before,
        after=after,
        note=note,
        ip=ip,
        created_at=utcnow(),
    )
    db.add(entry)
    return entry
