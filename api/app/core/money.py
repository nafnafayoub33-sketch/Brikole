"""Money is an integer number of centimes. Always.

`3000` is 30,00 DH. There are no floats in this codebase, and no `DECIMAL`
column that JavaScript would have to read back as a string. Formatting for a
human happens in the web app, at render time, and nowhere else.
"""

from __future__ import annotations

from app.core.errors import DomainError, ErrorCode

CENTIMES_PER_DIRHAM = 100
MAX_AMOUNT_CENTIMES = 100_000_000  # 1 000 000,00 DH — a top-up above this is a typo


def dirhams(amount: int) -> int:
    """Whole dirhams to centimes. `dirhams(30)` is `3000`."""
    return amount * CENTIMES_PER_DIRHAM


def validate_amount(centimes: int, *, allow_zero: bool = False) -> int:
    """A positive, sane amount, or raise `AMOUNT_INVALID`."""
    if not isinstance(centimes, int) or isinstance(centimes, bool):
        raise DomainError(ErrorCode.AMOUNT_INVALID)
    if centimes < 0 or (centimes == 0 and not allow_zero):
        raise DomainError(ErrorCode.AMOUNT_INVALID)
    if centimes > MAX_AMOUNT_CENTIMES:
        raise DomainError(ErrorCode.AMOUNT_INVALID, max_centimes=MAX_AMOUNT_CENTIMES)
    return centimes


def can_afford(balance_centimes: int, fee_centimes: int, free_leads: int) -> bool:
    """A tradesman can take a lead if he has a free one or the balance for it."""
    if free_leads > 0:
        return True
    return balance_centimes >= fee_centimes


def debit(balance_centimes: int, amount_centimes: int) -> int:
    """Subtract, refusing to go negative. The ledger is never allowed to lie."""
    validate_amount(amount_centimes)
    if balance_centimes < amount_centimes:
        raise DomainError(
            ErrorCode.INSUFFICIENT_CREDIT,
            balance_centimes=balance_centimes,
            required_centimes=amount_centimes,
        )
    return balance_centimes - amount_centimes


def credit(balance_centimes: int, amount_centimes: int) -> int:
    validate_amount(amount_centimes)
    return balance_centimes + amount_centimes
