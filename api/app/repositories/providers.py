"""Every query about tradesmen."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.enums import ProviderStatus, UserStatus
from app.models.catalog import Trade
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
        query: str | None = None,
        trade_id: int | None = None,
        city_id: int | None = None,
        sort: ProviderSort = ProviderSort.RATING,
        page: int = 1,
        per_page: int = 12,
    ) -> tuple[list[ProviderProfile], int]:
        stmt = self._visible()

        if city_id is not None:
            stmt = stmt.where(ProviderProfile.city_id == city_id)

        if query:
            stmt = stmt.where(self._matches(query))
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

        # Paid placement comes first, inside whatever the client asked to sort
        # by — it moves a tradesman up the list and does nothing else. It is
        # never a filter, so the man who did not pay is still on the page, and
        # it never touches a rating: what a client is told about somebody is
        # not for sale. The card carries a badge saying the position was paid
        # for, because placement a reader cannot see the reason for is a lie
        # by omission.
        #
        # `id` breaks every tie, so page 2 never repeats a row from page 1.
        boosted_first = self._boosted().desc()

        if sort is ProviderSort.JOBS:
            stmt = stmt.order_by(
                boosted_first, ProviderProfile.jobs_done.desc(), ProviderProfile.id.asc()
            )
        elif sort is ProviderSort.NEWEST:
            stmt = stmt.order_by(
                boosted_first, ProviderProfile.created_at.desc(), ProviderProfile.id.asc()
            )
        elif sort is ProviderSort.PRICE:
            # Nulls last: "I would rather quote" must not sort as "free".
            stmt = stmt.order_by(
                boosted_first,
                ProviderProfile.starting_price_centimes.is_(None),
                ProviderProfile.starting_price_centimes.asc(),
                ProviderProfile.id.asc(),
            )
        else:
            stmt = stmt.order_by(
                boosted_first,
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

    @staticmethod
    def _boosted() -> ColumnElement[bool]:
        """Whether his placement is paid for *right now*.

        Compared against the clock rather than kept as a flag: a boost that has
        run out needs nothing swept, and there is no job to forget to run.

        Two details that both bite silently.

        **The null check is not redundant.** `NULL > x` is NULL, and MySQL
        sorts NULL last under `DESC` — so a tradesman whose boost *lapsed*
        (false) would outrank one who never bought one (null). Written this
        way the expression is only ever true or false.

        **`UTC_TIMESTAMP()`, never `NOW()`.** These columns are naive UTC by
        contract; `NOW()` is the database server's wall clock, and on a machine
        set to Casablanca time it would call a boost active for an hour after
        it expired — and only there, which is the worst kind of bug to find.
        """
        return and_(
            ProviderProfile.boosted_until.is_not(None),
            ProviderProfile.boosted_until > func.utc_timestamp(),
        )

    @staticmethod
    def _matches(query: str) -> ColumnElement[bool]:
        """Match a name, a headline, or a trade — in any of the three languages.

        Somebody types "plombier", "سباك" or a person's name into one box and
        expects the same box to understand all three. `%` and `_` are escaped
        so a stray underscore in a search term does not quietly become a
        wildcard.
        """
        needle = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{needle}%"

        trade_match = select(provider_trades.c.provider_id).join(
            Trade, Trade.id == provider_trades.c.trade_id
        ).where(
            or_(
                Trade.name_ar.like(pattern, escape="\\"),
                Trade.name_fr.like(pattern, escape="\\"),
                Trade.name_en.like(pattern, escape="\\"),
                Trade.slug.like(pattern, escape="\\"),
            )
        )

        return or_(
            User.full_name.like(pattern, escape="\\"),
            ProviderProfile.headline.like(pattern, escape="\\"),
            ProviderProfile.id.in_(trade_match),
        )

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
