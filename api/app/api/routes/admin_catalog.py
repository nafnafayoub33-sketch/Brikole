"""A6 — the trades and the cities.

There is deliberately no `DELETE` under here. Deactivating is the only removal
this product has, and it is the honest one: it stops a trade being offered and
leaves every job that ever went through it exactly where it is.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.enums import Role
from app.deps import CurrentUser, DbSession, require_roles
from app.models.catalog import City, Trade
from app.repositories.catalog import Usage
from app.schemas.admin_catalog import (
    ActiveIn,
    AdminCityOut,
    AdminTradeOut,
    CatalogOut,
    CityIn,
    NewCityIn,
    NewTradeIn,
    TradeIn,
    UsageOut,
)
from app.services.admin_catalog import AdminCatalogService

router = APIRouter(
    prefix="/admin/catalog",
    tags=["admin"],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)

#: What a row nobody has touched shows: zero of everything, rather than a
#: field the screen has to guess whether to render.
NOTHING = Usage(providers=0, requests=0, jobs=0)


@router.get("", response_model=CatalogOut)
def read_catalog(db: DbSession) -> CatalogOut:
    return _catalog(AdminCatalogService(db))


@router.post("/trades", response_model=CatalogOut, status_code=201)
def create_trade(
    payload: NewTradeIn, admin: CurrentUser, db: DbSession, request: Request
) -> CatalogOut:
    service = AdminCatalogService(db)
    service.create_trade(admin, payload.model_dump(), ip=_ip(request))
    return _catalog(service)


@router.patch("/trades/{trade_id}", response_model=CatalogOut)
def update_trade(
    trade_id: int,
    payload: TradeIn,
    admin: CurrentUser,
    db: DbSession,
    request: Request,
) -> CatalogOut:
    """Everything but the slug — see `AdminCatalogService.update_trade`."""
    service = AdminCatalogService(db)
    service.update_trade(admin, trade_id, payload.model_dump(), ip=_ip(request))
    return _catalog(service)


@router.patch("/trades/{trade_id}/active", response_model=CatalogOut)
def set_trade_active(
    trade_id: int,
    payload: ActiveIn,
    admin: CurrentUser,
    db: DbSession,
    request: Request,
) -> CatalogOut:
    service = AdminCatalogService(db)
    service.set_trade_active(admin, trade_id, active=payload.is_active, ip=_ip(request))
    return _catalog(service)


@router.post("/cities", response_model=CatalogOut, status_code=201)
def create_city(
    payload: NewCityIn, admin: CurrentUser, db: DbSession, request: Request
) -> CatalogOut:
    service = AdminCatalogService(db)
    service.create_city(admin, payload.model_dump(), ip=_ip(request))
    return _catalog(service)


@router.patch("/cities/{city_id}", response_model=CatalogOut)
def update_city(
    city_id: int,
    payload: CityIn,
    admin: CurrentUser,
    db: DbSession,
    request: Request,
) -> CatalogOut:
    service = AdminCatalogService(db)
    service.update_city(admin, city_id, payload.model_dump(), ip=_ip(request))
    return _catalog(service)


@router.patch("/cities/{city_id}/active", response_model=CatalogOut)
def set_city_active(
    city_id: int,
    payload: ActiveIn,
    admin: CurrentUser,
    db: DbSession,
    request: Request,
) -> CatalogOut:
    service = AdminCatalogService(db)
    service.set_city_active(admin, city_id, active=payload.is_active, ip=_ip(request))
    return _catalog(service)


def _catalog(service: AdminCatalogService) -> CatalogOut:
    """Both lists, freshly read.

    Every write returns the whole catalogue rather than the one row it
    changed: activating a trade moves counts on nothing but itself, but
    a screen that patches one row into a list it already had is a screen
    that drifts out of step with the database the first time two admins
    are editing at once.
    """
    trades, trade_usage = service.trades()
    cities, city_usage = service.cities()

    return CatalogOut(
        trades=[_trade(trade, trade_usage.get(trade.id, NOTHING)) for trade in trades],
        cities=[_city(city, city_usage.get(city.id, NOTHING)) for city in cities],
    )


def _usage(usage: Usage) -> UsageOut:
    return UsageOut(providers=usage.providers, requests=usage.requests, jobs=usage.jobs)


def _trade(trade: Trade, usage: Usage) -> AdminTradeOut:
    return AdminTradeOut(
        id=trade.id,
        slug=trade.slug,
        name_ar=trade.name_ar,
        name_fr=trade.name_fr,
        name_en=trade.name_en,
        icon=trade.icon,
        lead_fee_centimes=trade.lead_fee_centimes,
        sort_order=trade.sort_order,
        is_active=trade.is_active,
        usage=_usage(usage),
    )


def _city(city: City, usage: Usage) -> AdminCityOut:
    return AdminCityOut(
        id=city.id,
        slug=city.slug,
        name_ar=city.name_ar,
        name_fr=city.name_fr,
        name_en=city.name_en,
        latitude=city.latitude,
        longitude=city.longitude,
        is_active=city.is_active,
        usage=_usage(usage),
    )


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None
