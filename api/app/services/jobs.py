"""Accepting an offer, and everything the job does afterwards.

The acceptance is the only place in the product where money moves as a side
effect of somebody pressing a button, so it is the one transaction worth
reading carefully: one offer wins, the rest are declined, the request is taken
off the market, the job exists, and the tradesman is charged — or it all rolls
back and none of it happened.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    CancelledBy,
    JobStatus,
    OfferStatus,
    ProviderStatus,
    RequestStatus,
    Role,
)
from app.core.errors import DomainError, ErrorCode
from app.core.job import can_move
from app.models.base import utcnow
from app.models.job import Job, Review
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User
from app.repositories.catalog import SettingsRepository
from app.repositories.jobs import JobRepository
from app.repositories.requests import RequestRepository
from app.schemas.job import NewReviewIn
from app.services import lead_fee


class JobService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.jobs = JobRepository(db)
        self.requests = RequestRepository(db)
        self.settings = SettingsRepository(db)

    # -- reading ---------------------------------------------------------

    def get_own(self, user: User, job_id: int) -> Job:
        """His job, from whichever side he is on.

        Somebody else's is *not found* rather than forbidden, for the same
        reason a request is: the id space is guessable and a 403 confirms one
        exists.
        """
        job = self.jobs.get(job_id)
        if job is None or not self._is_party(user, job):
            raise DomainError(ErrorCode.NOT_FOUND)
        return job

    def list_own(
        self, user: User, *, page: int = 1, per_page: int = 20
    ) -> tuple[list[Job], int]:
        if user.role is Role.PROVIDER:
            profile = self._own_profile(user)
            return self.jobs.list_for_provider(profile.id, page=page, per_page=per_page)
        return self.jobs.list_for_client(user.id, page=page, per_page=per_page)

    # -- the acceptance --------------------------------------------------

    def accept_offer(
        self,
        user: User,
        request_id: int,
        offer_id: int,
        *,
        price_centimes: int | None = None,
        commit: bool = True,
    ) -> Job:
        """One transaction, or none of it.

        Order matters only in that the charge is last: everything before it is
        cheap to undo, and a failure after money moved is the expensive kind.

        `price_centimes` is what the two of them settled on in the chat, which
        is not always what the tradesman first offered — he quoted before he
        had seen the photos. Left out, the offer's own price stands.

        `commit=False` lets the handshake seal the conversation and create the
        job in one transaction rather than two: the conversation service is the
        only caller that needs it, and a job that exists while its conversation
        still says "waiting" is exactly the split this avoids.
        """
        request = self._own_open_request(user, request_id)

        offer = self.db.get(Offer, offer_id)
        if offer is None or offer.request_id != request.id:
            raise DomainError(ErrorCode.NOT_FOUND)

        if offer.status is not OfferStatus.PENDING:
            # Withdrawn between him opening the page and pressing the button.
            raise DomainError(ErrorCode.CONFLICT, reason="offer_not_pending",
                              status=offer.status.value)

        provider = self.db.get(ProviderProfile, offer.provider_id)
        if provider is None or provider.status is not ProviderStatus.APPROVED:
            # Suspended since he offered. Accepting would hand the client
            # somebody the platform has already decided against.
            raise DomainError(ErrorCode.CONFLICT, reason="provider_unavailable")

        now = utcnow()

        offer.status = OfferStatus.ACCEPTED
        offer.responded_at = now
        for other in self.jobs.offers_on(request.id):
            if other.id != offer.id and other.status is OfferStatus.PENDING:
                other.status = OfferStatus.REJECTED
                other.responded_at = now

        request.status = RequestStatus.ASSIGNED

        job = Job(
            request_id=request.id,
            offer_id=offer.id,
            client_id=user.id,
            provider_id=provider.id,
            agreed_price_centimes=(
                offer.price_centimes if price_centimes is None else price_centimes
            ),
            status=JobStatus.ASSIGNED,
        )
        self.db.add(job)
        self.db.flush()

        offer.lead_fee_centimes = self._charge_lead_fee(provider, offer, job, request)

        if not commit:
            return job

        self.db.commit()
        return self.get_own(user, job.id)

    def _charge_lead_fee(
        self, provider: ProviderProfile, offer: Offer, job: Job, request: ServiceRequest
    ) -> int:
        """The fee for this lead, unless it has already been paid.

        A tradesman who handed over his number in the chat has already been
        charged for exactly this lead — `offer.lead_fee_centimes` is set the
        moment that happens. Charging again at the handshake would bill him
        twice for one client, which is the fastest way to teach him never to
        answer a question in the chat again.

        The fee is frozen onto the offer either way: a later change to the
        trade's price must never rewrite what this lead actually cost.
        """
        if offer.lead_fee_centimes is not None:
            return offer.lead_fee_centimes

        taken = lead_fee.charge(
            self.db, provider=provider, offer=offer, request=request, job_id=job.id
        )
        return taken.fee_centimes

    # -- moving it along -------------------------------------------------

    def start(self, user: User, job_id: int) -> Job:
        return self._move(user, job_id, JobStatus.IN_PROGRESS, by_provider=True)

    def finish(self, user: User, job_id: int) -> Job:
        return self._move(user, job_id, JobStatus.DONE, by_provider=True)

    def confirm(self, user: User, job_id: int) -> Job:
        """The client says the work happened. This is what ends a job."""
        return self._move(user, job_id, JobStatus.CONFIRMED, by_provider=False)

    def cancel(self, user: User, job_id: int, *, reason: str | None) -> Job:
        job = self.get_own(user, job_id)
        by_provider = user.role is Role.PROVIDER

        if not can_move(job.status, JobStatus.CANCELLED, by_provider=by_provider):
            raise DomainError(ErrorCode.CONFLICT, status=job.status.value)

        cleaned = " ".join((reason or "").split())
        if by_provider and not cleaned:
            # His cancellation rate is built from these. A blank one is a rate
            # nobody can explain to him later.
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="reason")

        job.status = JobStatus.CANCELLED
        job.cancelled_at = utcnow()
        job.cancelled_by = CancelledBy.PROVIDER if by_provider else CancelledBy.CLIENT
        job.cancel_reason = cleaned or None

        # The request goes back to being a request nobody is doing.
        request = self.jobs.request_for(job)
        request.status = RequestStatus.CANCELLED

        if by_provider:
            provider = self.jobs.provider_for(job)
            provider.jobs_cancelled += 1

        self.db.commit()
        return self.get_own(user, job_id)

    def _move(self, user: User, job_id: int, target: JobStatus, *, by_provider: bool) -> Job:
        job = self.get_own(user, job_id)

        expected = Role.PROVIDER if by_provider else Role.CLIENT
        if user.role is not expected:
            raise DomainError(ErrorCode.FORBIDDEN, role=user.role.value)

        if not can_move(job.status, target, by_provider=by_provider):
            raise DomainError(ErrorCode.CONFLICT, status=job.status.value)

        now = utcnow()
        job.status = target
        if target is JobStatus.IN_PROGRESS:
            job.started_at = now
        elif target is JobStatus.DONE:
            job.finished_at = now
        elif target is JobStatus.CONFIRMED:
            job.confirmed_at = now
            self.jobs.request_for(job).status = RequestStatus.DONE
            # `jobs_done` is a cache of exactly this moment, and P3 sorts on it.
            self.jobs.provider_for(job).jobs_done += 1

        self.db.commit()
        return self.get_own(user, job_id)

    # -- the review ------------------------------------------------------

    def review(self, user: User, job_id: int, payload: NewReviewIn) -> Review:
        """C5. Only the client, only once, and only on work he confirmed."""
        job = self.get_own(user, job_id)

        if user.role is not Role.CLIENT or job.client_id != user.id:
            raise DomainError(ErrorCode.FORBIDDEN, role=user.role.value)

        if job.status is not JobStatus.CONFIRMED:
            raise DomainError(ErrorCode.CONFLICT, status=job.status.value)

        if self.jobs.review_for(job.id) is not None:
            raise DomainError(ErrorCode.CONFLICT, reason="already_reviewed")

        comment = (payload.comment or "").strip()
        review = Review(
            job_id=job.id,
            author_id=user.id,
            provider_id=job.provider_id,
            rating=payload.rating,
            comment=comment or None,
        )
        self.db.add(review)
        self.db.flush()

        self._recompute_rating(job.provider_id)
        self.db.commit()
        return review

    def _recompute_rating(self, provider_id: int) -> None:
        """Derive the card's stars from the reviews behind them.

        Incrementing an average is how a profile ends up claiming 4.9 over a
        page of three-star reviews. It is a cheap query; it stays a query.
        """
        average, count = self.db.execute(
            select(func.avg(Review.rating), func.count())
            .where(Review.provider_id == provider_id, Review.is_hidden.is_(False))
        ).one()

        provider = self.db.get(ProviderProfile, provider_id)
        if provider is not None:
            provider.rating_avg = round(float(average), 2) if count else 0.0
            provider.rating_count = int(count)

    # -- helpers ---------------------------------------------------------

    def _is_party(self, user: User, job: Job) -> bool:
        if user.role is Role.CLIENT:
            return job.client_id == user.id
        if user.role is Role.PROVIDER:
            profile = self.db.execute(
                select(ProviderProfile.id).where(ProviderProfile.user_id == user.id)
            ).scalar_one_or_none()
            return profile is not None and job.provider_id == profile
        return False

    def _own_profile(self, user: User) -> ProviderProfile:
        profile = self.db.execute(
            select(ProviderProfile).where(ProviderProfile.user_id == user.id)
        ).scalar_one_or_none()
        if profile is None:
            raise DomainError(ErrorCode.NOT_FOUND)
        return profile

    def _own_open_request(self, user: User, request_id: int) -> ServiceRequest:
        request = self.requests.get(request_id)
        if request is None or request.client_id != user.id:
            raise DomainError(ErrorCode.NOT_FOUND)
        if request.status is not RequestStatus.OPEN:
            raise DomainError(ErrorCode.CONFLICT, status=request.status.value)
        return request
