"""A3 — the accounts screen.

The only place on the platform where a role changes, and the only place a
suspension can be made permanent. Everything under here is admin-only and
everything that changes an account writes an audit row.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select

from app.core.enums import Role, UserStatus
from app.deps import CurrentUser, DbSession, require_roles
from app.models.credit import CreditAccount
from app.models.dispute import Dispute
from app.models.user import User
from app.schemas.catalog import CityOut
from app.schemas.common import Page
from app.schemas.staff import (
    NewStaffIn,
    RoleIn,
    SuspendIn,
    UserActivityOut,
    UserDetailOut,
    UserDisputeOut,
    UserProviderOut,
    UserRowOut,
)
from app.services.staff import StaffService

router = APIRouter(
    prefix="/admin/users",
    tags=["admin"],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)


@router.get("", response_model=Page[UserRowOut])
def list_users(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=120)] = None,
    role: Role | None = None,
    status: UserStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 25,
) -> Page[UserRowOut]:
    rows, total = StaffService(db).page(
        query=q, role=role, status=status, page=page, per_page=per_page
    )
    return Page[UserRowOut](
        items=[_row(user) for user in rows], total=total, page=page, per_page=per_page
    )


@router.get("/{user_id}", response_model=UserDetailOut)
def get_user(user_id: int, db: DbSession) -> UserDetailOut:
    service = StaffService(db)
    user = service.get(user_id)
    return _detail(user, service, db)


@router.post("/{user_id}/suspend", response_model=UserDetailOut)
def suspend(
    user_id: int,
    payload: SuspendIn,
    actor: CurrentUser,
    db: DbSession,
    request: Request,
) -> UserDetailOut:
    service = StaffService(db)
    user = service.suspend(
        actor, user_id, days=payload.days, reason=payload.reason, ip=_ip(request)
    )
    return _detail(user, service, db)


@router.post("/{user_id}/reactivate", response_model=UserDetailOut)
def reactivate(
    user_id: int, actor: CurrentUser, db: DbSession, request: Request
) -> UserDetailOut:
    service = StaffService(db)
    user = service.reactivate(actor, user_id, ip=_ip(request))
    return _detail(user, service, db)


@router.patch("/{user_id}/role", response_model=UserDetailOut)
def change_role(
    user_id: int,
    payload: RoleIn,
    actor: CurrentUser,
    db: DbSession,
    request: Request,
) -> UserDetailOut:
    service = StaffService(db)
    user = service.change_role(actor, user_id, role=payload.role, ip=_ip(request))
    return _detail(user, service, db)


@router.post("", response_model=UserDetailOut, status_code=201)
def create_staff(
    payload: NewStaffIn, actor: CurrentUser, db: DbSession, request: Request
) -> UserDetailOut:
    service = StaffService(db)
    user = service.create_staff(
        actor,
        phone=payload.phone,
        full_name=payload.full_name,
        password=payload.password,
        role=payload.role,
        language=payload.language,
        ip=_ip(request),
    )
    return _detail(user, service, db)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _row(user: User) -> UserRowOut:
    return UserRowOut(
        id=user.id,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        avatar_url=user.avatar_url,
        city=CityOut.model_validate(user.city) if user.city else None,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        suspended_until=user.suspended_until,
        provider_status=(
            user.provider_profile.status if user.provider_profile else None
        ),
    )


def _detail(user: User, service: StaffService, db: DbSession) -> UserDetailOut:
    row = _row(user)
    return UserDetailOut(
        **row.model_dump(),
        language=user.language,
        suspension_reason=user.suspension_reason,
        locked_until=user.locked_until,
        provider=_provider(user, db),
        activity=UserActivityOut(**asdict(service.activity(user))),
        disputes=[_dispute(row_, user) for row_ in service.disputes(user)],
    )


def _provider(user: User, db: DbSession) -> UserProviderOut | None:
    profile = user.provider_profile
    if profile is None:
        return None

    account = db.execute(
        select(CreditAccount).where(CreditAccount.provider_id == profile.id)
    ).scalar_one_or_none()
    return UserProviderOut(
        id=profile.id,
        status=profile.status,
        headline=profile.headline,
        rating_avg=profile.rating_avg,
        rating_count=profile.rating_count,
        jobs_done=profile.jobs_done,
        balance_centimes=account.balance_centimes if account else 0,
        free_leads_left=account.free_leads_left if account else 0,
    )


def _dispute(dispute: Dispute, user: User) -> UserDisputeOut:
    return UserDisputeOut(
        id=dispute.id,
        job_id=dispute.job_id,
        status=dispute.status,
        reason=dispute.reason,
        created_at=dispute.created_at,
        opened_by_them=dispute.opened_by_id == user.id,
    )
