"""Password policy, hashing, lockout arithmetic and token handling."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode
from app.core.security import (
    ACCESS_TOKEN,
    LOCKOUT_MINUTES,
    MAX_FAILED_ATTEMPTS,
    REFRESH_TOKEN,
    create_token,
    decode_token,
    hash_password,
    is_locked,
    lockout_remaining_seconds,
    lockout_until,
    validate_password,
    verify_password,
)

SECRET = "test-secret-not-used-anywhere-real-and-long-enough-for-hs256"
OTHER_SECRET = "a-different-secret-that-is-also-long-enough-for-hs256"

#: Fixed instant for the lockout arithmetic, which never looks at a clock.
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

#: Token tests must mint against the real clock — `decode_token` verifies
#: `exp` against it, so a token issued at a hardcoded past date is born
#: expired and would pass the wrong assertion for the wrong reason.
REAL_NOW = datetime.now(UTC)


@pytest.mark.parametrize("bad", ["short1", "", "abcdefghij", "1234567890", "a" * 200 + "1"])
def test_weak_passwords_are_refused(bad):
    with pytest.raises(DomainError) as exc:
        validate_password(bad)
    assert exc.value.code is ErrorCode.PASSWORD_TOO_WEAK


def test_a_reasonable_password_passes():
    assert validate_password("khedma2026") == "khedma2026"


def test_hashing_is_salted_and_verifiable():
    first = hash_password("khedma2026")
    second = hash_password("khedma2026")
    assert first != second  # different salts
    assert verify_password("khedma2026", first)
    assert not verify_password("khedma2027", first)


def test_verify_survives_a_corrupt_hash():
    assert verify_password("khedma2026", "not-a-hash") is False


def test_lockout_only_after_the_limit():
    for attempts in range(MAX_FAILED_ATTEMPTS):
        assert lockout_until(attempts, NOW) is None
    locked = lockout_until(MAX_FAILED_ATTEMPTS, NOW)
    assert locked == NOW + timedelta(minutes=LOCKOUT_MINUTES)


def test_lockout_expiry():
    locked = NOW + timedelta(minutes=15)
    assert is_locked(locked, NOW) is True
    assert is_locked(locked, NOW + timedelta(minutes=16)) is False
    assert is_locked(None, NOW) is False
    assert lockout_remaining_seconds(locked, NOW) == 900
    assert lockout_remaining_seconds(None, NOW) == 0


def test_a_token_round_trips():
    token = create_token(
        user_id=42,
        role=Role.ADMIN,
        secret=SECRET,
        token_type=ACCESS_TOKEN,
        expires_in=timedelta(minutes=30),
        now=REAL_NOW,
    )
    payload = decode_token(token, secret=SECRET, expected_type=ACCESS_TOKEN)
    assert payload.user_id == 42
    assert payload.role is Role.ADMIN


def test_a_refresh_token_cannot_be_used_as_an_access_token():
    token = create_token(
        user_id=1,
        role=Role.CLIENT,
        secret=SECRET,
        token_type=REFRESH_TOKEN,
        expires_in=timedelta(days=30),
        now=REAL_NOW,
    )
    with pytest.raises(DomainError) as exc:
        decode_token(token, secret=SECRET, expected_type=ACCESS_TOKEN)
    assert exc.value.code is ErrorCode.TOKEN_WRONG_TYPE


def test_another_secret_cannot_forge_a_token():
    token = create_token(
        user_id=1,
        role=Role.ADMIN,
        secret=OTHER_SECRET,
        token_type=ACCESS_TOKEN,
        expires_in=timedelta(minutes=30),
        now=REAL_NOW,
    )
    with pytest.raises(DomainError) as exc:
        decode_token(token, secret=SECRET, expected_type=ACCESS_TOKEN)
    assert exc.value.code is ErrorCode.TOKEN_INVALID


def test_an_expired_token_says_so():
    token = create_token(
        user_id=1,
        role=Role.CLIENT,
        secret=SECRET,
        token_type=ACCESS_TOKEN,
        expires_in=timedelta(seconds=-1),
        now=REAL_NOW,
    )
    with pytest.raises(DomainError) as exc:
        decode_token(token, secret=SECRET, expected_type=ACCESS_TOKEN)
    assert exc.value.code is ErrorCode.TOKEN_EXPIRED


def test_two_tokens_are_never_the_same_token():
    args = dict(
        user_id=1,
        role=Role.CLIENT,
        secret=SECRET,
        token_type=ACCESS_TOKEN,
        expires_in=timedelta(minutes=30),
        now=REAL_NOW,
    )
    assert create_token(**args) != create_token(**args)  # distinct jti
