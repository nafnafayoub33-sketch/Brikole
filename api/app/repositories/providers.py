"""Every query about tradesmen."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ProviderStatus, UserStatus
from app.models.provider import ProviderProfile, provider_trades
from app.models.user import User


class ProviderSort(StrEnum):
    RATING = "rating"
    JOBS = "jobs"
    PRICE = "price"
    NEWEST = "newest"


class ProviderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _visible(self) -> Select[tuple[ProviderProfile]]:
        """Only approved tradesmen on live accounts are ever listed.

        A pending application is not somebody you can hire, and a suspended
        account must disappear from the grid the moment it is suspended rather
        than at the next deploy.
        """
        return (
            select(ProviderProfile)
            .join(User, User.id == ProviderProfile.user_id)
            .where(
                ProviderProfile.status == ProviderStatus.APPROVED,
                User.status == UserStatus.ACTIVE,
            )
        )

    def list_cards(
        self,
        *,
        trade_id: int | None = None,
        city_id: int | None = None,
        sort: ProviderSort = ProviderSort.RATING,
        page: int = 1,
        per_page: int = 12,
    ) -> tuple[list[ProviderProfile], int]:
        stmt = self._visible()

        if city_id is not None:
            stmt = stmt.where(ProviderProfile.city_id == city_id)
        if trade_id is not None:
            stmt = stmt.where(
                ProviderProfile.id.in_(
                    select(provider_trades.c.provider_id).where(
                        provider_trades.c.trade_id == trade_id
                    )
                )
            )

        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()

        stmt = stmt.options(
            selectinload(ProviderProfile.user),
            selectinload(ProviderProfile.city),
            selectinload(ProviderProfile.trades),
        )

        # `id` breaks every tie, so page 2 never repeats a row from page 1.
        if sort is ProviderSort.JOBS:
            stmt = stmt.order_by(ProviderProfile.jobs_done.desc(), ProviderProfile.id.asc())
        elif sort is ProviderSort.NEWEST:
            stmt = stmt.order_by(ProviderProfile.created_at.desc(), ProviderProfile.id.asc())
        elif sort is ProviderSort.PRICE:
            # Nulls last: "I would rather quote" must not sort as "free".
            stmt = stmt.order_by(
                ProviderProfile.starting_price_centimes.is_(None),
                ProviderProfile.starting_price_centimes.asc(),
                ProviderProfile.id.asc(),
            )
        else:
            stmt = stmt.order_by(
                ProviderProfile.rating_avg.desc(),
                ProviderProfile.rating_count.desc(),
                ProviderProfile.id.asc(),
            )

        rows = list(
            self.db.execute(stmt.offset((page - 1) * per_page).limit(per_page))
            .scalars()
            .unique()
        )
        return rows, total

    def get_card(self, provider_id: int) -> ProviderProfile | None:
        stmt = (
            self._visible()
            .where(ProviderProfile.id == provider_id)
            .options(
                selectinload(ProviderProfile.user),
                selectinload(ProviderProfile.city),
                selectinload(ProviderProfile.trades),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()
