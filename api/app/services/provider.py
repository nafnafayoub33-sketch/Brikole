"""Creating and correcting a tradesman's application."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.availability import is_available, validate_pause
from app.core.enums import ProviderStatus, Role
from app.core.errors import DomainError, ErrorCode
from app.core.policy import FREE_LEADS_NEW_PROVIDER, MAX_PORTFOLIO_PHOTOS
from app.core.provider_application import ProviderApplication, validate_application
from app.models.base import utcnow
from app.models.catalog import City, Trade
from app.models.credit import CreditAccount
from app.models.provider import ProviderPhoto, ProviderProfile
from app.models.user import User
from app.schemas.availability import AvailabilityOut
from app.schemas.pro import AvailabilityIn, ProfileEditIn, ProviderApplicationIn


def availability_of(profile: ProviderProfile) -> AvailabilityOut:
    """What he typed, and whether clients can find him because of it.

    `is_available` folds in the status on purpose: for a pending applicant the
    switch says "taking work" and the honest answer is still no, because
    nobody can reach him yet. One field, one meaning — "clients can find me" —
    so the screen never has to combine two of them and get it wrong.
    """
    return AvailabilityOut(
        accepting_work=profile.accepting_work,
        back_on=profile.back_on,
        is_available=profile.status is ProviderStatus.APPROVED
        and is_available(
            accepting_work=profile.accepting_work,
            back_on=profile.back_on,
            today=utcnow().date(),
        ),
    )


class ProviderProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_own(self, user: User) -> ProviderProfile | None:
        stmt = (
            select(ProviderProfile)
            .where(ProviderProfile.user_id == user.id)
            .options(
                selectinload(ProviderProfile.trades),
                selectinload(ProviderProfile.city),
                selectinload(ProviderProfile.photos),
                selectinload(ProviderProfile.user),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def submit(self, user: User, payload: ProviderApplicationIn) -> ProviderProfile:
        """Create the application, or correct one an admin sent back.

        The status is forced to `pending` whichever path it takes. A tradesman
        approving himself by posting a status is not a case worth relying on a
        schema to prevent.
        """
        if user.role is not Role.PROVIDER:
            raise DomainError(ErrorCode.FORBIDDEN, role=user.role.value)

        application = validate_application(
            trade_ids=payload.trade_ids,
            city_id=payload.city_id,
            radius_km=payload.radius_km,
            headline=payload.headline,
            bio=payload.bio,
            years_experience=payload.years_experience,
            starting_price_centimes=payload.starting_price_centimes,
            avatar_path=payload.avatar_path,
            id_card_path=payload.id_card_path,
            photo_paths=payload.photo_paths,
        )

        city = self.db.get(City, application.city_id)
        if city is None or not city.is_active:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="city_id")

        trades = list(
            self.db.execute(
                select(Trade).where(
                    Trade.id.in_(application.trade_ids), Trade.is_active.is_(True)
                )
            ).scalars()
        )
        if len(trades) != len(application.trade_ids):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="trade_ids")

        profile = self.get_own(user)
        if profile is None:
            profile = ProviderProfile(user_id=user.id)
            self.db.add(profile)
        elif profile.status not in (ProviderStatus.PENDING, ProviderStatus.REJECTED):
            # An approved profile is edited at M8, not by resubmitting the
            # application that got it approved.
            raise DomainError(ErrorCode.CONFLICT, status=profile.status.value)

        self._apply(profile, application, trades)
        self.db.flush()
        self._replace_photos(profile, application)

        if application.avatar_path:
            user.avatar_url = f"/api/v1/uploads/{application.avatar_path}"

        self._ensure_credit_account(profile)
        self.db.commit()

        refreshed = self.get_own(user)
        assert refreshed is not None
        return refreshed

    # -- M8 ---------------------------------------------------------------

    def edit(self, user: User, payload: ProfileEditIn) -> ProviderProfile:
        """Change the shop window. Never the CIN, never the status.

        His identity was checked once at A2; letting him swap the card
        afterwards would make that check mean nothing. So this method reaches
        for a narrow list of fields rather than reusing `_apply`, which resets
        the application — sharing that code is how an edit ends up sending an
        approved tradesman back into the queue.
        """
        profile = self._approved(user)

        city = self.db.get(City, payload.city_id)
        if city is None or not city.is_active:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="city_id")

        trades = list(
            self.db.execute(
                select(Trade).where(
                    Trade.id.in_(payload.trade_ids), Trade.is_active.is_(True)
                )
            ).scalars()
        )
        if len(trades) != len(set(payload.trade_ids)):
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="trade_ids")

        profile.city_id = city.id
        profile.radius_km = payload.radius_km
        profile.headline = payload.headline.strip()
        profile.bio = " ".join(payload.bio.split())
        profile.years_experience = payload.years_experience
        profile.starting_price_centimes = payload.starting_price_centimes
        profile.trades = trades

        if payload.avatar_path:
            user.avatar_url = f"/api/v1/uploads/{payload.avatar_path}"

        self.db.commit()
        return self._reload(user)

    def set_availability(self, user: User, payload: AvailabilityIn) -> ProviderProfile:
        """Taking work, or away until a date that lifts the pause itself."""
        profile = self._approved(user)

        if payload.accepting_work:
            profile.accepting_work = True
            # The date belonged to the pause it ended. Keeping it would show
            # "back on the 12th" beside a man who is already working.
            profile.back_on = None
        else:
            try:
                profile.back_on = validate_pause(
                    back_on=payload.back_on, today=utcnow().date()
                )
            except ValueError as error:
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field=str(error)
                ) from error
            profile.accepting_work = False

        self.db.commit()
        return self._reload(user)

    def add_photo(self, user: User, path: str) -> ProviderProfile:
        profile = self._approved(user)

        if len(profile.photos) >= MAX_PORTFOLIO_PHOTOS:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                field="photos",
                max_photos=MAX_PORTFOLIO_PHOTOS,
            )

        profile.photos.append(
            ProviderPhoto(
                url=f"/api/v1/uploads/{path}",
                sort_order=max((photo.sort_order for photo in profile.photos), default=-1) + 1,
            )
        )
        self.db.commit()
        return self._reload(user)

    def remove_photo(self, user: User, photo_id: int) -> ProviderProfile:
        profile = self._approved(user)

        photo = next((one for one in profile.photos if one.id == photo_id), None)
        if photo is None:
            # Somebody else's photo id is a 404, not a 403: the id space is
            # guessable and a 403 would confirm the photo exists.
            raise DomainError(ErrorCode.NOT_FOUND)

        profile.photos.remove(photo)
        self.db.commit()
        return self._reload(user)

    def _approved(self, user: User) -> ProviderProfile:
        """M8 is for a tradesman who is on the platform.

        While he is pending or rejected the screen he needs is M2, and the
        thing he edits there is the application itself.
        """
        profile = self.get_own(user)
        if profile is None:
            raise DomainError(ErrorCode.NOT_FOUND)
        if profile.status is not ProviderStatus.APPROVED:
            raise DomainError(ErrorCode.CONFLICT, status=profile.status.value)
        return profile

    def _reload(self, user: User) -> ProviderProfile:
        refreshed = self.get_own(user)
        assert refreshed is not None
        return refreshed

    def _apply(
        self,
        profile: ProviderProfile,
        application: ProviderApplication,
        trades: list[Trade],
    ) -> None:
        profile.city_id = application.city_id
        profile.radius_km = application.radius_km
        profile.headline = application.headline
        profile.bio = application.bio
        profile.years_experience = application.years_experience
        profile.starting_price_centimes = application.starting_price_centimes
        profile.id_card_url = application.id_card_path
        profile.trades = trades

        # Whatever was posted, an application starts unjudged.
        profile.status = ProviderStatus.PENDING
        profile.rejection_reason = None
        profile.approved_at = None
        profile.approved_by_id = None

    def _replace_photos(
        self, profile: ProviderProfile, application: ProviderApplication
    ) -> None:
        profile.photos.clear()
        self.db.flush()
        for order, path in enumerate(application.photo_paths):
            profile.photos.append(
                ProviderPhoto(url=f"/api/v1/uploads/{path}", sort_order=order)
            )

    def _ensure_credit_account(self, profile: ProviderProfile) -> None:
        existing = self.db.execute(
            select(CreditAccount).where(CreditAccount.provider_id == profile.id)
        ).scalar_one_or_none()
        if existing is not None:
            return

        self.db.add(
            CreditAccount(
                provider_id=profile.id,
                balance_centimes=0,
                free_leads_left=FREE_LEADS_NEW_PROVIDER,
            )
        )
