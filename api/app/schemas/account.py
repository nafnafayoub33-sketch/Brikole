"""C7, M11 and D4 — a person's own account."""

from __future__ import annotations

from pydantic import Field

from app.core.account import LANGUAGES, MAX_NAME, MIN_NAME
from app.schemas.common import ApiModel

_LANGUAGE_PATTERN = f"^({'|'.join(LANGUAGES)})$"


class AccountEditIn(ApiModel):
    """Everything a person may change about himself.

    There is no `phone`. Not "phone, ignored" — absent, so nobody has to
    remember to drop it: the number is the identity, and an endpoint that
    accepts one is an endpoint that can take over an account.
    """

    full_name: str = Field(min_length=MIN_NAME, max_length=MAX_NAME)
    #: Optional for a client, who may not have said where he is.
    city_id: int | None = None
    language: str = Field(pattern=_LANGUAGE_PATTERN)
    #: A fresh upload's storage path. Absent leaves the current photo alone —
    #: an edit that forgets to re-send it must not wipe it.
    avatar_path: str | None = Field(default=None, max_length=300)


class CommitmentsOut(ApiModel):
    """What is holding the account open, so the screen can say so before the
    button rather than after the error."""

    live_jobs: int
    live_disputes: int

    #: Filled from `core.account.can_delete`, the same predicate the refusal
    #: uses, so the button and the 409 cannot disagree.
    can_delete: bool
