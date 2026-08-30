"""Creating and correcting a tradesman's application."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ProviderStatus, Role
from app.core.errors import DomainError, ErrorCode
from app.core.policy import FREE_LEADS_NEW_PROVIDER
from app.core.provider_application import ProviderApplication, validate_application
from app.models.catalog import City, Trade
from app.models.credit import CreditAccount
from app.models.provider import ProviderPhoto, ProviderProfile
from app.models.user import User
from app.schemas.pro import ProviderApplicationIn


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
