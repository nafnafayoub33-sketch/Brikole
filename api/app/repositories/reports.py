"""The report queue, and the content each report points at."""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.core.report import ReportStatus, ReportTarget
from app.models.dispute import Report
from app.models.job import Review
from app.models.provider import ProviderProfile
from app.models.user import User


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, report_id: int) -> Report | None:
        return self.db.get(Report, report_id)

    def queue(
        self, condition: ColumnElement[bool], *, page: int = 1, per_page: int = 20
    ) -> tuple[list[Report], int]:
        base = select(Report).where(condition)
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        rows = list(
            self.db.execute(
                # Oldest first: a report nobody reads is content still on the
                # site, and the one waiting longest has been there longest.
                base.order_by(Report.created_at.asc(), Report.id.asc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            ).scalars()
        )
        return rows, total

    def already_reported_by(
        self, reporter_id: int, target_type: str, target_id: int
    ) -> Report | None:
        """One open report per person per thing. A second is the same complaint."""
        return self.db.execute(
            select(Report).where(
                Report.reporter_id == reporter_id,
                Report.target_type == target_type,
                Report.target_id == target_id,
                Report.status == ReportStatus.OPEN.value,
            )
        ).scalar_one_or_none()

    def open_count_for(self, target_type: str, target_id: int, *, excluding: int) -> int:
        """Other open reports on the same thing. Three complaints about one
        review is a different decision from one."""
        return self.db.execute(
            select(func.count())
            .select_from(Report)
            .where(
                Report.target_type == target_type,
                Report.target_id == target_id,
                Report.status == ReportStatus.OPEN.value,
                Report.id != excluding,
            )
        ).scalar_one()

    def review(self, review_id: int) -> Review | None:
        return self.db.get(Review, review_id)

    def provider(self, provider_id: int) -> ProviderProfile | None:
        return self.db.get(ProviderProfile, provider_id)

    def user(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def target_exists(self, target_type: ReportTarget, target_id: int) -> bool:
        """Nothing is filed against a thing that is not there — an empty row in
        the queue is a moderator's wasted minute."""
        if target_type is ReportTarget.REVIEW:
            return self.review(target_id) is not None
        return self.provider(target_id) is not None
