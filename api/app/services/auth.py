"""Registration, sign-in and tokens.

The rules themselves live in `app.core`; this ties them to the database and to
the settings. Anything here that could be a pure function is one, over there.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import Settings
from app.core import security
from app.core.enums import Role, UserStatus
from app.core.errors import DomainError, ErrorCode
from app.core.permissions import assert_self_registerable, home_path, permissions_for
from app.models.base import utcnow
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.auth import MeOut, ProviderSummaryOut, TokenOut


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access: TokenOut
    refresh: str
    refresh_max_age: int


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.users = UserRepository(db)

    # --- registration --------------------------------------------------------

    def register(
        self, *, phone: str, full_name: str, password: str, role: Role, language: str = "ar"
    ) -> User:
        """Create a client or a tradesman account.

        A tradesman gets **no** provider profile here: he fills that in at M1,
        and it is created `pending` for an admin to approve. Landing without one
        is exactly what routes him to onboarding.
        """
        assert_self_registerable(role)

        if self.users.phone_exists(phone):
            raise DomainError(ErrorCode.PHONE_TAKEN)

        # Raises PASSWORD_TOO_WEAK before anything is written.
        password_hash = security.hash_password(password)

        user = self.users.add(
            phone=phone,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            language=language,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    # --- sign-in -------------------------------------------------------------

    def authenticate(self, *, phone: str, password: str, now: datetime | None = None) -> User:
        moment = now or utcnow()
        user = self.users.get_by_phone(phone)

        if user is None:
            # Same error as a wrong password: telling a stranger which numbers
            # are registered is a free list of who to target.
            raise DomainError(ErrorCode.INVALID_CREDENTIALS)

        if security.is_locked(user.locked_until, moment):
            raise DomainError(
                ErrorCode.ACCOUNT_LOCKED,
                retry_after_seconds=security.lockout_remaining_seconds(user.locked_until, moment),
            )

        if not security.verify_password(password, user.password_hash):
            attempts = user.failed_login_attempts + 1
            self.users.record_failed_login(
                user, locked_until=security.lockout_until(attempts, moment)
            )
            self.db.commit()
            raise DomainError(ErrorCode.INVALID_CREDENTIALS)

        self._assert_usable(user, moment)

        if security.needs_rehash(user.password_hash):
            user.password_hash = security.hash_password(password)

        self.users.record_successful_login(user, now=moment)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _assert_usable(self, user: User, now: datetime) -> None:
        if user.status is UserStatus.DELETED:
            raise DomainError(ErrorCode.INVALID_CREDENTIALS)

        if user.status is UserStatus.SUSPENDED:
            # A timed suspension lifts itself; there is no cron for something
            # this cheap to check on the way in.
            if user.suspended_until is not None and user.suspended_until <= now:
                user.status = UserStatus.ACTIVE
                user.suspended_until = None
                user.suspension_reason = None
                return
            raise DomainError(
                ErrorCode.ACCOUNT_SUSPENDED,
                until=user.suspended_until.isoformat() if user.suspended_until else None,
                reason=user.suspension_reason,
            )

    # --- tokens --------------------------------------------------------------

    def issue_tokens(self, user: User) -> IssuedTokens:
        access_ttl = timedelta(minutes=self.settings.access_token_minutes)
        refresh_ttl = timedelta(days=self.settings.refresh_token_days)

        access = security.create_token(
            user_id=user.id,
            role=user.role,
            secret=self.settings.secret_key,
            token_type=security.ACCESS_TOKEN,
            expires_in=access_ttl,
        )
        refresh = security.create_token(
            user_id=user.id,
            role=user.role,
            secret=self.settings.secret_key,
            token_type=security.REFRESH_TOKEN,
            expires_in=refresh_ttl,
        )
        return IssuedTokens(
            access=TokenOut(access_token=access, expires_in=int(access_ttl.total_seconds())),
            refresh=refresh,
            refresh_max_age=int(refresh_ttl.total_seconds()),
        )

    def user_from_token(self, token: str, *, expected_type: str) -> User:
        payload = security.decode_token(
            token, secret=self.settings.secret_key, expected_type=expected_type
        )
        user = self.users.get(payload.user_id)
        if user is None or user.status is UserStatus.DELETED:
            raise DomainError(ErrorCode.TOKEN_INVALID)

        # The role is re-read from the database rather than trusted from the
        # token: an admin who demotes someone must not have to wait for a token
        # to expire.
        self._assert_usable(user, utcnow())
        return user

    def refresh(self, refresh_token: str) -> tuple[User, IssuedTokens]:
        user = self.user_from_token(refresh_token, expected_type=security.REFRESH_TOKEN)
        return user, self.issue_tokens(user)

    # --- password ------------------------------------------------------------

    def change_password(self, user: User, *, current: str, new: str) -> None:
        if not security.verify_password(current, user.password_hash):
            raise DomainError(ErrorCode.INVALID_CREDENTIALS)
        user.password_hash = security.hash_password(new)
        self.db.commit()


def me_payload(user: User) -> MeOut:
    """What `/auth/me` returns: the account plus what it is allowed to do."""
    provider = None
    if user.provider_profile is not None:
        provider = ProviderSummaryOut.model_validate(user.provider_profile)

    return MeOut(
        id=user.id,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        language=user.language,
        city_id=user.city_id,
        avatar_url=user.avatar_url,
        permissions=sorted(permissions_for(user.role)),
        home_path=home_path(user.role),
        provider=provider,
    )
