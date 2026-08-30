"""C1, C2 and C3 — a client's own job requests."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.enums import Role
from app.deps import CurrentUser, DbSession, require_roles
from app.models.offer import Offer
from app.models.request import ServiceRequest
from app.schemas.catalog import TradeOut
from app.schemas.common import Page
from app.schemas.offer import OfferOut, OfferProviderOut
from app.schemas.provider import ProviderCityOut
from app.schemas.request import CancelRequestIn, NewRequestIn, RequestOut, RequestPhotoOut
from app.services.requests import RequestService

router = APIRouter(
    prefix="/client/requests",
    tags=["client"],
    dependencies=[Depends(require_roles(Role.CLIENT))],
)


@router.get("", response_model=Page[RequestOut])
def list_requests(
    user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[RequestOut]:
    """C2. Newest first — his own, and nobody else's."""
    rows, total = RequestService(db).list_own(user, page=page, per_page=per_page)
    return Page[RequestOut](
        items=[_out(row) for row in rows], total=total, page=page, per_page=per_page
    )


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(payload: NewRequestIn, user: CurrentUser, db: DbSession) -> RequestOut:
    """C1."""
    return _out(RequestService(db).create(user, payload))


@router.get("/{request_id}", response_model=RequestOut)
def get_request(request_id: int, user: CurrentUser, db: DbSession) -> RequestOut:
    """C3."""
    return _out(RequestService(db).get_own(user, request_id))


@router.get("/{request_id}/offers", response_model=list[OfferOut])
def list_offers(request_id: int, user: CurrentUser, db: DbSession) -> list[OfferOut]:
    """C3. Unsorted beyond newest first — the sorting a client wants (price,
    rating, soonest) is a decision he changes on the page, not a round trip."""
    return [_offer_out(offer) for offer in RequestService(db).list_offers(user, request_id)]


@router.patch("/{request_id}", response_model=RequestOut)
def update_request(
    request_id: int, payload: NewRequestIn, user: CurrentUser, db: DbSession
) -> RequestOut:
    """C3. Allowed only while nobody has priced it — see the service."""
    return _out(RequestService(db).update(user, request_id, payload))


@router.post("/{request_id}/offers/{offer_id}/decline", response_model=OfferOut)
def decline_offer(
    request_id: int, offer_id: int, user: CurrentUser, db: DbSession
) -> OfferOut:
    """C3. Turning one down without choosing another."""
    return _offer_out(RequestService(db).decline_offer(user, request_id, offer_id))


@router.post("/{request_id}/cancel", response_model=RequestOut)
def cancel_request(
    request_id: int, payload: CancelRequestIn, user: CurrentUser, db: DbSession
) -> RequestOut:
    return _out(RequestService(db).cancel(user, request_id, reason=payload.reason))


def _out(request: ServiceRequest) -> RequestOut:
    return RequestOut(
        id=request.id,
        title=request.title,
        description=request.description,
        address=request.address,
        latitude=request.latitude,
        longitude=request.longitude,
        trade=TradeOut.model_validate(request.trade),
        city=ProviderCityOut.model_validate(request.city),
        urgency=request.urgency,
        status=request.status,
        budget_min_centimes=request.budget_min_centimes,
        budget_max_centimes=request.budget_max_centimes,
        offers_count=request.offers_count,
        photos=[RequestPhotoOut.model_validate(photo) for photo in request.photos],
        created_at=request.created_at,
        expires_at=request.expires_at,
        cancelled_at=request.cancelled_at,
        cancel_reason=request.cancel_reason,
    )


def _offer_out(offer: Offer) -> OfferOut:
    provider = offer.provider
    return OfferOut(
        id=offer.id,
        price_centimes=offer.price_centimes,
        message=offer.message,
        available_from=offer.available_from,
        status=offer.status,
        created_at=offer.created_at,
        provider=OfferProviderOut(
            id=provider.id,
            full_name=provider.user.full_name,
            avatar_url=provider.user.avatar_url,
            headline=provider.headline,
            city=ProviderCityOut.model_validate(provider.city),
            rating_avg=provider.rating_avg,
            rating_count=provider.rating_count,
            jobs_done=provider.jobs_done,
            years_experience=provider.years_experience,
        ),
    )
