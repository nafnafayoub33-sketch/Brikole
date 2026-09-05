"""C6 — the client's inbox.

Written the way `audit.record` is written: the row goes in the same session as
the event that caused it, and the caller's own `commit()` is what makes both
true at once. A notification that can outlive a rolled-back offer is a lie the
client acts on.

**The API never ships a sentence.** `payload` carries ids and numbers, and the
web app interpolates them into its own translated string — the same reason
`ErrorCode` exists. A notification stored as "Karim a envoyé une offre" is a
notification that stays French when the person switches to Arabic.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.enums import NotificationKind
from app.core.errors import DomainError, ErrorCode
from app.models.base import utcnow
from app.models.system import Notification
from app.models.user import User


def notify(
    db: Session, *, user_id: int, kind: NotificationKind, **payload: Any
) -> Notification:
    """Queue one notification. The caller commits it with its own change."""
    row = Notification(
        user_id=user_id, kind=kind, payload=payload, created_at=utcnow()
    )
    db.add(row)
    return row


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def page(
        self, user: User, *, page: int, per_page: int
    ) -> tuple[list[Notification], int]:
        base = select(Notification).where(Notification.user_id == user.id)
        total = int(
            self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        )

        rows = list(
            self.db.execute(
                base
                # Newest first, with the id breaking ties so pages never
                # overlap when several land in the same second — which they do,
                # because several of them are written in one transaction.
                .order_by(Notification.created_at.desc(), Notification.id.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            .scalars()
            .all()
        )
        return rows, total

    def unread(self, user: User) -> int:
        return int(
            self.db.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.user_id == user.id, Notification.read_at.is_(None)
                )
            ).scalar_one()
        )

    def mark_read(self, user: User, notification_id: int) -> Notification:
        row = self.db.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user.id
            )
        ).scalar_one_or_none()

        if row is None:
            # Somebody else's notification id is a 404, not a 403: the id space
            # is guessable, and a 403 would confirm the row exists.
            raise DomainError(ErrorCode.NOT_FOUND)

        # Already read stays read at the time it was first read. Re-stamping it
        # would move a thing that already happened.
        if row.read_at is None:
            row.read_at = utcnow()
            self.db.commit()
            self.db.refresh(row)
        return row

    def mark_all_read(self, user: User) -> None:
        """One statement, not a loop: a client who has ignored the bell for a
        month is clearing a hundred rows, and a hundred round trips to do it."""
        self.db.execute(
            update(Notification)
            .where(Notification.user_id == user.id, Notification.read_at.is_(None))
            .values(read_at=utcnow())
        )
        self.db.commit()
