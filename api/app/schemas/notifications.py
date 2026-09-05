"""C6 — the client's inbox."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.enums import NotificationKind
from app.schemas.common import ApiModel


class NotificationOut(ApiModel):
    """A thing that happened, not a sentence about it.

    `kind` picks the wording and `payload` fills its blanks, both on the web
    side — so one row reads correctly in Arabic, French and English, and a
    person switching language does not find last week's notifications stuck in
    the old one. It is also what the web turns into a link: `payload` carries
    the id of the request, job or dispute the notification is about.
    """

    id: int
    kind: NotificationKind
    payload: dict[str, Any]
    created_at: datetime
    read_at: datetime | None


class UnreadOut(ApiModel):
    count: int
