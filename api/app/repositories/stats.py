"""The counts A1 leads with.

Every number here is a query over rows that exist, never a cached figure kept
up to date by hand. A dashboard whose numbers drift from the tables under it is
worse than no dashboard: it is a wrong answer somebody will act on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    DisputeStatus,
    JobStatus,
    ProviderStatus,
    RequestStatus,
    TransactionType,
)
from app.models.credit import CreditTransaction
from app.models.dispute import Dispute
from app.models.job import Job
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User

#: Anything with a mapped table this module counts rows of.
Countable = User | ProviderProfile | ServiceRequest | Job | CreditTransaction | Dispute


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
