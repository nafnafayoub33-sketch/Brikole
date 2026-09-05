"""A2 — the approvals queue."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.permissions import Permission
from app.deps import CurrentUser, DbSession, require_permission
from app.models.provider import ProviderProfile
from app.repositories.reviews import ReviewRepository
from app.schemas.catalog import TradeOut
from app.schemas.common import Page
from app.schemas.pro import ApplicationOut, RejectionIn
from app.schemas.provider import ProviderCityOut, ProviderPhotoOut
from app.services.approvals import ApprovalService
from app.services.provider import availability_of

router = APIRouter(
    prefix="/admin/approvals",
    tags=["admin"],
    dependencies=[Depends(require_permission(Permission.APPROVE_PROVIDER))],
)


@router.get("", response_model=Page[ApplicationOut])
def list_pending(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[ApplicationOut]:
    rows, total = ApprovalService(db).queue(page=page, per_page=per_page)
    return Page[ApplicationOut](
        items=[_application(row, db) for row in rows], total=total, page=page, per_page=per_page
    )


@router.get("/{provider_id}", response_model=ApplicationOut)
def get_application(provider_id: int, db: DbSession) -> ApplicationOut:
    return _application(ApprovalService(db).get(provider_id), db)


@router.post("/{provider_id}/approve", response_model=ApplicationOut)
def approve(
    provider_id: int, user: CurrentUser, db: DbSession, request: Request
) -> ApplicationOut:
    profile = ApprovalService(db).approve(user, provider_id, ip=_ip(request))
    return _application(profile, db)


@router.post("/{provider_id}/reject", response_model=ApplicationOut)
def reject(
    provider_id: int,
    payload: RejectionIn,
    user: CurrentUser,
    db: DbSession,
    request: Request,
) -> ApplicationOut:
    profile = ApprovalService(db).reject(
        user, provider_id, reason=payload.reason, ip=_ip(request)
    )
    return _application(profile, db)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _application(profile: ProviderProfile, db: DbSession) -> ApplicationOut:
    return ApplicationOut(
        id=profile.id,
        full_name=profile.user.full_name,
        phone=profile.user.phone,
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
        bio=profile.bio,
        radius_km=profile.radius_km,
        member_since=profile.created_at,
        submitted_at=profile.updated_at,
        rating_breakdown=ReviewRepository(db).breakdown(profile.id),
        photos=[ProviderPhotoOut.model_validate(photo) for photo in profile.photos],
        rejection_reason=profile.rejection_reason,
        id_card_path=profile.id_card_url,
        availability=availability_of(profile),
    )
