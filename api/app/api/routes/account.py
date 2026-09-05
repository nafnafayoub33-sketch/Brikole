"""C7, M11 and D4 — a person's own account.

One set of endpoints for all three, because the row being edited is the same
whatever the role. `/auth` stays about sessions and credentials; this is about
the person.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.account import can_delete
from app.deps import REFRESH_COOKIE, REFRESH_COOKIE_PATH, CurrentUser, DbSession
from app.schemas.account import AccountEditIn, CommitmentsOut
from app.schemas.auth import MeOut
from app.services.account import AccountService
from app.services.auth import me_payload

router = APIRouter(prefix="/account", tags=["account"])


@router.patch("", response_model=MeOut)
def edit(payload: AccountEditIn, user: CurrentUser, db: DbSession) -> MeOut:
    """Returns the same shape as `/auth/me`, so the web app can drop it
    straight into the session it already holds instead of refetching."""
    return me_payload(AccountService(db).edit(user, payload))


@router.get("/commitments", response_model=CommitmentsOut)
def commitments(user: CurrentUser, db: DbSession) -> CommitmentsOut:
    """What is still hanging off this account. The screen asks before it offers
    to close it, so a man with a job in progress reads why rather than pressing
    and getting a 409."""
    open_items = AccountService(db).commitments(user)
    return CommitmentsOut(
        live_jobs=open_items.live_jobs,
        live_disputes=open_items.live_disputes,
        can_delete=can_delete(
            live_jobs=open_items.live_jobs, live_disputes=open_items.live_disputes
        ),
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete(user: CurrentUser, db: DbSession, response: Response) -> None:
    AccountService(db).delete(user)
    # He is gone: the refresh cookie goes with him, or the browser keeps
    # quietly trying to renew a session the API will refuse.
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
