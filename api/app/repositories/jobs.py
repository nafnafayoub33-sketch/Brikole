"""Jobs, from either side of one."""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.job import Job, Review
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest


class JobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, job_id: int) -> Job | None:
        return self.db.get(Job, job_id)

    def get_by_request(self, request_id: int) -> Job | None:
        return self.db.execute(
            select(Job).where(Job.request_id == request_id)
        ).scalar_one_or_none()

    def request_for(self, job: Job) -> ServiceRequest:
        request = self.db.execute(
            select(ServiceRequest)
            .where(ServiceRequest.id == job.request_id)
            .options(
                selectinload(ServiceRequest.trade),
                selectinload(ServiceRequest.city),
                selectinload(ServiceRequest.photos),
            )
        ).scalar_one()
        return request

    def provider_for(self, job: Job) -> ProviderProfile:
        return self.db.execute(
            select(ProviderProfile)
            .where(ProviderProfile.id == job.provider_id)
            .options(selectinload(ProviderProfile.user), selectinload(ProviderProfile.city))
        ).scalar_one()

    def list_for_client(
        self, client_id: int, *, page: int = 1, per_page: int = 20
    ) -> tuple[list[Job], int]:
        return self._page(Job.client_id == client_id, page=page, per_page=per_page)

    def list_for_provider(
        self, provider_id: int, *, page: int = 1, per_page: int = 20
    ) -> tuple[list[Job], int]:
        return self._page(Job.provider_id == provider_id, page=page, per_page=per_page)

    def review_for(self, job_id: int) -> Review | None:
        return self.db.execute(
            select(Review).where(Review.job_id == job_id)
        ).scalar_one_or_none()

    def offers_on(self, request_id: int) -> list[Offer]:
        return list(
            self.db.execute(select(Offer).where(Offer.request_id == request_id)).scalars()
        )

    def _page(
        self, condition: ColumnElement[bool], *, page: int, per_page: int
    ) -> tuple[list[Job], int]:
        base = select(Job).where(condition)
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        rows = list(
            self.db.execute(
                # Newest first, with the id breaking ties so pages never overlap.
                base.order_by(Job.created_at.desc(), Job.id.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            ).scalars()
        )
        return rows, total
