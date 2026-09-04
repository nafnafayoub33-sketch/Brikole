"""The tradesmen a client browses on the home page and inside a trade."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core import boost as boost_rules
from app.core.errors import DomainError, ErrorCode
from app.deps import DbSession
from app.models.base import utcnow
from app.models.provider import ProviderProfile
from app.repositories.providers import ProviderRepository, ProviderSort
from app.repositories.reviews import ReviewRepository, ReviewRow
from app.schemas.catalog import TradeOut
from app.schemas.common import Page
from app.schemas.provider import (
    ProviderCardOut,
    ProviderCityOut,
    ProviderPhotoOut,
    ProviderProfileOut,
    ReviewAuthorOut,
    ReviewOut,
)

router = APIRouter(tags=["providers"])


@router.get("/providers", response_model=Page[ProviderCardOut])
def list_providers(
    db: DbSession,
    q: Annotated[
        str | None,
        Query(max_length=80, description="Match a name, a headline or a trade."),
    ] = None,
    trade_id: Annotated[int | None, Query(description="Only tradesmen in this trade.")] = None,
    city_id: Annotated[int | None, Query(description="Only tradesmen in this city.")] = None,
    sort: Annotated[ProviderSort, Query()] = ProviderSort.RATING,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=48)] = 12,
) -> Page[ProviderCardOut]:
    """The grid. Public, because browsing is what convinces somebody to sign up."""
    rows, total = ProviderRepository(db).list_cards(
        query=q, trade_id=trade_id, city_id=city_id, sort=sort, page=page, per_page=per_page
    )
    return Page[ProviderCardOut](
        items=[to_card(row) for row in rows], total=total, page=page, per_page=per_page
    )


@router.get("/providers/{provider_id}", response_model=ProviderProfileOut)
def get_provider(provider_id: int, db: DbSession) -> ProviderProfileOut:
    """P3. Everything the grid shows, plus what a decision needs a page for."""
    row = ProviderRepository(db).get_card(provider_id)
    if row is None:
        # A pending or suspended profile is *not found*, not "forbidden":
        # confirming it exists tells a stranger something about someone else.
        raise DomainError(ErrorCode.NOT_FOUND)

    card = to_card(row)
    return ProviderProfileOut(
        **card.model_dump(),
        bio=row.bio,
        radius_km=row.radius_km,
        member_since=row.created_at,
        rating_breakdown=ReviewRepository(db).breakdown(row.id),
        photos=[ProviderPhotoOut.model_validate(photo) for photo in row.photos],
    )


@router.get("/providers/{provider_id}/reviews", response_model=Page[ReviewOut])
def list_provider_reviews(
    provider_id: int,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 10,
) -> Page[ReviewOut]:
    if ProviderRepository(db).get_card(provider_id) is None:
        raise DomainError(ErrorCode.NOT_FOUND)

    rows, total = ReviewRepository(db).list_for_provider(
        provider_id, page=page, per_page=per_page
    )
    return Page[ReviewOut](
        items=[to_review(row) for row in rows], total=total, page=page, per_page=per_page
    )


def to_review(row: ReviewRow) -> ReviewOut:
    return ReviewOut(
        id=row.review.id,
        rating=row.review.rating,
        comment=row.review.comment,
        created_at=row.review.created_at,
        reply=row.review.reply,
        replied_at=row.review.replied_at,
        author=ReviewAuthorOut(
            display_name=display_name(row.author.full_name),
            city=None if row.city is None else ProviderCityOut.model_validate(row.city),
        ),
        trade=None if row.trade is None else TradeOut.model_validate(row.trade),
    )


def display_name(full_name: str) -> str:
    """"Youssef Alami" reads as "Youssef A." beside a public review.

    The review is public; the reviewer's full name does not have to be.
    """
    parts = [part for part in full_name.split() if part]
    if not parts:
        return "—"
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0].upper()}."


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
        is_boosted=boost_rules.is_active(profile.boosted_until, utcnow()),
    )
