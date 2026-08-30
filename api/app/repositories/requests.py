"""A client's own requests, and the offers they have drawn."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import RequestStatus
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest

#: Everything C2 and C3 render off a request, loaded in one round trip each
#: rather than one per row.
_FULL = (
    selectinload(ServiceRequest.photos),
    selectinload(ServiceRequest.trade),
    selectinload(ServiceRequest.city),
)


class RequestRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, request_id: int) -> ServiceRequest | None:
        return self.db.execute(
            select(ServiceRequest).where(ServiceRequest.id == request_id).options(*_FULL)
        ).scalar_one_or_none()

    def list_for_client(
        self, client_id: int, *, page: int = 1, per_page: int = 20
    ) -> tuple[list[ServiceRequest], int]:
        base = select(ServiceRequest).where(ServiceRequest.client_id == client_id)
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        rows = list(
            self.db.execute(
                base.options(*_FULL)
                # Newest first, with the id breaking ties so pages never overlap.
                .order_by(ServiceRequest.created_at.desc(), ServiceRequest.id.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            .scalars()
            .unique()
        )
        return rows, total

    def count_open_for_client(self, client_id: int) -> int:
        return self.db.execute(
            select(func.count())
            .select_from(ServiceRequest)
            .where(
                ServiceRequest.client_id == client_id,
                ServiceRequest.status == RequestStatus.OPEN,
            )
        ).scalar_one()

    def list_offers(self, request_id: int) -> list[Offer]:
        """Newest first, with the tradesman behind each one."""
        return list(
            self.db.execute(
                select(Offer)
                .where(Offer.request_id == request_id)
                .options(
                    selectinload(Offer.provider).selectinload(ProviderProfile.user),
                    selectinload(Offer.provider).selectinload(ProviderProfile.city),
                )
                .order_by(Offer.created_at.desc(), Offer.id.desc())
            )
            .scalars()
            .unique()
        )
