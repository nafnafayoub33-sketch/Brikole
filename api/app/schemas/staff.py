"""A3 — accounts, as an admin sees and changes them."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import DisputeStatus, ProviderStatus, Role, UserStatus
from app.core.staff import MAX_SUSPENSION_DAYS, REASON_MAX
from app.schemas.catalog import CityOut
from app.schemas.common import ApiModel


class UserRowOut(ApiModel):
    """One line of the list. Enough to decide who to open, and nothing more."""

    id: int
    phone: str
    full_name: str
    role: Role
    status: UserStatus
    avatar_url: str | None = None
    city: CityOut | None = None
    created_at: datetime
    last_login_at: datetime | None = None
    suspended_until: datetime | None = None
    #: Set when this account also has a tradesman profile, so the row can say
    #: so without the client fetching a second endpoint.
    provider_status: ProviderStatus | None = None


class UserProviderOut(ApiModel):
    id: int
    status: ProviderStatus
    headline: str | None = None
    rating_avg: float
    rating_count: int
    jobs_done: int
    balance_centimes: int
    free_leads_left: int


class UserActivityOut(BaseModel):
    requests_posted: int
    jobs_hired: int
    spent_centimes: int
    reviews_written: int
    offers_sent: int
    jobs_worked: int
    disputes_opened: int
    disputes_against: int
    staff_actions: int


class UserDisputeOut(BaseModel):
    id: int
    job_id: int
    status: DisputeStatus
    reason: str
    created_at: datetime
    #: True when this user is the one who opened it.
    opened_by_them: bool


class UserDetailOut(UserRowOut):
    """The account, what it has done, and every argument it is in."""

    language: str
    suspension_reason: str | None = None
    locked_until: datetime | None = None
    provider: UserProviderOut | None = None
    activity: UserActivityOut
    disputes: list[UserDisputeOut]


class SuspendIn(BaseModel):
    """`days` null asks for a permanent suspension, which only an admin has."""

    days: int | None = Field(default=None, ge=1, le=MAX_SUSPENSION_DAYS)
    reason: str = Field(min_length=1, max_length=REASON_MAX)


class RoleIn(BaseModel):
    role: Role


class NewStaffIn(BaseModel):
    phone: str
    full_name: str = Field(min_length=1, max_length=120)
    password: str
    role: Role
    language: str = Field(default="ar", pattern="^(ar|fr|en)$")
