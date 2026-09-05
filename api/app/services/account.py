"""C7, M11 and D4 — a person's own account.

One service for three screens, because a client, a tradesman and a moderator
edit exactly the same row. What differs between them is what the *rest* of the
screen shows, and that is the web app's problem, not this one's.

The refusals live in `core/account.py`, framework-free. This layer fetches the
counts they need and writes the change.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import account as rules
from app.core.enums import UserStatus
from app.core.errors import DomainError, ErrorCode
from app.models.catalog import City
from app.models.user import User
from app.repositories.users import Commitments, UserRepository
from app.schemas.account import AccountEditIn


class AccountService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def commitments(self, user: User) -> Commitments:
        """What would be left dangling if this account closed right now.

        The screen asks before it offers the button, so somebody with a job in
        progress reads *why* instead of pressing and getting a 409.
        """
        return self.users.commitments(user)

    def edit(self, user: User, payload: AccountEditIn) -> User:
        """Name, city, language, photo. Never the phone.

        The phone is the identity — it signs him in, it is what an admin asks
        for on the P6 call, and it is what the platform means by "this person".
        There is no field for it here, so there is nothing to guard.
        """
        user.full_name = rules.validate_name(payload.full_name)
        user.language = rules.validate_language(payload.language)

        if payload.city_id is None:
            user.city_id = None
        else:
            city = self.db.get(City, payload.city_id)
            if city is None or not city.is_active:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="city_id")
            user.city_id = city.id

        if payload.avatar_path:
            user.avatar_url = f"/api/v1/uploads/{payload.avatar_path}"

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        """Close the account, once nobody else is waiting on it.

        `DELETED` rather than a row removed: every job, review, offer and audit
        row points here, and deleting the row would either cascade through the
        history of people who did nothing wrong or leave it pointing at
        nothing. `AuthService.user_from_token` already refuses a deleted
        account, so every token he holds stops working on its next request, and
        `_reachable` drops a tradesman out of search on the same status.

        His phone number stays on the closed row, so registering again with it
        is refused — coming back is a conversation with an admin. The second
        confirmation on the screen says so before he presses.
        """
        commitments = self.commitments(user)
        rules.assert_can_delete(
            live_jobs=commitments.live_jobs,
            live_disputes=commitments.live_disputes,
        )

        user.status = UserStatus.DELETED
        self.db.commit()
