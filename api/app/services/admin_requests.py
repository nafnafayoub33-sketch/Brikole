"""A4 — the support browser.

Every question this screen answers has the same shape: somebody is on the
phone about a request, find it and say what happened to it. So it is read-only
apart from one action, and that action is the one support actually needs — a
client who posted by mistake, or a request that should never have been posted.

**Cancelling stops at `open`, deliberately.** Once a request is assigned there
is a tradesman who may already be on his way, a fee already charged, and
possibly a refund owed. That is a dispute, and disputes already have the
machinery for it. A second cancel path here would be a second set of rules
about the same moment, and the two would drift.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import RequestStatus, Role
from app.core.errors import DomainError, ErrorCode
from app.models.base import utcnow
from app.models.dispute import Dispute
from app.models.job import Job
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User
from app.repositories.requests import RequestRepository
from app.services import audit
from app.services.audit import AuditAction

#: What a request cancelled from here is recorded as. Free text on the model,
#: a constant here so the audit rows are searchable.
CANCELLED_BY_ADMIN = "cancelled_by_admin"


@dataclass(frozen=True, slots=True)
class RequestDetail:
    """One request and everything hanging off it, in one read.

    Assembled here rather than fetched piecemeal by the route: the screen shows
    all of it at once, and a support call is not the moment to discover that
    the job loaded and the dispute did not.
    """

    request: ServiceRequest
    client: User
    offers: list[tuple[Offer, ProviderProfile, User]]
    job: Job | None
    provider: tuple[ProviderProfile, User] | None
    dispute: Dispute | None


class AdminRequestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.requests = RequestRepository(db)

    def page(
        self,
        *,
        query: str | None = None,
        status: RequestStatus | None = None,
        city_id: int | None = None,
        trade_id: int | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> tuple[list[tuple[ServiceRequest, User]], int]:
        return self.requests.page(
            query=query,
            status=status,
            city_id=city_id,
            trade_id=trade_id,
            page=page,
            per_page=per_page,
        )

    def detail(self, request_id: int) -> RequestDetail:
        request = self.requests.get(request_id)
        if request is None:
            raise DomainError(ErrorCode.NOT_FOUND)

        client = self.db.get(User, request.client_id)
        if client is None:
            # The FK is `CASCADE`, so a request without its client is a row
            # that should not exist rather than a case to render around.
            raise DomainError(ErrorCode.NOT_FOUND)

        offers = [
            (offer, offer.provider, offer.provider.user)
            for offer in self.requests.list_offers(request_id)
        ]

        job = self.db.execute(
            select(Job).where(Job.request_id == request_id)
        ).scalar_one_or_none()

        provider = None
        dispute = None
        if job is not None:
            profile = self.db.get(ProviderProfile, job.provider_id)
            if profile is not None:
                provider = (profile, profile.user)
            dispute = self.db.execute(
                select(Dispute).where(Dispute.job_id == job.id)
            ).scalar_one_or_none()

        return RequestDetail(
            request=request,
            client=client,
            offers=offers,
            job=job,
            provider=provider,
            dispute=dispute,
        )

    def cancel(
        self, admin: User, request_id: int, *, reason: str, ip: str | None = None
    ) -> RequestDetail:
        """Close an open request on somebody's behalf, on the record."""
        if admin.role is not Role.ADMIN:
            raise DomainError(ErrorCode.FORBIDDEN, role=admin.role.value)

        request = self.requests.get(request_id)
        if request is None:
            raise DomainError(ErrorCode.NOT_FOUND)

        if request.status is not RequestStatus.OPEN:
            raise DomainError(ErrorCode.CONFLICT, status=request.status.value)

        cleaned = " ".join(reason.split())
        if not cleaned:
            # Somebody will read this in three months and need to know why a
            # client's request vanished. "Cancelled by an admin" is not a why.
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="reason")

        before = request.status.value
        request.status = RequestStatus.CANCELLED
        request.cancelled_at = utcnow()
        request.cancel_reason = cleaned

        audit.record(
            self.db,
            actor=admin,
            action=AuditAction.REQUEST_CANCELLED,
            target_type="service_request",
            target_id=request.id,
            before={"status": before},
            after={"status": request.status.value, "reason": cleaned},
            note=CANCELLED_BY_ADMIN,
            ip=ip,
        )

        self.db.commit()
        return self.detail(request_id)
