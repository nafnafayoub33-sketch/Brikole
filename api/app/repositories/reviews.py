"""Reviews, as a profile page reads them."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
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

    def list_for_provider(
        self, provider_id: int, *, page: int = 1, per_page: int = 10
    ) -> tuple[list[ReviewRow], int]:
        base = select(Review).where(
            Review.provider_id == provider_id, Review.is_hidden.is_(False)
        )
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        stmt = (
            select(Review, User, City, Trade)
            .join(User, User.id == Review.author_id)
            .join(Job, Job.id == Review.job_id)
            .join(ServiceRequest, ServiceRequest.id == Job.request_id)
            .join(City, City.id == ServiceRequest.city_id, isouter=True)
            .join(Trade, Trade.id == ServiceRequest.trade_id, isouter=True)
            .where(Review.provider_id == provider_id, Review.is_hidden.is_(False))
            # Newest first, with the id breaking ties so pages never overlap.
            .order_by(Review.created_at.desc(), Review.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        rows = [
            ReviewRow(review=review, author=author, city=city, trade=trade)
            for review, author, city, trade in self.db.execute(stmt)
        ]
        return rows, total
