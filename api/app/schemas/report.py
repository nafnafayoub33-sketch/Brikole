"""Reports, as a visitor files them and a moderator clears them (D3)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.report import MAX_DESCRIPTION, ReportOutcome, ReportReason, ReportTarget
from app.schemas.common import ApiModel


class ReportedContentOut(ApiModel):
    """The thing complained about, quoted so a moderator judges the content
    rather than the complaint about it."""

    kind: ReportTarget
    #: The tradesman's name, for a profile; the review's author, for a review.
    title: str
    #: The review's text. Empty for a profile.
    body: str
    rating: int | None = None
    #: Whether it is already hidden — a second report on the same review is
    #: common, and the moderator should not hide it twice.
    is_hidden: bool = False
    #: Where to go and look at it.
    provider_id: int | None = None
    #: The account a suspension would land on, when the target has one.
    owner_id: int | None = None
    owner_name: str | None = None


class ReportOut(ApiModel):
    id: int
    target_type: ReportTarget
    target_id: int
    reason: ReportReason
    description: str | None
    status: str
    created_at: datetime

    #: Null when the platform filed it rather than a person. The screen says
    #: so in words: "flagged automatically" carries different weight from an
    #: accusation with a name on it.
    reporter_id: int | None
    reporter_name: str | None

    handled_by_name: str | None
    handled_at: datetime | None
    outcome: ReportOutcome | None

    content: ReportedContentOut | None
    #: How many other open reports name the same thing. Three complaints about
    #: one review is a different decision from one.
    also_reported: int = 0


class NewReportIn(BaseModel):
    target_type: ReportTarget
    target_id: int = Field(gt=0)
    reason: ReportReason
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION)


class HandleReportIn(BaseModel):
    outcome: ReportOutcome
    #: What the moderator decided and why. Read by the next moderator to see
    #: this person, so it is not optional.
    note: str = Field(min_length=1, max_length=1000)
