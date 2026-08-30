"""The ledger and the top-up queue."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import TopupStatus
from app.models.credit import CreditAccount, CreditTransaction, TopupRequest
from app.models.provider import ProviderProfile


class CreditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ledger(self, account_id: int, *, limit: int = 50) -> list[CreditTransaction]:
        return list(
            self.db.execute(
                select(CreditTransaction)
                .where(CreditTransaction.account_id == account_id)
                # Newest first, with the id breaking ties: two rows written in
                # the same transaction share a timestamp.
                .order_by(CreditTransaction.created_at.desc(), CreditTransaction.id.desc())
                .limit(limit)
            ).scalars()
        )

    def topups_for(self, provider_id: int, *, limit: int = 20) -> list[TopupRequest]:
        return list(
            self.db.execute(
                select(TopupRequest)
                .where(TopupRequest.provider_id == provider_id)
                .order_by(TopupRequest.created_at.desc(), TopupRequest.id.desc())
                .limit(limit)
            ).scalars()
        )

    def has_pending(self, provider_id: int) -> bool:
        return (
            self.db.execute(
                select(func.count())
                .select_from(TopupRequest)
                .where(
                    TopupRequest.provider_id == provider_id,
                    TopupRequest.status == TopupStatus.PENDING,
                )
            ).scalar_one()
            > 0
        )

    def queue(
        self, *, page: int = 1, per_page: int = 20
    ) -> tuple[list[tuple[TopupRequest, ProviderProfile, CreditAccount | None]], int]:
        """A5's queue, oldest first — the person who has waited longest is next."""
        base = select(TopupRequest).where(TopupRequest.status == TopupStatus.PENDING)
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        rows = self.db.execute(
            select(TopupRequest, ProviderProfile, CreditAccount)
            .join(ProviderProfile, ProviderProfile.id == TopupRequest.provider_id)
            .join(CreditAccount, CreditAccount.provider_id == ProviderProfile.id, isouter=True)
            .where(TopupRequest.status == TopupStatus.PENDING)
            .order_by(TopupRequest.created_at.asc(), TopupRequest.id.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()

        return [(topup, profile, account) for topup, profile, account in rows], total

    def account_for(self, provider_id: int) -> CreditAccount | None:
        return self.db.execute(
            select(CreditAccount).where(CreditAccount.provider_id == provider_id)
        ).scalar_one_or_none()
