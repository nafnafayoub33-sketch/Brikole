"""A2 — an admin judging an application."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ProviderStatus
from app.core.errors import DomainError, ErrorCode
from app.models.base import utcnow
from app.models.provider import ProviderProfile
from app.models.user import User
from app.services.audit import AuditAction, record

MAX_REJECTION_REASON = 500


class ApprovalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def queue(self, *, page: int = 1, per_page: int = 20) -> tuple[list[ProviderProfile], int]:
        """Pending applications, oldest first — a queue, not a feed.

        The person who has waited longest is the one to look at next.
        """
        base = select(ProviderProfile).where(ProviderProfile.status == ProviderStatus.PENDING)
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        rows = list(
            self.db.execute(
                base.options(
                    selectinload(ProviderProfile.user),
                    selectinload(ProviderProfile.city),
                    selectinload(ProviderProfile.trades),
                    selectinload(ProviderProfile.photos),
                )
                .order_by(ProviderProfile.updated_at.asc(), ProviderProfile.id.asc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            .scalars()
            .unique()
        )
        return rows, total

    def get(self, provider_id: int) -> ProviderProfile:
        profile = self.db.execute(
            select(ProviderProfile)
            .where(ProviderProfile.id == provider_id)
            .options(
                selectinload(ProviderProfile.user),
                selectinload(ProviderProfile.city),
                selectinload(ProviderProfile.trades),
                selectinload(ProviderProfile.photos),
            )
        ).scalar_one_or_none()

        if profile is None:
            raise DomainError(ErrorCode.NOT_FOUND)
        return profile

    def approve(self, admin: User, provider_id: int, *, ip: str | None = None) -> ProviderProfile:
        profile = self._claim(provider_id)

        profile.status = ProviderStatus.APPROVED
        profile.rejection_reason = None
        profile.approved_at = utcnow()
        profile.approved_by_id = admin.id

        record(
            self.db,
            actor=admin,
            action=AuditAction.PROVIDER_APPROVED,
            target_type="provider_profile",
            target_id=profile.id,
            before={"status": ProviderStatus.PENDING.value},
            after={"status": ProviderStatus.APPROVED.value},
            ip=ip,
        )
        self.db.commit()
        return self.get(provider_id)

    def reject(
        self, admin: User, provider_id: int, *, reason: str, ip: str | None = None
    ) -> ProviderProfile:
        clean = " ".join(reason.split())
        if not clean or len(clean) > MAX_REJECTION_REASON:
            # The reason is not paperwork: it is the only thing M2 can tell him
            # to fix, so an empty one makes the rejection unanswerable.
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="reason", max=MAX_REJECTION_REASON
            )

        profile = self._claim(provider_id)

        profile.status = ProviderStatus.REJECTED
        profile.rejection_reason = clean
        profile.approved_at = None
        profile.approved_by_id = None

        record(
            self.db,
            actor=admin,
            action=AuditAction.PROVIDER_REJECTED,
            target_type="provider_profile",
            target_id=profile.id,
            before={"status": ProviderStatus.PENDING.value},
            after={"status": ProviderStatus.REJECTED.value},
            note=clean,
            ip=ip,
        )
        self.db.commit()
        return self.get(provider_id)

    def _claim(self, provider_id: int) -> ProviderProfile:
        """Fetch it, and refuse if somebody already decided.

        Two admins open the same queue; one of them acts first. The second must
        be told, not allowed to overwrite a decision that has already been sent
        to the tradesman.
        """
        profile = self.get(provider_id)
        if profile.status is not ProviderStatus.PENDING:
            raise DomainError(ErrorCode.CONFLICT, status=profile.status.value)
        return profile
