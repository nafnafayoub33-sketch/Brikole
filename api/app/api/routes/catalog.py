"""Trades and cities. Public — P1's grid needs them before anyone signs in."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.deps import DbSession
from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import CityOut, TradeOut

router = APIRouter(tags=["catalog"])


@router.get("/trades", response_model=list[TradeOut])
def list_trades(
    db: DbSession,
    city_id: int | None = Query(
        default=None,
        description="Count only tradesmen working in this city. Omit to count everywhere.",
    ),
) -> list[TradeOut]:
    """The trade grid, with how many tradesmen are actually behind each one."""
    rows = CatalogRepository(db).list_trades_with_counts(city_id=city_id)
    return [
        TradeOut.model_validate(trade).model_copy(update={"providers_count": count})
        for trade, count in rows
    ]


@router.get("/cities", response_model=list[CityOut])
def list_cities(db: DbSession) -> list[CityOut]:
    cities = CatalogRepository(db).list_cities()
    return [CityOut.model_validate(c) for c in cities]
