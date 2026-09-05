"""M10 — the tradesman reading what clients wrote, and answering once.

He sees exactly what the public sees. A review D3 has hidden is not on his
page: the platform decided not to stand behind it, and putting it back in front
of him would only send him to argue with a client about something nobody else
can read.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import ProviderStatus
from app.core.errors import DomainError, ErrorCode
from app.core.review_reply import validate_reply
from app.models.base import utcnow
from app.models.provider import ProviderProfile
from app.models.user import User
from app.repositories.reviews import ReviewRepository, ReviewRow
from app.services.provider import ProviderProfileService


class ProviderReviewsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.reviews = ReviewRepository(db)

    def page(
        self, user: User, *, page: int, per_page: int
    ) -> tuple[list[ReviewRow], int]:
        profile = self._approved(user)
        return self.reviews.list_for_provider(
            profile.id, page=page, per_page=per_page
        )

    def summary(self, user: User) -> tuple[ProviderProfile, dict[int, int], int]:
        """His numbers, and the one that is a thing to do.

        `unanswered` is the difference between a list and a queue: "three to
        answer" is work, "forty-seven reviews" is a fact.
        """
        profile = self._approved(user)
        return (
            profile,
            self.reviews.breakdown(profile.id),
            self.reviews.unanswered(profile.id),
        )

    def reply(self, user: User, review_id: int, text: str) -> ReviewRow:
        """His one answer. `validate_reply` is what makes it one."""
        profile = self._approved(user)

        review = self.reviews.owned_by(review_id, profile.id)
        if review is None:
            # Somebody else's review id is a 404, not a 403: the id space is
            # guessable and a 403 would confirm the review exists.
            raise DomainError(ErrorCode.NOT_FOUND)

        review.reply = validate_reply(text, already_replied=review.reply is not None)
        review.replied_at = utcnow()

        self.db.commit()

        row = self.reviews.row(review_id)
        assert row is not None  # it was just written
        return row

    def _approved(self, user: User) -> ProviderProfile:
        """M10 is for a tradesman who is on the platform. Before that he has no
        reviews to read, and the screen he needs is M2."""
        profile = ProviderProfileService(self.db).get_own(user)
        if profile is None:
            raise DomainError(ErrorCode.NOT_FOUND)
        if profile.status is not ProviderStatus.APPROVED:
            raise DomainError(ErrorCode.CONFLICT, status=profile.status.value)
        return profile
