"""Job requests, as a client posts and reads them."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import RequestStatus, Urgency
from app.core.policy import MAX_REQUEST_PHOTOS
from app.core.service_request import (
    MAX_ADDRESS,
    MAX_DESCRIPTION,
    MAX_TITLE,
    MIN_DESCRIPTION,
    MIN_TITLE,
)
from app.schemas.catalog import TradeOut
from app.schemas.common import ApiModel
from app.schemas.provider import ProviderCityOut


class NewRequestIn(BaseModel):
    """What C1 posts. The bounds mirror `app.core.service_request`, which is
    where the decision about what counts as complete actually lives."""

    trade_id: int = Field(gt=0)
    city_id: int = Field(gt=0)

    title: str = Field(min_length=MIN_TITLE, max_length=MAX_TITLE)
    description: str = Field(min_length=MIN_DESCRIPTION, max_length=MAX_DESCRIPTION)
    address: str = Field(min_length=1, max_length=MAX_ADDRESS)

    latitude: float | None = None
    longitude: float | None = None

    urgency: Urgency = Urgency.FLEXIBLE
    budget_min_centimes: int | None = None
    budget_max_centimes: int | None = None

    #: Paths from `POST /uploads`, not URLs.
    photo_paths: list[str] = Field(default_factory=list, max_length=MAX_REQUEST_PHOTOS)


class RequestPhotoOut(ApiModel):
    id: int
    url: str


class RequestOut(ApiModel):
    id: int
    title: str
    description: str
    address: str
    latitude: float | None
    longitude: float | None

    trade: TradeOut
    city: ProviderCityOut

    urgency: Urgency
    status: RequestStatus
    budget_min_centimes: int | None
    budget_max_centimes: int | None

    #: How many tradesmen have answered. The loudest number on C2.
    offers_count: int

    photos: list[RequestPhotoOut]

    created_at: datetime
    expires_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None


class CancelRequestIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
