"""A7 and A8 — the platform's dials, and the record of who turned them."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ApiModel


class SettingOut(ApiModel):
    key: str
    value: Any
    #: Null while nobody has ever changed it: the value is the shipped default,
    #: and A7 says so rather than implying somebody chose it.
    updated_at: datetime | None
    updated_by_name: str | None


class SettingsOut(ApiModel):
    items: list[SettingOut]


class UpdateSettingsIn(BaseModel):
    """A partial write. Only the keys sent are touched, so two admins editing
    different halves of the screen do not overwrite each other."""

    values: dict[str, Any] = Field(min_length=1)


class AuditEntryOut(ApiModel):
    id: int
    action: str
    target_type: str
    target_id: int | None
    #: Null when the actor's account has since been deleted. The row survives —
    #: that is the point of an audit log.
    actor_id: int | None
    actor_name: str | None
    before: Any | None
    after: Any | None
    note: str | None
    ip: str | None
    created_at: datetime


class AuditFiltersOut(ApiModel):
    """The values actually present in the log, so A8's filters offer only what
    would return something."""

    actions: list[str]
    target_types: list[str]


class PlatformStatsOut(ApiModel):
    """A1. Seven numbers, each linking to the screen it came from."""

    new_users_this_week: int
    new_users_last_week: int
    providers_awaiting_approval: int
    open_requests: int
    jobs_done: int
    leads_sold: int
    #: What the platform actually took. The one figure it lives on.
    leads_value_centimes: int
    disputes_open: int
