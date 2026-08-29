"""A1's dashboard tiles.

Small on purpose — the point in Phase 0 is that the gate is real: a moderator
holding a perfectly valid token gets 403 here, because money is not his.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.enums import ProviderStatus, RequestStatus, Role, UserStatus
from app.core.permissions import Permission
from app.deps import DbSession, require_permission
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


class OverviewOut(BaseModel):
    clients: int
    providers: int
    providers_pending: int
    moderators: int
    admins: int
    requests_open: int
    suspended_users: int


@router.get(
    "/overview",
    response_model=OverviewOut,
    dependencies=[Depends(require_permission(Permission.READ_STATS))],
)
def overview(db: DbSession) -> OverviewOut:
    rows = db.execute(
        select(User.role, func.count())
        .where(User.status != UserStatus.DELETED)
        .group_by(User.role)
    ).all()
    by_role: dict[Role, int] = {role: count for role, count in rows}

    providers_pending = db.execute(
        select(func.count())
        .select_from(ProviderProfile)
        .where(ProviderProfile.status == ProviderStatus.PENDING)
    ).scalar_one()

    requests_open = db.execute(
        select(func.count())
        .select_from(ServiceRequest)
        .where(ServiceRequest.status == RequestStatus.OPEN)
    ).scalar_one()

    suspended = db.execute(
        select(func.count()).select_from(User).where(User.status == UserStatus.SUSPENDED)
    ).scalar_one()

    return OverviewOut(
        clients=by_role.get(Role.CLIENT, 0),
        providers=by_role.get(Role.PROVIDER, 0),
        providers_pending=providers_pending,
        moderators=by_role.get(Role.MODERATOR, 0),
        admins=by_role.get(Role.ADMIN, 0),
        requests_open=requests_open,
        suspended_users=suspended,
    )
