"""The tradesman's side: the feed he answers, and the offers he has sent."""

from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import RequestStatus
from app.models.credit import CreditAccount
from app.models.job import Job
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest


class OfferRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def credit_account(self, provider_id: int) -> CreditAccount | None:
        return self.db.execute(
            select(CreditAccount).where(CreditAccount.provider_id == provider_id)
        ).scalar_one_or_none()

    def feed(
        self,
        provider: ProviderProfile,
        *,
        trade_id: int | None = None,
        urgency: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ServiceRequest], int]:
        """Open requests he could take.

        Matched on trade and city. The spec says "inside his radius", and
        `radius_km` is stored, but most requests carry no coordinates — C1 does
        not ask for a pin. Matching on the city is the honest version of the
        same idea until there is something to measure a distance against, and
        it is what keeps a plumber in Meknès out of a Rabat homeowner's feed.
        """
        trade_ids = [trade.id for trade in provider.trades]
        if not trade_ids:
            return [], 0

        stmt = select(ServiceRequest).where(
            ServiceRequest.status == RequestStatus.OPEN,
            ServiceRequest.city_id == provider.city_id,
            ServiceRequest.trade_id.in_(trade_ids),
        )
        if trade_id is not None:
            stmt = stmt.where(ServiceRequest.trade_id == trade_id)
        if urgency is not None:
            stmt = stmt.where(ServiceRequest.urgency == urgency)

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = list(
            self.db.execute(
                self._loaded(stmt)
                # Newest first, with the id breaking ties so pages never overlap.
                .order_by(ServiceRequest.created_at.desc(), ServiceRequest.id.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            .scalars()
            .unique()
        )
        return rows, total

    def open_request(self, request_id: int) -> ServiceRequest | None:
        return self.db.execute(
            self._loaded(select(ServiceRequest).where(ServiceRequest.id == request_id))
        ).scalar_one_or_none()

    def his_offer_on(self, provider_id: int, request_id: int) -> Offer | None:
        return self.db.execute(
            select(Offer).where(
                Offer.provider_id == provider_id, Offer.request_id == request_id
            )
        ).scalar_one_or_none()

    def his_offers_on(self, provider_id: int, request_ids: list[int]) -> dict[int, Offer]:
        """One query for a page of feed rows, rather than one per row."""
        if not request_ids:
            return {}
        rows = self.db.execute(
            select(Offer).where(
                Offer.provider_id == provider_id, Offer.request_id.in_(request_ids)
            )
        ).scalars()
        return {offer.request_id: offer for offer in rows}

    def list_his(
        self, provider_id: int, *, page: int = 1, per_page: int = 20
    ) -> tuple[list[Offer], int]:
        stmt = select(Offer).where(Offer.provider_id == provider_id)
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = list(
            self.db.execute(
                stmt.options(
                    selectinload(Offer.request).selectinload(ServiceRequest.trade),
                    selectinload(Offer.request).selectinload(ServiceRequest.city),
                )
                .order_by(Offer.created_at.desc(), Offer.id.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            .scalars()
            .unique()
        )
        return rows, total

    def jobs_for_offers(self, offer_ids: list[int]) -> dict[int, int]:
        """Offer id → job id, for the accepted ones. One query, not N."""
        if not offer_ids:
            return {}
        rows = self.db.execute(
            select(Job.offer_id, Job.id).where(Job.offer_id.in_(offer_ids))
        ).all()
        return {int(offer_id): int(job_id) for offer_id, job_id in rows}

    @staticmethod
    def _loaded(stmt: Select[tuple[ServiceRequest]]) -> Select[tuple[ServiceRequest]]:
        return stmt.options(
            selectinload(ServiceRequest.trade),
            selectinload(ServiceRequest.city),
            selectinload(ServiceRequest.photos),
        )
