"""C8, D1 and D2 — opening a dispute, the queue, and settling one."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.dispute import is_stale
from app.core.enums import Role
from app.deps import CurrentUser, DbSession, require_roles
from app.models.base import utcnow
from app.models.dispute import Dispute
from app.models.offer import Offer
from app.models.user import User
from app.schemas.common import Page
from app.schemas.dispute import (
    DisputeJobOut,
    DisputeMessageIn,
    DisputeMessageOut,
    DisputeOut,
    DisputePartyOut,
    DisputeRowOut,
    NewDisputeIn,
    ResolveDisputeIn,
)
from app.services.disputes import DisputeService

router = APIRouter(tags=["disputes"])

Staff = Depends(require_roles(Role.MODERATOR, Role.ADMIN))
Party = Depends(require_roles(Role.CLIENT, Role.PROVIDER))


@router.post(
    "/jobs/{job_id}/dispute",
    response_model=DisputeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Party],
)
def open_dispute(
    job_id: int, payload: NewDisputeIn, user: CurrentUser, db: DbSession
) -> DisputeOut:
    """C8."""
    service = DisputeService(db)
    return _out(service, service.open(user, job_id, payload), user)


@router.get("/disputes", response_model=Page[DisputeRowOut], dependencies=[Party])
def my_disputes(
    user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[DisputeRowOut]:
    service = DisputeService(db)
    rows, total = service.mine(user, page=page, per_page=per_page)
    return Page[DisputeRowOut](
        items=[_row(service, dispute) for dispute in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/mod/disputes", response_model=Page[DisputeRowOut], dependencies=[Staff])
def dispute_queue(
    user: CurrentUser,
    db: DbSession,
    tab: Literal["open", "mine", "resolved"] = "open",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[DisputeRowOut]:
    """D1. Oldest first — two people are waiting on each row."""
    service = DisputeService(db)
    rows, total = service.queue(user, tab=tab, page=page, per_page=per_page)
    return Page[DisputeRowOut](
        items=[_row(service, dispute) for dispute in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/disputes/{dispute_id}", response_model=DisputeOut)
def get_dispute(dispute_id: int, user: CurrentUser, db: DbSession) -> DisputeOut:
    """D2 for staff; the same case, minus the internal notes, for a party."""
    service = DisputeService(db)
    return _out(service, service.get(user, dispute_id), user)


@router.post("/mod/disputes/{dispute_id}/claim", response_model=DisputeOut, dependencies=[Staff])
def claim_dispute(dispute_id: int, user: CurrentUser, db: DbSession) -> DisputeOut:
    service = DisputeService(db)
    return _out(service, service.claim(user, dispute_id), user)


@router.post(
    "/disputes/{dispute_id}/messages",
    response_model=DisputeOut,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    dispute_id: int, payload: DisputeMessageIn, user: CurrentUser, db: DbSession
) -> DisputeOut:
    service = DisputeService(db)
    service.add_message(user, dispute_id, payload)
    return _out(service, service.get(user, dispute_id), user)


@router.post(
    "/mod/disputes/{dispute_id}/resolve", response_model=DisputeOut, dependencies=[Staff]
)
def resolve_dispute(
    dispute_id: int,
    payload: ResolveDisputeIn,
    user: CurrentUser,
    db: DbSession,
    request: Request,
) -> DisputeOut:
    service = DisputeService(db)
    resolved = service.resolve(user, dispute_id, payload, ip=_ip(request))
    return _out(service, resolved, user)


def _row(service: DisputeService, dispute: Dispute) -> DisputeRowOut:
    job = service.repo.job_for(dispute)
    request = service.jobs.request_for(job)
    opener = service.repo.user(dispute.opened_by_id)
    against = service.repo.user(dispute.against_id)

    return DisputeRowOut(
        id=dispute.id,
        reason=dispute.reason,
        status=dispute.status,
        created_at=dispute.created_at,
        job_title=request.title,
        opened_by_name=opener.full_name if opener else "—",
        against_name=against.full_name if against else "—",
        claimed_by_id=dispute.claimed_by_id,
        is_stale=dispute.claimed_by_id is None and is_stale(dispute.created_at, utcnow()),
    )


def _out(service: DisputeService, dispute: Dispute, reader: User) -> DisputeOut:
    job = service.repo.job_for(dispute)
    request = service.jobs.request_for(job)
    offer = service.db.get(Offer, job.offer_id)

    opener = service.repo.user(dispute.opened_by_id)
    against = service.repo.user(dispute.against_id)
    claimed_by = (
        service.repo.user(dispute.claimed_by_id) if dispute.claimed_by_id else None
    )

    messages = service.visible_messages(reader, dispute)
    names = {
        user.id: user.full_name
        for user in (opener, against, claimed_by)
        if user is not None
    }

    return DisputeOut(
        id=dispute.id,
        reason=dispute.reason,
        description=dispute.description,
        status=dispute.status,
        created_at=dispute.created_at,
        job=DisputeJobOut(
            id=job.id,
            title=request.title,
            status=job.status.value,
            agreed_price_centimes=job.agreed_price_centimes,
            finished_at=job.finished_at,
            # The one money figure a moderator sees, because he can refund it.
            lead_fee_centimes=offer.lead_fee_centimes if offer else None,
        ),
        opened_by=_party(service, opener),
        against=_party(service, against),
        claimed_by_id=dispute.claimed_by_id,
        claimed_by_name=claimed_by.full_name if claimed_by else None,
        claimed_at=dispute.claimed_at,
        verdict=dispute.verdict,
        resolution_note=dispute.resolution_note,
        lead_fee_refunded=dispute.lead_fee_refunded,
        resolved_at=dispute.resolved_at,
        evidence=[
            message.attachment_url
            for message in dispute.messages
            if message.attachment_url
        ],
        messages=[
            DisputeMessageOut(
                id=message.id,
                author_id=message.author_id,
                author_name=names.get(message.author_id, "—"),
                body=message.body,
                attachment_url=message.attachment_url,
                is_internal=message.is_internal,
                created_at=message.created_at,
            )
            for message in messages
        ],
        is_stale=dispute.claimed_by_id is None and is_stale(dispute.created_at, utcnow()),
    )


def _party(service: DisputeService, user: User | None) -> DisputePartyOut:
    if user is None:
        return DisputePartyOut(id=0, full_name="—", role="deleted")

    profile = service.repo.profile_for_user(user.id)
    return DisputePartyOut(
        id=user.id,
        full_name=user.full_name,
        role=user.role.value,
        provider_id=profile.id if profile else None,
        rating_avg=profile.rating_avg if profile else None,
        rating_count=profile.rating_count if profile else None,
        jobs_done=profile.jobs_done if profile else None,
        disputes_lost=service.repo.disputes_lost(user.id, user.role),
    )


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None
