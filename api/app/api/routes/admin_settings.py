"""A7 and A8 — the platform's dials, and the record of who turned them."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.enums import Role
from app.deps import CurrentUser, DbSession, require_roles
from app.models.base import utcnow
from app.models.system import AuditLog, PlatformSetting
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.repositories.stats import PlaceRow, StatsRepository
from app.schemas.admin_settings import (
    AuditEntryOut,
    AuditFiltersOut,
    FunnelOut,
    MoneyOut,
    MonthOut,
    PlaceOut,
    PlatformStatsOut,
    SettingOut,
    SettingsOut,
    UpdateSettingsIn,
)
from app.schemas.common import Page
from app.services.admin_settings import PlatformSettingsService

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)


@router.get("/stats", response_model=PlatformStatsOut)
def platform_stats(db: DbSession) -> PlatformStatsOut:
    """A1. Every figure is a query over the rows it describes, not a cache.

    The whole dashboard in one response. The alternative — a request per panel
    — buys nothing here: the counts are small, and a screen that reads six
    endpoints can show six different moments of the same platform.
    """
    now = utcnow()
    repository = StatsRepository(db)
    stats = repository.platform(now=now)
    money = repository.money()
    funnel = repository.funnel()

    return PlatformStatsOut(
        new_users_this_week=stats.new_users_this_week,
        new_users_last_week=stats.new_users_last_week,
        providers_awaiting_approval=stats.providers_awaiting_approval,
        open_requests=stats.open_requests,
        jobs_done=stats.jobs_done,
        leads_sold=stats.leads_sold,
        leads_value_centimes=stats.leads_value_centimes,
        disputes_open=stats.disputes_open,
        money=MoneyOut(
            taken_centimes=money.taken_centimes,
            in_dispute_centimes=money.in_dispute_centimes,
            disputed_lead_fees_centimes=money.disputed_lead_fees_centimes,
            topups_waiting=money.topups_waiting,
            topups_waiting_centimes=money.topups_waiting_centimes,
            credit_held_centimes=money.credit_held_centimes,
            credit_owed_centimes=money.credit_owed_centimes,
        ),
        months=[
            MonthOut(
                month=point.month,
                leads=point.leads,
                value_centimes=point.value_centimes,
                jobs=point.jobs,
            )
            for point in repository.months(now=now)
        ],
        cities=[_place(row) for row in repository.cities()],
        trades=[_place(row) for row in repository.trades()],
        funnel=FunnelOut(
            requests=funnel.requests,
            with_offer=funnel.with_offer,
            hired=funnel.hired,
            confirmed=funnel.confirmed,
        ),
    )


def _place(row: PlaceRow) -> PlaceOut:
    return PlaceOut(
        id=row.id,
        slug=row.slug,
        name_ar=row.name_ar,
        name_fr=row.name_fr,
        name_en=row.name_en,
        jobs=row.jobs,
        open_requests=row.open_requests,
        providers=row.providers,
        value_centimes=row.value_centimes,
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings(db: DbSession) -> SettingsOut:
    """A7."""
    rows = PlatformSettingsService(db).list_all()
    return SettingsOut(items=[_setting(key, value, row) for key, value, row in rows])


@router.patch("/settings", response_model=SettingsOut)
def update_settings(
    payload: UpdateSettingsIn, user: CurrentUser, db: DbSession, request: Request
) -> SettingsOut:
    """A partial write: only the keys sent are touched."""
    rows = PlatformSettingsService(db).update(user, payload.values, ip=_ip(request))
    return SettingsOut(items=[_setting(key, value, row) for key, value, row in rows])


@router.get("/audit", response_model=Page[AuditEntryOut])
def read_audit(
    db: DbSession,
    actor_id: Annotated[int | None, Query(gt=0)] = None,
    action: str | None = None,
    target_type: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Page[AuditEntryOut]:
    """A8. Read-only: there is deliberately no write and no delete here."""
    rows, total = AuditRepository(db).page(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        page=page,
        per_page=per_page,
    )
    return Page[AuditEntryOut](
        items=[_entry(entry, actor) for entry, actor in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/audit/filters", response_model=AuditFiltersOut)
def audit_filters(db: DbSession) -> AuditFiltersOut:
    """Only what the log actually contains, so a filter never returns nothing
    because the option was invented by the screen."""
    repo = AuditRepository(db)
    return AuditFiltersOut(
        actions=repo.distinct_actions(), target_types=repo.distinct_target_types()
    )


def _setting(key: str, value: object, row: PlatformSetting | None) -> SettingOut:
    return SettingOut(
        key=key,
        value=value,
        updated_at=row.updated_at if row is not None else None,
        updated_by_name=(
            row.updated_by.full_name if row is not None and row.updated_by else None
        ),
    )


def _entry(entry: AuditLog, actor: User | None) -> AuditEntryOut:
    return AuditEntryOut(
        id=entry.id,
        action=entry.action,
        target_type=entry.target_type,
        target_id=entry.target_id,
        actor_id=entry.actor_id,
        actor_name=actor.full_name if actor else None,
        before=entry.before,
        after=entry.after,
        note=entry.note,
        ip=entry.ip,
        created_at=entry.created_at,
    )


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None
