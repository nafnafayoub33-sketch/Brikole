"""The tradesman's own area. M1 and M2 live here."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.routes.providers import to_review
from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode
from app.deps import CurrentUser, DbSession, require_roles
from app.models.provider import ProviderProfile
from app.repositories.reviews import ReviewRepository
from app.schemas.catalog import TradeOut
from app.schemas.common import Page
from app.schemas.pro import (
    AvailabilityIn,
    MyProviderProfileOut,
    MyReviewsSummaryOut,
    PhotoIn,
    ProfileEditIn,
    ProviderApplicationIn,
    ReplyIn,
)
from app.schemas.provider import ProviderCityOut, ProviderPhotoOut, ReviewOut
from app.services.pro_reviews import ProviderReviewsService
from app.services.provider import ProviderProfileService, availability_of

router = APIRouter(
    prefix="/pro",
    tags=["pro"],
    dependencies=[Depends(require_roles(Role.PROVIDER))],
)


@router.get("/profile", response_model=MyProviderProfileOut)
def get_my_profile(user: CurrentUser, db: DbSession) -> MyProviderProfileOut:
    """His own application, at whatever status.

    404 while he has not filled one in is what routes him to M1 — the absence
    of a profile is the signal, not a flag on the account.
    """
    profile = ProviderProfileService(db).get_own(user)
    if profile is None:
        raise DomainError(ErrorCode.NOT_FOUND)
    return _mine(profile, db)


@router.post("/profile", response_model=MyProviderProfileOut, status_code=status.HTTP_201_CREATED)
def submit_my_profile(
    payload: ProviderApplicationIn, user: CurrentUser, db: DbSession
) -> MyProviderProfileOut:
    """M1, and the resubmission from M2 after a rejection."""
    profile = ProviderProfileService(db).submit(user, payload)
    return _mine(profile, db)


@router.patch("/profile", response_model=MyProviderProfileOut)
def edit_my_profile(
    payload: ProfileEditIn, user: CurrentUser, db: DbSession
) -> MyProviderProfileOut:
    """M8. Everything a client reads about him, and nothing that decided
    whether he got here: not the CIN, not the status.

    Changing his trades or his city moves his feed on the next request — the
    feed is a query, not a stored list, so there is nothing to rebuild.
    """
    profile = ProviderProfileService(db).edit(user, payload)
    return _mine(profile, db)


@router.patch("/profile/availability", response_model=MyProviderProfileOut)
def set_availability(
    payload: AvailabilityIn, user: CurrentUser, db: DbSession
) -> MyProviderProfileOut:
    """Taking work, or away. A pause takes him out of search and leaves his
    own feed alone — see `core/availability.py`."""
    profile = ProviderProfileService(db).set_availability(user, payload)
    return _mine(profile, db)


@router.post(
    "/profile/photos",
    response_model=MyProviderProfileOut,
    status_code=status.HTTP_201_CREATED,
)
def add_photo(payload: PhotoIn, user: CurrentUser, db: DbSession) -> MyProviderProfileOut:
    profile = ProviderProfileService(db).add_photo(user, payload.path)
    return _mine(profile, db)


@router.delete("/profile/photos/{photo_id}", response_model=MyProviderProfileOut)
def remove_photo(photo_id: int, user: CurrentUser, db: DbSession) -> MyProviderProfileOut:
    profile = ProviderProfileService(db).remove_photo(user, photo_id)
    return _mine(profile, db)


# -- M10 ---------------------------------------------------------------------


@router.get("/reviews/summary", response_model=MyReviewsSummaryOut)
def my_reviews_summary(user: CurrentUser, db: DbSession) -> MyReviewsSummaryOut:
    """Declared before `/reviews` so `summary` is never read as a page number.

    Its own endpoint rather than a field on every page: the numbers do not
    change as he pages, so this way they are fetched once and stay put while he
    reads.
    """
    profile, breakdown, unanswered = ProviderReviewsService(db).summary(user)
    return MyReviewsSummaryOut(
        rating_avg=profile.rating_avg,
        rating_count=profile.rating_count,
        breakdown=breakdown,
        unanswered=unanswered,
    )


@router.get("/reviews", response_model=Page[ReviewOut])
def my_reviews(
    user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 10,
) -> Page[ReviewOut]:
    """The same shape P3 shows the public, because it is the same set."""
    rows, total = ProviderReviewsService(db).page(user, page=page, per_page=per_page)
    return Page[ReviewOut](
        items=[to_review(row) for row in rows], total=total, page=page, per_page=per_page
    )


@router.post("/reviews/{review_id}/reply", response_model=ReviewOut)
def reply_to_review(
    review_id: int, payload: ReplyIn, user: CurrentUser, db: DbSession
) -> ReviewOut:
    """His one answer. A second attempt is a 409, not a rewrite."""
    return to_review(ProviderReviewsService(db).reply(user, review_id, payload.reply))


def _mine(profile: ProviderProfile, db: DbSession) -> MyProviderProfileOut:
    return MyProviderProfileOut(
        id=profile.id,
        full_name=profile.user.full_name,
        avatar_url=profile.user.avatar_url,
        headline=profile.headline,
        status=profile.status,
        city=ProviderCityOut.model_validate(profile.city),
        trades=[TradeOut.model_validate(trade) for trade in profile.trades],
        rating_avg=profile.rating_avg,
        rating_count=profile.rating_count,
        jobs_done=profile.jobs_done,
        years_experience=profile.years_experience,
        starting_price_centimes=profile.starting_price_centimes,
        bio=profile.bio,
        radius_km=profile.radius_km,
        member_since=profile.created_at,
        rating_breakdown=ReviewRepository(db).breakdown(profile.id),
        photos=[ProviderPhotoOut.model_validate(photo) for photo in profile.photos],
        rejection_reason=profile.rejection_reason,
        id_card_path=profile.id_card_url,
        availability=availability_of(profile),
    )
