"""A4 — the support browser, and the one thing it can change."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.enums import RequestStatus, Role
from app.deps import CurrentUser, DbSession, require_roles
from app.models.dispute import Dispute
from app.models.job import Job
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User
from app.schemas.admin_requests import (
    CancelRequestIn,
    RequestDetailOut,
    RequestDisputeOut,
    RequestJobOut,
    RequestOfferOut,
    RequestPersonOut,
    RequestRowOut,
)
from app.schemas.catalog import CityOut, TradeOut
from app.schemas.common import Page
from app.services.admin_requests import AdminRequestService, RequestDetail

router = APIRouter(
    prefix="/admin/requests",
    tags=["admin"],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)


@router.get("", response_model=Page[RequestRowOut])
def list_requests(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=120)] = None,
    status: RequestStatus | None = None,
    city_id: Annotated[int | None, Query(gt=0)] = None,
    trade_id: Annotated[int | None, Query(gt=0)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 25,
) -> Page[RequestRowOut]:
    rows, total = AdminRequestService(db).page(
        query=q,
        status=status,
        city_id=city_id,
        trade_id=trade_id,
        page=page,
        per_page=per_page,
    )
    return Page[RequestRowOut](
        items=[_row(request, client) for request, client in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{request_id}", response_model=RequestDetailOut)
def get_request(request_id: int, db: DbSession) -> RequestDetailOut:
    return _detail(AdminRequestService(db).detail(request_id))


@router.post("/{request_id}/cancel", response_model=RequestDetailOut)
def cancel_request(
    request_id: int,
    payload: CancelRequestIn,
    admin: CurrentUser,
    db: DbSession,
    request: Request,
) -> RequestDetailOut:
    """Close an open request on somebody's behalf. Audited, always."""
    service = AdminRequestService(db)
    return _detail(
        service.cancel(admin, request_id, reason=payload.reason, ip=_ip(request))
    )


def _person(user: User) -> RequestPersonOut:
    return RequestPersonOut(id=user.id, full_name=user.full_name, phone=user.phone)


def _row(request: ServiceRequest, client: User) -> RequestRowOut:
    return RequestRowOut(
        id=request.id,
        title=request.title,
        status=request.status,
        urgency=request.urgency,
        offers_count=request.offers_count,
        created_at=request.created_at,
        client=_person(client),
        trade=TradeOut.model_validate(request.trade),
        city=CityOut.model_validate(request.city),
    )


def _detail(found: RequestDetail) -> RequestDetailOut:
    request = found.request
    return RequestDetailOut(
        id=request.id,
        title=request.title,
        description=request.description,
        status=request.status,
        urgency=request.urgency,
        address=request.address,
        budget_min_centimes=request.budget_min_centimes,
        budget_max_centimes=request.budget_max_centimes,
        photos=len(request.photos),
        offers_count=request.offers_count,
        created_at=request.created_at,
        expires_at=request.expires_at,
        cancelled_at=request.cancelled_at,
        cancel_reason=request.cancel_reason,
        client=_person(found.client),
        trade=TradeOut.model_validate(request.trade),
        city=CityOut.model_validate(request.city),
        offers=[_offer(offer, profile, user) for offer, profile, user in found.offers],
        job=_job(found.job, found.provider) if found.job else None,
        dispute=_dispute(found.dispute) if found.dispute else None,
        can_cancel=request.status is RequestStatus.OPEN,
    )


def _offer(offer: Offer, profile: ProviderProfile, user: User) -> RequestOfferOut:
    return RequestOfferOut(
        id=offer.id,
        price_centimes=offer.price_centimes,
        message=offer.message,
        status=offer.status,
        created_at=offer.created_at,
        lead_fee_centimes=offer.lead_fee_centimes,
        provider=_person(user),
        provider_id=profile.id,
    )


def _job(job: Job, provider: tuple[ProviderProfile, User] | None) -> RequestJobOut:
    return RequestJobOut(
        id=job.id,
        status=job.status,
        agreed_price_centimes=job.agreed_price_centimes,
        started_at=job.started_at,
        finished_at=job.finished_at,
        confirmed_at=job.confirmed_at,
        cancelled_at=job.cancelled_at,
        cancelled_by=job.cancelled_by.value if job.cancelled_by else None,
        cancel_reason=job.cancel_reason,
        provider=_person(provider[1]) if provider else None,
    )


def _dispute(dispute: Dispute) -> RequestDisputeOut:
    return RequestDisputeOut(
        id=dispute.id,
        status=dispute.status,
        reason=dispute.reason.value,
        opened_by_id=dispute.opened_by_id,
    )


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None
