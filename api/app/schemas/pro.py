"""The tradesman's own profile, as he fills it in at M1."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.policy import MAX_PORTFOLIO_PHOTOS, MAX_RADIUS_KM
from app.core.provider_application import (
    MAX_BIO,
    MAX_HEADLINE,
    MAX_TRADES,
    MAX_YEARS_EXPERIENCE,
    MIN_TRADES,
)
from app.schemas.provider import ProviderProfileOut


class ProviderApplicationIn(BaseModel):
    """What M1 posts.

    The bounds here are the same ones `app.core.provider_application` enforces.
    Pydantic rejects the obviously wrong shape early; the core module is what
    decides whether an application is *complete*, and it is the one the tests
    are written against.
    """

    trade_ids: list[int] = Field(min_length=MIN_TRADES, max_length=MAX_TRADES)
    city_id: int = Field(gt=0)
    radius_km: int = Field(ge=1, le=MAX_RADIUS_KM)

    headline: str = Field(min_length=1, max_length=MAX_HEADLINE)
    bio: str = Field(max_length=MAX_BIO)
    years_experience: int = Field(ge=0, le=MAX_YEARS_EXPERIENCE)
    starting_price_centimes: int | None = None

    #: Paths from `POST /uploads`, not URLs.
    avatar_path: str | None = None
    id_card_path: str | None = None
    photo_paths: list[str] = Field(default_factory=list, max_length=MAX_PORTFOLIO_PHOTOS)


class MyProviderProfileOut(ProviderProfileOut):
    """His own profile, which he may read at any status — including the
    rejection reason, which is the only way M2 can tell him what to fix."""

    rejection_reason: str | None
    id_card_path: str | None


class ApplicationOut(MyProviderProfileOut):
    """An application as an admin reads it at A2.

    It carries the applicant's phone, which the public profile never does: an
    admin checking an identity has to be able to reach the person.
    """

    phone: str
    submitted_at: datetime


class RejectionIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
