"""Registration, sign-in, tokens, and who am I."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.enums import ProviderStatus, Role, UserStatus
from app.core.phone import normalise_phone
from app.core.security import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from app.schemas.common import ApiModel


class _PhoneField(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def _normalise(cls, value: str) -> str:
        # Normalising at the edge means every layer below sees exactly one
        # format, and `0612…` and `+212612…` can never become two accounts.
        return normalise_phone(value)


class RegisterIn(_PhoneField):
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    #: Only `client` and `provider` are accepted; the service rejects the rest.
    role: Role
    language: str = Field(default="ar", pattern="^(ar|fr|en)$")

    @field_validator("full_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("full_name too short")
        return cleaned


class LoginIn(_PhoneField):
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class ProviderSummaryOut(ApiModel):
    id: int
    status: ProviderStatus
    city_id: int
    rating_avg: float
    rating_count: int
    jobs_done: int


class MeOut(ApiModel):
    id: int
    phone: str
    full_name: str
    role: Role
    status: UserStatus
    language: str
    city_id: int | None
    avatar_url: str | None

    #: What this role may do, and where it belongs. The web app reads both
    #: instead of hardcoding role names in components.
    permissions: list[str]
    home_path: str

    #: Present only for a tradesman. `None` means he has not filled in M1 yet,
    #: which is what sends him to onboarding.
    provider: ProviderSummaryOut | None = None


class LoginOut(BaseModel):
    token: TokenOut
    user: MeOut


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
