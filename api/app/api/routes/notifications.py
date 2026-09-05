"""C6 — the client's inbox.

Not gated to a role. The rows are per-user and a client is the only one with a
screen for them today, but the endpoints answer for whoever holds the token:
gating them to `client` would mean the day a tradesman gets his own inbox, the
guard here is a second thing to remember.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.notifications import NotificationOut, UnreadOut
from app.services.notifications import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/unread", response_model=UnreadOut)
def unread(user: CurrentUser, db: DbSession) -> UnreadOut:
    """Declared before `/{id}` so `unread` is never read as an id.

    Its own endpoint because the header asks for it on every screen, and the
    header should not pay for a page of rows to learn one number.
    """
    return UnreadOut(count=NotificationService(db).unread(user))


@router.get("", response_model=Page[NotificationOut])
def page(
    user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[NotificationOut]:
    rows, total = NotificationService(db).page(user, page=page, per_page=per_page)
    return Page[NotificationOut](
        items=[NotificationOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(user: CurrentUser, db: DbSession) -> None:
    NotificationService(db).mark_all_read(user)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: CurrentUser, db: DbSession) -> NotificationOut:
    """Opening the thing it points at is what marks it read — the list itself
    marks nothing, so a glance at the bell does not erase what he has not
    looked at yet."""
    row = NotificationService(db).mark_read(user, notification_id)
    return NotificationOut.model_validate(row)
