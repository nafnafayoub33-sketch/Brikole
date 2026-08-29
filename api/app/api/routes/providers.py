"""The tradesmen a client browses on the home page and inside a trade."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.errors import DomainError, ErrorCode
from app.deps import DbSession
from app.models.provider import ProviderProfile
from app.repositories.providers import ProviderRepository, ProviderSort
from app.schemas.catalog import TradeOut
from app.schemas.common import Page
from app.schemas.provider import ProviderCardOut, ProviderCityOut

router = APIRouter(tags=["providers"])


@router.get("/providers", response_model=Page[ProviderCardOut])
def list_providers(
    db: DbSession,
    trade_id: Annotated[int | None, Query(description="Only tradesmen in this trade.")] = None,
    city_id: Annotated[int | None, Query(description="Only tradesmen in this city.")] = None,
    sort: Annotated[ProviderSort, Query()] = ProviderSort.RATING,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=48)] = 12,
) -> Page[ProviderCardOut]:
    """The grid. Public, because browsing is what convinces somebody to sign up."""
    rows, total = ProviderRepository(db).list_cards(
        trade_id=trade_id, city_id=city_id, sort=sort, page=page, per_page=per_page
    )
    return Page[ProviderCardOut](
        items=[to_card(row) for row in rows], total=total, page=page, per_page=per_page
    )


@router.get("/providers/{provider_id}", response_model=ProviderCardOut)
def get_provider(provider_id: int, db: DbSession) -> ProviderCardOut:
    row = ProviderRepository(db).get_card(provider_id)
    if row is None:
        # A pending or suspended profile is *not found*, not "forbidden":
        # confirming it exists tells a stranger something about someone else.
        raise DomainError(ErrorCode.NOT_FOUND)
    return to_card(row)


def to_card(profile: ProviderProfile) -> ProviderCardOut:
    return ProviderCardOut(
        id=profile.id,
        full_name=profile.user.full_name,
        avatar_url=profile.user.avatar_url,
        headline=profile.headline,
        status=profile.status,
        city=ProviderCityOut.model_validate(profile.city),
        trades=[TradeOut.model_validate(trade) for trade in profile.trades],
        rating_avg=profile.rating_avg,
        rating_count=profile.rating_count,
        jobs_done=profile.jobs_done,
        years_experience=profile.years_experience,
        starting_price_centimes=profile.starting_price_centimes,
    )
