"""Topping up a tradesman's balance.

The rule this module exists to state: **submitting a top-up moves no money.**
Only an admin confirming that the transfer landed does, and that is a different
action taken by a different person on a different screen.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.money import dirhams

MIN_TOPUP = dirhams(50)
MAX_TOPUP = dirhams(20_000)
MAX_REFERENCE = 120

#: What M9 offers as buttons. He can still type any amount in range — these are
#: the ones that save him the typing, sized to a round number of leads.
PRESET_AMOUNTS = (dirhams(100), dirhams(300), dirhams(500), dirhams(1_000))


@dataclass(frozen=True, slots=True)
class NewTopup:
    amount_centimes: int
    reference: str


def validate_topup(*, amount_centimes: int, reference: str | None) -> NewTopup:
    """Bound the amount and require a reference somebody can match.

    The reference is what an admin types into a bank statement search. Without
    it the approval screen is a list of claims nobody can check, so it is not
    optional and it is not allowed to be whitespace.
    """
    if amount_centimes < MIN_TOPUP or amount_centimes > MAX_TOPUP:
        raise ValueError("amount_centimes")

    cleaned = " ".join((reference or "").split())
    if not cleaned or len(cleaned) > MAX_REFERENCE:
        raise ValueError("reference")

    return NewTopup(amount_centimes=amount_centimes, reference=cleaned)


def leads_bought(amount_centimes: int, fee_centimes: int) -> int:
    """How many accepted offers an amount pays for.

    M9 shows this beside every preset: "500 DH" means nothing to a tradesman
    deciding how much to transfer, and "50 jobs" means everything.
    """
    if fee_centimes <= 0:
        return 0
    return amount_centimes // fee_centimes
