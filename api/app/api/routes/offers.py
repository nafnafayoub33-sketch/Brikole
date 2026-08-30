"""M3, M4, M5 and M6 — the tradesman's feed, his offers, his balance."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.enums import Role, Urgency
from app.deps import CurrentUser, DbSession, require_roles
from app.models.offer import Offer
from app.models.request import ServiceRequest
from app.schemas.catalog import TradeOut
from app.schemas.common import Page
from app.schemas.offer import (
    CreditSummaryOut,
    FeedRequestDetailOut,
    FeedRequestOut,
    MyOfferOut,
    NewOfferIn,
)
from app.schemas.provider import ProviderCityOut
from app.schemas.request import RequestPhotoOut
from app.services.offers import OfferService

router = APIRouter(
    prefix="/pro",
    tags=["pro"],
    dependencies=[Depends(require_roles(Role.PROVIDER))],
)

#: How much of the description M4 shows before he opens it.
EXCERPT = 180


@router.get("/credit", response_model=CreditSummaryOut)
def get_credit(user: CurrentUser, db: DbSession) -> CreditSummaryOut:
    """M3's loudest number, and what M4 and M5 gate on."""
    service = OfferService(db)
    profile = service.profile_for(user)
    account = service.credit(profile)

    return CreditSummaryOut(
        balance_centimes=account.balance_centimes,
        free_leads_left=account.free_leads_left,
        default_lead_fee_centimes=service.default_fee(),
        can_take_work=service.can_take_work(profile),
    )


@router.get("/requests", response_model=Page[FeedRequestOut])
def request_feed(
    user: CurrentUser,
    db: DbSession,
    trade_id: Annotated[int | None, Query(gt=0)] = None,
    urgency: Urgency | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[FeedRequestOut]:
    """M4. Answers 402 when he is out of credit — he is not shown work he
    cannot take, and the code is what drives the top-up screen."""
    _, rows, mine, total = OfferService(db).feed(
        user,
        trade_id=trade_id,
        urgency=urgency.value if urgency else None,
        page=page,
        per_page=per_page,
    )
    return Page[FeedRequestOut](
        items=[_row(request, mine.get(request.id)) for request in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/requests/{request_id}", response_model=FeedRequestDetailOut)
def request_detail(request_id: int, user: CurrentUser, db: DbSession) -> FeedRequestDetailOut:
    """M5. Note what is *not* here: the address. It is not his until his offer
    is accepted, and the schema simply has no field for it."""
    service = OfferService(db)
    _, request, mine = service.request_detail(user, request_id)

    return FeedRequestDetailOut(
        **_row(request, mine).model_dump(),
        description=request.description,
        photos=[RequestPhotoOut.model_validate(photo) for photo in request.photos],
        lead_fee_centimes=service.fee_for_request(request),
        my_offer=_mine(mine, request) if mine else None,
    )


@router.post(
    "/requests/{request_id}/offer",
    response_model=MyOfferOut,
    status_code=status.HTTP_201_CREATED,
)
def send_offer(
    request_id: int, payload: NewOfferIn, user: CurrentUser, db: DbSession
) -> MyOfferOut:
    service = OfferService(db)
    offer = service.send_offer(user, request_id, payload)
    return _mine(offer, offer.request)


@router.post("/offers/{offer_id}/withdraw", response_model=MyOfferOut)
def withdraw_offer(offer_id: int, user: CurrentUser, db: DbSession) -> MyOfferOut:
    offer = OfferService(db).withdraw_offer(user, offer_id)
    return _mine(offer, offer.request)


@router.get("/offers", response_model=Page[MyOfferOut])
def list_offers(
    user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[MyOfferOut]:
    """M6."""
    rows, jobs, total = OfferService(db).list_his(user, page=page, per_page=per_page)
    return Page[MyOfferOut](
        items=[_mine(offer, offer.request, jobs.get(offer.id)) for offer in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


def _row(request: ServiceRequest, mine: Offer | None) -> FeedRequestOut:
    return FeedRequestOut(
        id=request.id,
        title=request.title,
        excerpt=_excerpt(request.description),
        trade=TradeOut.model_validate(request.trade),
        city=ProviderCityOut.model_validate(request.city),
        urgency=request.urgency,
        budget_min_centimes=request.budget_min_centimes,
        budget_max_centimes=request.budget_max_centimes,
        offers_count=request.offers_count,
        photos_count=len(request.photos),
        created_at=request.created_at,
        expires_at=request.expires_at,
        my_offer_id=mine.id if mine else None,
        my_offer_price_centimes=mine.price_centimes if mine else None,
    )


def _mine(offer: Offer, request: ServiceRequest, job_id: int | None = None) -> MyOfferOut:
    return MyOfferOut(
        id=offer.id,
        request_id=offer.request_id,
        request_title=request.title,
        trade=TradeOut.model_validate(request.trade),
        city=ProviderCityOut.model_validate(request.city),
        price_centimes=offer.price_centimes,
        message=offer.message,
        available_from=offer.available_from,
        status=offer.status,
        created_at=offer.created_at,
        responded_at=offer.responded_at,
        job_id=job_id,
    )


def _excerpt(description: str) -> str:
    """Enough to judge from, cut on a word so it does not end mid-syllable."""
    text = " ".join(description.split())
    if len(text) <= EXCERPT:
        return text
    return text[:EXCERPT].rsplit(" ", 1)[0] + "…"
