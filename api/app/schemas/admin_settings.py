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


class MoneyOut(ApiModel):
    """A1. Where the money is, and whose it is."""

    taken_centimes: int
    #: Between a client and a tradesman, never on the platform's books: there
    #: is no escrow before phase 3.
    in_dispute_centimes: int
    #: What the platform charged on those same jobs, and could be told to
    #: refund. This is its own exposure; the line above is not.
    disputed_lead_fees_centimes: int
    topups_waiting: int
    topups_waiting_centimes: int
    credit_held_centimes: int
    credit_owed_centimes: int


class MonthOut(ApiModel):
    """One month of the trend. `2026-08`."""

    month: str
    leads: int
    value_centimes: int
    jobs: int


class PlaceOut(ApiModel):
    """A city or a trade. Names travel in all three languages — an admin adds
    them at runtime (A6), so they cannot be translation keys."""

    id: int
    slug: str
    name_ar: str
    name_fr: str
    name_en: str
    jobs: int
    open_requests: int
    providers: int
    value_centimes: int


class FunnelOut(ApiModel):
    """Published -> answered -> hired -> confirmed. Each step is a subset."""

    requests: int
    with_offer: int
    hired: int
    confirmed: int


class PlatformStatsOut(ApiModel):
    """A1. Every figure counted at read time, never a stored total."""

    new_users_this_week: int
    new_users_last_week: int
    providers_awaiting_approval: int
    open_requests: int
    jobs_done: int
    leads_sold: int
    #: What the platform actually took. The one figure it lives on.
    leads_value_centimes: int
    disputes_open: int

    money: MoneyOut
    #: Oldest first, gaps included: a quiet month is a fact, not a missing row.
    months: list[MonthOut]
    cities: list[PlaceOut]
    trades: list[PlaceOut]
    funnel: FunnelOut
