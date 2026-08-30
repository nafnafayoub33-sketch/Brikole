"""C4, C5 and M7 — the work itself, from both sides of it.

One router, not two: a job is one row read by two people, and splitting it
would mean two copies of the same serialisation drifting apart. The role gate
is on each route rather than the router for the same reason.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.enums import Role
from app.deps import CurrentUser, DbSession, require_roles
from app.models.job import Job, Review
from app.models.offer import Offer
from app.models.user import User
from app.schemas.catalog import TradeOut
from app.schemas.common import Page
from app.schemas.job import CancelJobIn, JobOut, JobPartyOut, JobReviewOut, NewReviewIn
from app.schemas.provider import ProviderCityOut
from app.services.jobs import JobService

router = APIRouter(tags=["jobs"])

AnyParty = Depends(require_roles(Role.CLIENT, Role.PROVIDER))


@router.get("/jobs", response_model=Page[JobOut], dependencies=[AnyParty])
def list_jobs(
    user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[JobOut]:
    """His jobs, from whichever side he is on. C4's list, and M7."""
    service = JobService(db)
    rows, total = service.list_own(user, page=page, per_page=per_page)
    return Page[JobOut](
        items=[_out(service, job, user) for job in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/jobs/{job_id}", response_model=JobOut, dependencies=[AnyParty])
def get_job(job_id: int, user: CurrentUser, db: DbSession) -> JobOut:
    service = JobService(db)
    return _out(service, service.get_own(user, job_id), user)


@router.post(
    "/client/requests/{request_id}/offers/{offer_id}/accept",
    response_model=JobOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.CLIENT))],
)
def accept_offer(
    request_id: int, offer_id: int, user: CurrentUser, db: DbSession
) -> JobOut:
    """C3's one irreversible button. Creates the job the client lands on."""
    service = JobService(db)
    return _out(service, service.accept_offer(user, request_id, offer_id), user)


@router.post(
    "/jobs/{job_id}/start",
    response_model=JobOut,
    dependencies=[Depends(require_roles(Role.PROVIDER))],
)
def start_job(job_id: int, user: CurrentUser, db: DbSession) -> JobOut:
    service = JobService(db)
    return _out(service, service.start(user, job_id), user)


@router.post(
    "/jobs/{job_id}/finish",
    response_model=JobOut,
    dependencies=[Depends(require_roles(Role.PROVIDER))],
)
def finish_job(job_id: int, user: CurrentUser, db: DbSession) -> JobOut:
    service = JobService(db)
    return _out(service, service.finish(user, job_id), user)


@router.post(
    "/jobs/{job_id}/confirm",
    response_model=JobOut,
    dependencies=[Depends(require_roles(Role.CLIENT))],
)
def confirm_job(job_id: int, user: CurrentUser, db: DbSession) -> JobOut:
    service = JobService(db)
    return _out(service, service.confirm(user, job_id), user)


@router.post("/jobs/{job_id}/cancel", response_model=JobOut, dependencies=[AnyParty])
def cancel_job(job_id: int, payload: CancelJobIn, user: CurrentUser, db: DbSession) -> JobOut:
    service = JobService(db)
    return _out(service, service.cancel(user, job_id, reason=payload.reason), user)


@router.post(
    "/jobs/{job_id}/review",
    response_model=JobOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.CLIENT))],
)
def review_job(
    job_id: int, payload: NewReviewIn, user: CurrentUser, db: DbSession
) -> JobOut:
    """C5."""
    service = JobService(db)
    service.review(user, job_id, payload)
    return _out(service, service.get_own(user, job_id), user)


def _out(service: JobService, job: Job, reader: User) -> JobOut:
    request = service.jobs.request_for(job)
    provider = service.jobs.provider_for(job)
    client = service.db.get(User, job.client_id)
    assert client is not None  # the FK says so
    review = service.jobs.review_for(job.id)

    return JobOut(
        id=job.id,
        request_id=job.request_id,
        status=job.status,
        title=request.title,
        description=request.description,
        trade=TradeOut.model_validate(request.trade),
        city=ProviderCityOut.model_validate(request.city),
        address=request.address,
        agreed_price_centimes=job.agreed_price_centimes,
        # What the lead cost is the tradesman's business, not the client's.
        lead_fee_centimes=_fee_for(service, job) if reader.role is Role.PROVIDER else None,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        confirmed_at=job.confirmed_at,
        cancelled_at=job.cancelled_at,
        cancelled_by=job.cancelled_by,
        cancel_reason=job.cancel_reason,
        client=JobPartyOut(
            id=client.id,
            full_name=client.full_name,
            avatar_url=client.avatar_url,
            phone=client.phone,
        ),
        provider=JobPartyOut(
            id=provider.id,
            full_name=provider.user.full_name,
            avatar_url=provider.user.avatar_url,
            phone=provider.user.phone,
            rating_avg=provider.rating_avg,
            rating_count=provider.rating_count,
            jobs_done=provider.jobs_done,
        ),
        review=_review_out(review),
    )


def _fee_for(service: JobService, job: Job) -> int | None:
    offer = service.db.get(Offer, job.offer_id)
    return offer.lead_fee_centimes if offer is not None else None


def _review_out(review: Review | None) -> JobReviewOut | None:
    if review is None:
        return None
    return JobReviewOut(
        id=review.id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        reply=review.reply,
        replied_at=review.replied_at,
    )
