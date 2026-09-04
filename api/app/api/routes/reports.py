"""Filing a report, and D3 — the moderator's queue of them."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.enums import Role
from app.core.report import ReportOutcome, ReportReason, ReportTarget
from app.deps import CurrentUser, DbSession, require_roles
from app.models.dispute import Report
from app.schemas.common import Page
from app.schemas.report import (
    HandleReportIn,
    NewReportIn,
    ReportedContentOut,
    ReportOut,
)
from app.services.reports import ReportService

router = APIRouter(tags=["reports"])

Staff = Depends(require_roles(Role.MODERATOR, Role.ADMIN))


@router.post(
    "/reports",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.CLIENT, Role.PROVIDER))],
)
def file_report(payload: NewReportIn, user: CurrentUser, db: DbSession) -> ReportOut:
    """Anyone with an account can flag a profile or a review."""
    service = ReportService(db)
    return _out(service, service.file(user, payload))


@router.get("/mod/reports", response_model=Page[ReportOut], dependencies=[Staff])
def report_queue(
    user: CurrentUser,
    db: DbSession,
    tab: Literal["open", "handled"] = "open",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[ReportOut]:
    """D3. Oldest first — a report nobody reads is content still on the site."""
    service = ReportService(db)
    rows, total = service.queue(user, tab=tab, page=page, per_page=per_page)
    return Page[ReportOut](
        items=[_out(service, report) for report in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/mod/reports/{report_id}/handle", response_model=ReportOut, dependencies=[Staff]
)
def handle_report(
    report_id: int,
    payload: HandleReportIn,
    user: CurrentUser,
    db: DbSession,
    request: Request,
) -> ReportOut:
    service = ReportService(db)
    handled = service.handle(user, report_id, payload, ip=_ip(request))
    return _out(service, handled)


def _out(service: ReportService, report: Report) -> ReportOut:
    reporter = service.repo.user(report.reporter_id) if report.reporter_id else None
    handler = service.repo.user(report.handled_by_id) if report.handled_by_id else None

    return ReportOut(
        id=report.id,
        target_type=ReportTarget(report.target_type),
        target_id=report.target_id,
        reason=ReportReason(report.reason),
        description=report.description,
        status=report.status,
        created_at=report.created_at,
        reporter_id=report.reporter_id,
        reporter_name=reporter.full_name if reporter else None,
        handled_by_name=handler.full_name if handler else None,
        handled_at=report.handled_at,
        outcome=ReportOutcome(report.outcome) if report.outcome else None,
        content=_content(service, report),
        also_reported=service.repo.open_count_for(
            report.target_type, report.target_id, excluding=report.id
        ),
    )


def _content(service: ReportService, report: Report) -> ReportedContentOut | None:
    """The thing complained about, quoted — a moderator judges the content, not
    the complaint about it."""
    kind = ReportTarget(report.target_type)

    if kind is ReportTarget.REVIEW:
        review = service.repo.review(report.target_id)
        if review is None:
            return None
        author = service.repo.user(review.author_id)
        return ReportedContentOut(
            kind=kind,
            title=author.full_name if author else "—",
            body=review.comment or "",
            rating=review.rating,
            is_hidden=review.is_hidden,
            provider_id=review.provider_id,
            owner_id=review.author_id,
            owner_name=author.full_name if author else None,
        )

    profile = service.repo.provider(report.target_id)
    if profile is None:
        return None
    return ReportedContentOut(
        kind=kind,
        title=profile.user.full_name,
        body=profile.headline or profile.bio or "",
        provider_id=profile.id,
        owner_id=profile.user_id,
        owner_name=profile.user.full_name,
    )


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None
