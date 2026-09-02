"""The counts A1 leads with.

Every number here is a query over rows that exist, never a cached figure kept
up to date by hand. A dashboard whose numbers drift from the tables under it is
worse than no dashboard: it is a wrong answer somebody will act on.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Column, ColumnElement, Select, func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.core.enums import (
    DisputeStatus,
    JobStatus,
    OfferStatus,
    ProviderStatus,
    RequestStatus,
    TopupStatus,
    TransactionType,
)
from app.models.catalog import City, Trade
from app.models.credit import CreditAccount, CreditTransaction, TopupRequest
from app.models.dispute import Dispute
from app.models.job import Job
from app.models.offer import Offer
from app.models.provider import ProviderProfile, provider_trades
from app.models.request import ServiceRequest
from app.models.user import User

#: How far back the trend goes. A year plus the current month, so the same
#: month last year is on the chart to compare against.
MONTHS_BACK = 13

#: Anything with a mapped table this module counts rows of.
#: A column the aggregates group by. Mapped attributes and the columns of the
#: provider/trade join table are both used, and they are separate types.
GroupKey = InstrumentedAttribute[int] | Column[int]

Countable = (
    User | ProviderProfile | ServiceRequest | Job | CreditTransaction | Dispute | TopupRequest
)


@dataclass(frozen=True, slots=True)
class PlatformStats:
    new_users_this_week: int
    #: The week before, so "this week" has something to be measured against.
    new_users_last_week: int
    providers_awaiting_approval: int
    open_requests: int
    jobs_done: int
    #: Accepted offers the platform charged for, and what they came to. A free
    #: lead is a lead sold at zero, so it is counted and adds nothing.
    leads_sold: int
    leads_value_centimes: int
    disputes_open: int


@dataclass(frozen=True, slots=True)
class MoneyStats:
    """Where the money is, and whose it is.

    The platform holds none of the job price — there is no escrow before phase
    3 — so `in_dispute_centimes` is money argued over between a client and a
    tradesman, not money on the platform's books. What the platform itself has
    at stake on those same jobs is the lead fees it charged for them, and a
    refund is the moderator's to order. The two are kept apart deliberately.
    """

    taken_centimes: int
    in_dispute_centimes: int
    disputed_lead_fees_centimes: int
    topups_waiting: int
    topups_waiting_centimes: int
    #: Credit tradesmen have bought and not spent yet — the platform's float.
    credit_held_centimes: int
    #: Balances below zero: leads taken on a wallet that could not cover them.
    credit_owed_centimes: int


@dataclass(frozen=True, slots=True)
class MonthPoint:
    """One month of the trend. Months with nothing in them are still points."""

    month: str
    leads: int
    value_centimes: int
    jobs: int


@dataclass(frozen=True, slots=True)
class PlaceRow:
    """A city or a trade, and how much of the platform happens there."""

    id: int
    slug: str
    name_ar: str
    name_fr: str
    name_en: str
    jobs: int
    open_requests: int
    providers: int
    value_centimes: int


@dataclass(frozen=True, slots=True)
class Funnel:
    """Published -> answered -> hired -> confirmed. Each step is a subset.

    This is the only thing on the dashboard that says whether the marketplace
    works: a request nobody answers is the failure the platform is for.
    """

    requests: int
    with_offer: int
    hired: int
    confirmed: int


def _month_of(column: InstrumentedAttribute[datetime]) -> ColumnElement[str]:
    """`2026-08`, grouped by the database rather than pulled into Python."""
    return func.date_format(column, "%Y-%m")


def _month_start(now: datetime, back: int) -> tuple[int, int, int]:
    month = now.month - back
    year = now.year + (month - 1) // 12
    return year, (month - 1) % 12 + 1, 1


def _month_keys(now: datetime, count: int) -> list[str]:
    """Oldest first, so the chart reads left to right in time."""
    keys = []
    for back in range(count - 1, -1, -1):
        year, month, _ = _month_start(now, back)
        keys.append(f"{year:04d}-{month:02d}")
    return keys


class StatsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def platform(self, *, now: datetime) -> PlatformStats:
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)

        return PlatformStats(
            new_users_this_week=self._count(User, User.created_at >= week_ago),
            new_users_last_week=self._count(
                User, (User.created_at >= two_weeks_ago) & (User.created_at < week_ago)
            ),
            providers_awaiting_approval=self._count(
                ProviderProfile, ProviderProfile.status == ProviderStatus.PENDING
            ),
            open_requests=self._count(
                ServiceRequest, ServiceRequest.status == RequestStatus.OPEN
            ),
            jobs_done=self._count(Job, Job.status == JobStatus.CONFIRMED),
            leads_sold=self._count(
                CreditTransaction,
                CreditTransaction.type.in_(
                    [TransactionType.LEAD_FEE, TransactionType.FREE_LEAD]
                ),
            ),
            # Stored negative — it left the tradesman's balance — and shown as
            # what the platform took.
            leads_value_centimes=-int(
                self.db.execute(
                    select(func.coalesce(func.sum(CreditTransaction.amount_centimes), 0)).where(
                        CreditTransaction.type == TransactionType.LEAD_FEE
                    )
                ).scalar_one()
            ),
            disputes_open=self._count(
                Dispute,
                Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.CLAIMED]),
            ),
        )

    def _count(self, model: type[Countable], condition: ColumnElement[bool]) -> int:
        return int(
            self.db.execute(
                select(func.count()).select_from(model).where(condition)
            ).scalar_one()
        )

    # -- money -----------------------------------------------------------

    def money(self) -> MoneyStats:
        disputed_jobs = select(Dispute.job_id).where(
            Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.CLAIMED])
        )

        return MoneyStats(
            taken_centimes=-self._sum(
                CreditTransaction.amount_centimes,
                CreditTransaction.type == TransactionType.LEAD_FEE,
            ),
            # A job can carry more than one dispute, so the price is summed over
            # jobs, not over disputes, or it would be counted twice.
            in_dispute_centimes=self._sum(
                Job.agreed_price_centimes, Job.id.in_(disputed_jobs)
            ),
            disputed_lead_fees_centimes=-self._sum(
                CreditTransaction.amount_centimes,
                (CreditTransaction.type == TransactionType.LEAD_FEE)
                & CreditTransaction.job_id.in_(disputed_jobs),
            ),
            topups_waiting=self._count(
                TopupRequest, TopupRequest.status == TopupStatus.PENDING
            ),
            topups_waiting_centimes=self._sum(
                TopupRequest.amount_centimes, TopupRequest.status == TopupStatus.PENDING
            ),
            credit_held_centimes=self._sum(
                CreditAccount.balance_centimes, CreditAccount.balance_centimes > 0
            ),
            credit_owed_centimes=-self._sum(
                CreditAccount.balance_centimes, CreditAccount.balance_centimes < 0
            ),
        )

    # -- the trend -------------------------------------------------------

    def months(self, *, now: datetime) -> list[MonthPoint]:
        """The last `MONTHS_BACK` months, oldest first, gaps included.

        A month with no work is a fact about the platform, not a row to leave
        out: dropping it would close the gap on the chart and draw a line that
        never happened.
        """
        wanted = _month_keys(now, MONTHS_BACK)
        since = datetime(*_month_start(now, MONTHS_BACK - 1))

        leads: dict[str, tuple[int, int]] = {
            str(month): (int(count), -int(total))
            for month, count, total in self.db.execute(
                select(
                    _month_of(CreditTransaction.created_at),
                    func.count(),
                    func.coalesce(func.sum(CreditTransaction.amount_centimes), 0),
                )
                .where(
                    CreditTransaction.type.in_(
                        [TransactionType.LEAD_FEE, TransactionType.FREE_LEAD]
                    ),
                    CreditTransaction.created_at >= since,
                )
                .group_by(_month_of(CreditTransaction.created_at))
            )
        }

        jobs: dict[str, int] = {
            str(month): int(count)
            for month, count in self.db.execute(
                select(_month_of(Job.created_at), func.count())
                .where(Job.status == JobStatus.CONFIRMED, Job.created_at >= since)
                .group_by(_month_of(Job.created_at))
            )
        }

        return [
            MonthPoint(
                month=key,
                leads=leads.get(key, (0, 0))[0],
                value_centimes=leads.get(key, (0, 0))[1],
                jobs=jobs.get(key, 0),
            )
            for key in wanted
        ]

    # -- where the work is ------------------------------------------------

    def cities(self) -> list[PlaceRow]:
        rows = list(self.db.execute(select(City).where(City.is_active.is_(True))).scalars())
        return self._places(
            rows,
            key=ServiceRequest.city_id,
            providers=self._grouped(
                ProviderProfile.city_id,
                select(ProviderProfile.city_id, func.count())
                .select_from(ProviderProfile)
                .where(ProviderProfile.status == ProviderStatus.APPROVED),
            ),
        )

    def trades(self) -> list[PlaceRow]:
        rows = list(self.db.execute(select(Trade).where(Trade.is_active.is_(True))).scalars())
        return self._places(
            rows,
            key=ServiceRequest.trade_id,
            # A tradesman can work more than one trade, so this counts the
            # join rows, not the tradesmen: the columns deliberately add up to
            # more than the number of people on the platform.
            providers=self._grouped(
                provider_trades.c.trade_id,
                select(provider_trades.c.trade_id, func.count())
                .select_from(provider_trades)
                .join(ProviderProfile, ProviderProfile.id == provider_trades.c.provider_id)
                .where(ProviderProfile.status == ProviderStatus.APPROVED),
            ),
        )

    def _places(
        self,
        rows: Sequence[City] | Sequence[Trade],
        *,
        key: GroupKey,
        providers: dict[int, int],
    ) -> list[PlaceRow]:
        """One row per city or trade, each measure counted on its own.

        Four small aggregates keyed by id, rather than one join carrying them
        all: a single query walking three one-to-many paths at once multiplies
        its own rows, and every total on it comes out wrong.
        """
        jobs = self._grouped(
            key,
            select(key, func.count())
            .select_from(Job)
            .join(ServiceRequest, ServiceRequest.id == Job.request_id)
            .where(Job.status == JobStatus.CONFIRMED),
        )
        value = self._grouped(
            key,
            select(key, func.coalesce(func.sum(CreditTransaction.amount_centimes), 0))
            .select_from(CreditTransaction)
            .join(Job, Job.id == CreditTransaction.job_id)
            .join(ServiceRequest, ServiceRequest.id == Job.request_id)
            .where(CreditTransaction.type == TransactionType.LEAD_FEE),
        )
        waiting = self._grouped(
            key,
            select(key, func.count())
            .select_from(ServiceRequest)
            .where(ServiceRequest.status == RequestStatus.OPEN),
        )

        places = [
            PlaceRow(
                id=row.id,
                slug=row.slug,
                name_ar=row.name_ar,
                name_fr=row.name_fr,
                name_en=row.name_en,
                jobs=jobs.get(row.id, 0),
                open_requests=waiting.get(row.id, 0),
                providers=providers.get(row.id, 0),
                value_centimes=-value.get(row.id, 0),
            )
            for row in rows
        ]
        places.sort(key=lambda place: (-place.jobs, -place.value_centimes, place.slug))
        return places

    def _grouped(
        self, key: GroupKey, statement: Select[Any]
    ) -> dict[int, int]:
        return {
            int(key_value): int(total)
            for key_value, total in self.db.execute(statement.group_by(key))
            if key_value is not None
        }

    # -- does the marketplace work ----------------------------------------

    def funnel(self) -> Funnel:
        return Funnel(
            requests=self._count(ServiceRequest, ServiceRequest.id.is_not(None)),
            with_offer=int(
                self.db.execute(
                    select(func.count(func.distinct(Offer.request_id))).where(
                        Offer.status != OfferStatus.WITHDRAWN
                    )
                ).scalar_one()
            ),
            hired=self._count(ServiceRequest, ServiceRequest.id.in_(select(Job.request_id))),
            confirmed=self._count(Job, Job.status == JobStatus.CONFIRMED),
        )

    # -- plumbing ---------------------------------------------------------

    def _sum(
        self, column: InstrumentedAttribute[int], condition: ColumnElement[bool]
    ) -> int:
        return int(
            self.db.execute(
                select(func.coalesce(func.sum(column), 0)).where(condition)
            ).scalar_one()
        )
