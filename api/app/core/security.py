"""Password hashing, password policy, sign-in lockout and JWTs.

Pure functions over their arguments: nothing here reads a setting, opens a
connection or looks at the clock on its own — `now` and `secret` are always
passed in, which is what makes it all testable without a database.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode

_hasher = PasswordHasher()

ALGORITHM = "HS256"

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


# --- passwords ---------------------------------------------------------------


def validate_password(password: str) -> str:
    """Enforce the password policy, or raise `PASSWORD_TOO_WEAK`.

    Long enough, not absurdly long (argon2 would happily burn CPU on a 1 MB
    string), and mixing letters with digits. Deliberately modest: a rule nobody
    can satisfy pushes people to `Password1!` written on the counter.
    """
    if not (MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH):
        raise DomainError(
            ErrorCode.PASSWORD_TOO_WEAK,
            min_length=MIN_PASSWORD_LENGTH,
            max_length=MAX_PASSWORD_LENGTH,
        )
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise DomainError(ErrorCode.PASSWORD_TOO_WEAK, needs="letter_and_digit")
    return password


def hash_password(password: str) -> str:
    return _hasher.hash(validate_password(password))


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True when argon2's parameters have moved on since this hash was made."""
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


# --- sign-in lockout ---------------------------------------------------------


def lockout_until(failed_attempts: int, now: datetime) -> datetime | None:
    """Where the account stands after `failed_attempts` consecutive failures.

    Returns the moment it unlocks, or None while it is still under the limit.
    """
    if failed_attempts < MAX_FAILED_ATTEMPTS:
        return None
    return now + timedelta(minutes=LOCKOUT_MINUTES)


def is_locked(locked_until: datetime | None, now: datetime) -> bool:
    return locked_until is not None and locked_until > now


def lockout_remaining_seconds(locked_until: datetime | None, now: datetime) -> int:
    if not is_locked(locked_until, now):
        return 0
    assert locked_until is not None
    return max(0, int((locked_until - now).total_seconds()))


# --- tokens ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TokenPayload:
    user_id: int
    role: Role
    token_type: str
    jti: str
    expires_at: datetime


def create_token(
    *,
    user_id: int,
    role: Role,
    secret: str,
    token_type: str,
    expires_in: timedelta,
    now: datetime | None = None,
) -> str:
    issued = now or datetime.now(UTC)
    expires = issued + expires_in
    claims = {
        "sub": str(user_id),
        "role": role.value,
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def decode_token(token: str, *, secret: str, expected_type: str) -> TokenPayload:
    """Verify signature, expiry and token type, or raise the matching code.

    Checking the type matters: a refresh token is long-lived and lives in a
    cookie, so it must never be usable as an access token.
    """
    try:
        claims = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise DomainError(ErrorCode.TOKEN_EXPIRED) from exc
    except jwt.PyJWTError as exc:
        raise DomainError(ErrorCode.TOKEN_INVALID) from exc

    if claims.get("type") != expected_type:
        raise DomainError(ErrorCode.TOKEN_WRONG_TYPE)

    try:
        user_id = int(claims["sub"])
        role = Role(claims["role"])
        expires_at = datetime.fromtimestamp(int(claims["exp"]), tz=UTC)
        jti = str(claims["jti"])
    except (KeyError, ValueError) as exc:
        raise DomainError(ErrorCode.TOKEN_INVALID) from exc

    return TokenPayload(
        user_id=user_id, role=role, token_type=expected_type, jti=jti, expires_at=expires_at
    )
