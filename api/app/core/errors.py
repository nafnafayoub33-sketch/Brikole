"""The error vocabulary.

The API never returns a sentence for a human to read: it returns a *code*, and
the web app owns the wording in all three languages. Adding a code here means
adding a translation key on the other side.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    # input
    PHONE_INVALID = "phone_invalid"
    PASSWORD_TOO_WEAK = "password_too_weak"
    VALIDATION_FAILED = "validation_failed"

    # registration and sign-in
    PHONE_TAKEN = "phone_taken"
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_SUSPENDED = "account_suspended"
    ROLE_NOT_SELF_REGISTERABLE = "role_not_self_registerable"

    # tokens
    TOKEN_INVALID = "token_invalid"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_WRONG_TYPE = "token_wrong_type"

    # authorisation
    NOT_AUTHENTICATED = "not_authenticated"
    FORBIDDEN = "forbidden"

    # resources
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"

    # staff acting on an account (A3)
    SELF_ACTION_REFUSED = "self_action_refused"
    LAST_ADMIN = "last_admin"
    ROLE_NOT_ASSIGNABLE = "role_not_assignable"
    PROVIDER_ROLE_LOCKED = "provider_role_locked"

    # money
    INSUFFICIENT_CREDIT = "insufficient_credit"
    #: Not a refusal — a price. The message contains a contact detail, which
    #: costs the lead fee; the caller resends with `accept_charge` to agree.
    CONTACT_COSTS_CREDIT = "contact_costs_credit"
    AMOUNT_INVALID = "amount_invalid"


_STATUS: dict[ErrorCode, int] = {
    ErrorCode.PHONE_INVALID: 422,
    ErrorCode.PASSWORD_TOO_WEAK: 422,
    ErrorCode.VALIDATION_FAILED: 422,
    ErrorCode.AMOUNT_INVALID: 422,
    ErrorCode.PHONE_TAKEN: 409,
    ErrorCode.CONFLICT: 409,
    # Well-formed, and the caller is allowed — the world says no.
    ErrorCode.SELF_ACTION_REFUSED: 409,
    ErrorCode.LAST_ADMIN: 409,
    ErrorCode.ROLE_NOT_ASSIGNABLE: 409,
    ErrorCode.PROVIDER_ROLE_LOCKED: 409,
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.NOT_AUTHENTICATED: 401,
    ErrorCode.TOKEN_INVALID: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    ErrorCode.TOKEN_WRONG_TYPE: 401,
    ErrorCode.ACCOUNT_LOCKED: 423,
    ErrorCode.ACCOUNT_SUSPENDED: 403,
    ErrorCode.ROLE_NOT_SELF_REGISTERABLE: 403,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.INSUFFICIENT_CREDIT: 402,
    ErrorCode.CONTACT_COSTS_CREDIT: 402,
    ErrorCode.NOT_FOUND: 404,
}


class DomainError(Exception):
    """Raised by the rules in `app.core` and by services.

    Carries a code and, optionally, details the client needs to render a useful
    message — how many minutes a lockout has left, for instance.
    """

    def __init__(self, code: ErrorCode, **details: Any) -> None:
        super().__init__(code.value)
        self.code = code
        self.details = details

    @property
    def http_status(self) -> int:
        return _STATUS.get(self.code, 400)

    def as_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"code": self.code.value}
        if self.details:
            body["details"] = self.details
        return body

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"DomainError({self.code.value}, {self.details})"
