"""Reviews, as a profile page reads them."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Row, Select, func, select
from sqlalchemy.orm import Session

from app.models.catalog import City, Trade
from app.models.job import Job, Review
from app.models.request import ServiceRequest
from app.models.user import User


@dataclass(frozen=True, slots=True)
class ReviewRow:
    """A review with the three things shown beside it."""

    review: Review
    author: User
    city: City | None
    trade: Trade | None


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def breakdown(self, provider_id: int) -> dict[int, int]:
        """How many reviews gave each score, 1 through 5.

        Always all five keys, including the zeros: a bar chart missing its
        empty bars reads as a chart with different categories.
        """
        rows = self.db.execute(
            select(Review.rating, func.count())
            .where(Review.provider_id == provider_id, Review.is_hidden.is_(False))
            .group_by(Review.rating)
        ).all()

        counts = dict.fromkeys(range(1, 6), 0)
        for rating, count in rows:
            counts[int(rating)] = int(count)
        return counts

    def unanswered(self, provider_id: int) -> int:
        """M10's actionable number: how many are still waiting on him.

        It is what turns the screen from a list into a queue — "you have three
        to answer" is a thing to do, "you have 47 reviews" is a fact.
        """
        return int(
            self.db.execute(
                select(func.count())
                .select_from(Review)
                .where(
                    Review.provider_id == provider_id,
                    Review.is_hidden.is_(False),
                    Review.reply.is_(None),
                )
            ).scalar_one()
        )

    def owned_by(self, review_id: int, provider_id: int) -> Review | None:
        """One of his own reviews, or nothing.

        Hidden ones are nothing too: M10 shows him exactly what the public
        sees, so a review D3 took down is not his to answer — a reply under a
        review nobody can read is an argument with a client about something
        invisible.
        """
        return self.db.execute(
            select(Review).where(
                Review.id == review_id,
                Review.provider_id == provider_id,
                Review.is_hidden.is_(False),
            )
        ).scalar_one_or_none()

    def list_for_provider(
        self, provider_id: int, *, page: int = 1, per_page: int = 10
    ) -> tuple[list[ReviewRow], int]:
        base = select(Review).where(
            Review.provider_id == provider_id, Review.is_hidden.is_(False)
        )
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        stmt = (
            _with_context()
            .where(Review.provider_id == provider_id, Review.is_hidden.is_(False))
            # Newest first, with the id breaking ties so pages never overlap.
            .order_by(Review.created_at.desc(), Review.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return [_row(result) for result in self.db.execute(stmt)], total

    def row(self, review_id: int) -> ReviewRow | None:
        """One review with the same three things beside it as in a list.

        So an endpoint that has just written a reply can answer with the review
        it changed, without paging the whole list to find it again.
        """
        result = self.db.execute(
            _with_context().where(Review.id == review_id)
        ).first()
        return None if result is None else _row(result)


def _with_context() -> Select[tuple[Review, User, City, Trade]]:
    """A review, its author, and the city and trade of the job behind it.

    The last two are outer joins, so they come back `None` when the request
    behind the job has lost its city or trade. SQLAlchemy types them as present
    either way; `ReviewRow` is where that is written down honestly.
    """
    return (
        select(Review, User, City, Trade)
        .join(User, User.id == Review.author_id)
        .join(Job, Job.id == Review.job_id)
        .join(ServiceRequest, ServiceRequest.id == Job.request_id)
        .join(City, City.id == ServiceRequest.city_id, isouter=True)
        .join(Trade, Trade.id == ServiceRequest.trade_id, isouter=True)
    )


def _row(result: Row[tuple[Review, User, City, Trade]]) -> ReviewRow:
    review, author, city, trade = result
    return ReviewRow(review=review, author=author, city=city, trade=trade)
