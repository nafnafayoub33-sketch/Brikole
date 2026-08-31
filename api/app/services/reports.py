"""Filing a report, and D3 — clearing the queue of them.

The ceiling is deliberate: dismiss, hide the content, warn, suspend 48 hours.
A moderator cannot close an account for good, and this service has no branch
that would let him. That is the same line drawn in `core/permissions.py`, kept
here where the action actually happens.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.enums import Role, UserStatus
from app.core.errors import DomainError, ErrorCode
from app.core.report import (
    SUSPENSION_HOURS,
    ReportOutcome,
    ReportStatus,
    ReportTarget,
    can_hide,
    validate_report,
)
from app.models.base import utcnow
from app.models.dispute import Report
from app.models.user import User
from app.repositories.reports import ReportRepository
from app.schemas.report import HandleReportIn, NewReportIn
from app.services import audit
from app.services.audit import AuditAction

STAFF = frozenset({Role.MODERATOR, Role.ADMIN})


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ReportRepository(db)

    # -- filing one ------------------------------------------------------

    def file(self, user: User, payload: NewReportIn) -> Report:
        try:
            new = validate_report(
                target_type=payload.target_type.value,
                target_id=payload.target_id,
                reason=payload.reason.value,
                description=payload.description,
            )
        except ValueError as error:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field=str(error)) from error

        if not self.repo.target_exists(new.target_type, new.target_id):
            raise DomainError(ErrorCode.NOT_FOUND)

        self._refuse_self_report(user, new.target_type, new.target_id)

        if self.repo.already_reported_by(
            user.id, new.target_type.value, new.target_id
        ) is not None:
            raise DomainError(ErrorCode.CONFLICT, reason="already_reported")

        report = Report(
            reporter_id=user.id,
            target_type=new.target_type.value,
            target_id=new.target_id,
            reason=new.reason.value,
            description=new.description or None,
            status=ReportStatus.OPEN.value,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def _refuse_self_report(
        self, user: User, target_type: ReportTarget, target_id: int
    ) -> None:
        """Reporting your own profile or a review you wrote is not moderation,
        it is a way to make a moderator read your complaint."""
        owner = self._owner_of(target_type, target_id)
        if owner is not None and owner.id == user.id:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="target_id")

    # -- D3 --------------------------------------------------------------

    def queue(
        self, user: User, *, tab: str = "open", page: int = 1, per_page: int = 20
    ) -> tuple[list[Report], int]:
        self._require_staff(user)
        condition = (
            Report.status == ReportStatus.HANDLED.value
            if tab == "handled"
            else Report.status == ReportStatus.OPEN.value
        )
        return self.repo.queue(condition, page=page, per_page=per_page)

    def get(self, user: User, report_id: int) -> Report:
        self._require_staff(user)
        report = self.repo.get(report_id)
        if report is None:
            raise DomainError(ErrorCode.NOT_FOUND)
        return report

    def handle(
        self, user: User, report_id: int, payload: HandleReportIn, *, ip: str | None = None
    ) -> Report:
        self._require_staff(user)
        report = self.get(user, report_id)

        if report.status == ReportStatus.HANDLED.value:
            # Two moderators on one queue. 409 beats hiding a review twice or
            # stacking two suspensions on one person.
            raise DomainError(ErrorCode.CONFLICT, status=report.status)

        note = " ".join(payload.note.split())
        if not note:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="note")

        target_type = ReportTarget(report.target_type)

        if payload.outcome is ReportOutcome.CONTENT_HIDDEN:
            if not can_hide(target_type):
                # Taking a tradesman off the market is a suspension. Calling it
                # "hidden" would leave nothing on the record saying why he went.
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED,
                    field="outcome",
                    target_type=report.target_type,
                )
            review = self.repo.review(report.target_id)
            if review is None:
                raise DomainError(ErrorCode.NOT_FOUND)
            review.is_hidden = True

        owner = self._owner_of(target_type, report.target_id)

        if payload.outcome is ReportOutcome.SUSPENDED:
            if owner is None:
                raise DomainError(ErrorCode.NOT_FOUND)
            owner.status = UserStatus.SUSPENDED
            # Always temporary from here. Permanence is an admin's decision.
            owner.suspended_until = utcnow() + timedelta(hours=SUSPENSION_HOURS)
            owner.suspension_reason = note

        report.status = ReportStatus.HANDLED.value
        report.outcome = payload.outcome.value
        report.handled_by_id = user.id
        report.handled_at = utcnow()

        audit.record(
            self.db,
            actor=user,
            action=AuditAction.REPORT_HANDLED,
            target_type=report.target_type,
            target_id=report.target_id,
            before={"status": ReportStatus.OPEN.value},
            after={"status": ReportStatus.HANDLED.value, "outcome": payload.outcome.value},
            note=note,
            ip=ip,
        )

        self.db.commit()
        self.db.refresh(report)
        return report

    # -- helpers ---------------------------------------------------------

    def _owner_of(self, target_type: ReportTarget, target_id: int) -> User | None:
        """Whose account a suspension would land on."""
        if target_type is ReportTarget.REVIEW:
            review = self.repo.review(target_id)
            return self.repo.user(review.author_id) if review else None

        profile = self.repo.provider(target_id)
        return self.repo.user(profile.user_id) if profile else None

    def _require_staff(self, user: User) -> None:
        if user.role not in STAFF:
            raise DomainError(ErrorCode.FORBIDDEN, role=user.role.value)
