"""The tradesman's own area. M1 and M2 live here."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode
from app.deps import CurrentUser, DbSession, require_roles
from app.repositories.reviews import ReviewRepository
from app.schemas.catalog import TradeOut
from app.schemas.pro import MyProviderProfileOut, ProviderApplicationIn
from app.schemas.provider import ProviderCityOut, ProviderPhotoOut
from app.services.provider import ProviderProfileService

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


def _mine(profile: object, db: DbSession) -> MyProviderProfileOut:
    from app.models.provider import ProviderProfile

    assert isinstance(profile, ProviderProfile)
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
    )
