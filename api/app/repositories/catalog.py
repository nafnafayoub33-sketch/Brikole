"""Trades, cities, and the platform settings table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.orm import Session

from app.core.enums import ProviderStatus
from app.core.policy import DEFAULTS
from app.models.catalog import City, Trade
from app.models.job import Job
from app.models.provider import ProviderProfile, provider_trades
from app.models.request import ServiceRequest
from app.models.system import PlatformSetting


class CatalogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_trades(self, *, only_active: bool = True) -> list[Trade]:
        stmt = select(Trade).order_by(Trade.sort_order, Trade.slug)
        if only_active:
            stmt = stmt.where(Trade.is_active.is_(True))
        return list(self.db.execute(stmt).scalars())

    def list_trades_with_counts(
        self, *, city_id: int | None = None, only_active: bool = True
    ) -> list[tuple[Trade, int]]:
        """Every trade with how many hireable tradesmen work in it.

        The count is the whole reason a visitor trusts the grid: "plumber" with
        nobody behind it is a dead end, and saying so beats letting them post a
        request nobody will answer.

        `city_id` narrows it to one city, because a plumber in Meknès is no use
        to somebody in Rabat — which is the difference between a real count and
        a vanity one. The join stays an outer join so a trade with nobody in it
        still comes back, with zero.
        """
        joined = (
            select(Trade, func.count(distinct(ProviderProfile.id)).label("providers_count"))
            .outerjoin(provider_trades, provider_trades.c.trade_id == Trade.id)
            .outerjoin(
                ProviderProfile,
                (ProviderProfile.id == provider_trades.c.provider_id)
                & (ProviderProfile.status == ProviderStatus.APPROVED)
                # Counted the same way the grid is filtered, or the page says
                # "12 plumbers" and then shows nine.
                & (
                    ProviderProfile.accepting_work.is_(True)
                    | (
                        ProviderProfile.back_on.is_not(None)
                        & (ProviderProfile.back_on <= func.utc_date())
                    )
                )
                & (ProviderProfile.city_id == city_id if city_id is not None else True),
            )
            .group_by(Trade.id)
            .order_by(Trade.sort_order, Trade.slug)
        )
        if only_active:
            joined = joined.where(Trade.is_active.is_(True))

        return [(trade, count) for trade, count in self.db.execute(joined).all()]

    def get_trade_by_slug(self, slug: str) -> Trade | None:
        return self.db.execute(select(Trade).where(Trade.slug == slug)).scalar_one_or_none()

    def list_cities(self, *, only_active: bool = True) -> list[City]:
        stmt = select(City).order_by(City.name_fr)
        if only_active:
            stmt = stmt.where(City.is_active.is_(True))
        return list(self.db.execute(stmt).scalars())


@dataclass(frozen=True, slots=True)
class Usage:
    """What points at one trade or one city.

    A6 shows these beside the switch. Deactivating is not a delete and never
    loses a row, but "this hides a trade 41 tradesmen work in" is the
    difference between a decision and a click.
    """

    providers: int
    requests: int
    jobs: int


class AdminCatalogRepository:
    """A6's view: the same two lists, including what the public never sees."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def trades(self) -> list[Trade]:
        """Inactive ones included — this is the screen that turns them back on."""
        return list(
            self.db.execute(select(Trade).order_by(Trade.sort_order, Trade.slug)).scalars()
        )

    def cities(self) -> list[City]:
        return list(self.db.execute(select(City).order_by(City.name_fr)).scalars())

    def trade(self, trade_id: int) -> Trade | None:
        return self.db.get(Trade, trade_id)

    def city(self, city_id: int) -> City | None:
        return self.db.get(City, city_id)

    def slug_taken(self, model: type[Trade] | type[City], slug: str) -> bool:
        return (
            self.db.execute(select(model.id).where(model.slug == slug)).first() is not None
        )

    def trade_usage(self) -> dict[int, Usage]:
        """Counted for every trade in three queries, not three per row.

        Keyed by id and joined in Python: a single query walking three
        one-to-many paths at once multiplies its own rows, and the totals come
        back quietly wrong.
        """
        providers = self._counts(
            select(provider_trades.c.trade_id, func.count())
            .group_by(provider_trades.c.trade_id)
        )
        requests = self._counts(
            select(ServiceRequest.trade_id, func.count()).group_by(ServiceRequest.trade_id)
        )
        jobs = self._counts(
            select(ServiceRequest.trade_id, func.count())
            .join(Job, Job.request_id == ServiceRequest.id)
            .group_by(ServiceRequest.trade_id)
        )
        return {
            trade.id: Usage(
                providers=providers.get(trade.id, 0),
                requests=requests.get(trade.id, 0),
                jobs=jobs.get(trade.id, 0),
            )
            for trade in self.trades()
        }

    def city_usage(self) -> dict[int, Usage]:
        providers = self._counts(
            select(ProviderProfile.city_id, func.count()).group_by(ProviderProfile.city_id)
        )
        requests = self._counts(
            select(ServiceRequest.city_id, func.count()).group_by(ServiceRequest.city_id)
        )
        jobs = self._counts(
            select(ServiceRequest.city_id, func.count())
            .join(Job, Job.request_id == ServiceRequest.id)
            .group_by(ServiceRequest.city_id)
        )
        return {
            city.id: Usage(
                providers=providers.get(city.id, 0),
                requests=requests.get(city.id, 0),
                jobs=jobs.get(city.id, 0),
            )
            for city in self.cities()
        }

    def _counts(self, stmt: Select[tuple[int, int]]) -> dict[int, int]:
        # Every key here is a NOT NULL foreign key, so there is nothing to
        # filter out — a missing id simply does not appear, and the callers
        # read it back with a default of zero.
        return {key: count for key, count in self.db.execute(stmt).all()}


class SettingsRepository:
    """Reads `platform_settings`, falling back to `app.core.policy.DEFAULTS`.

    The fallback is what makes a fresh database — or a key an admin has not
    touched — behave instead of crash.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, key: str) -> Any:
        row = self.db.get(PlatformSetting, key)
        if row is None:
            return DEFAULTS.get(key)
        return row.value

    def get_int(self, key: str) -> int:
        value = self.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            fallback = DEFAULTS.get(key)
            return int(fallback) if isinstance(fallback, int) else 0
        return value

    def set(self, key: str, value: Any, *, actor_id: int | None = None) -> PlatformSetting:
        row = self.db.get(PlatformSetting, key)
        if row is None:
            row = PlatformSetting(key=key, value=value, updated_by_id=actor_id)
            self.db.add(row)
        else:
            row.value = value
            row.updated_by_id = actor_id
        self.db.flush()
        return row
