"""What a tradesman may offer, and whether he may offer at all.

Framework-free. The credit rule in particular is the one the whole business
model rests on, so it lives here and is tested without a database.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.money import dirhams

MIN_PRICE = dirhams(20)
MAX_PRICE = dirhams(200_000)
MAX_MESSAGE = 1000


@dataclass(frozen=True, slots=True)
class NewOffer:
    price_centimes: int
    message: str


def validate_offer(*, price_centimes: int, message: str | None) -> NewOffer:
    """Bound the price and tidy the message.

    A floor exists because an offer of 1 DH is not a price, it is a way to sit
    at the top of a list sorted by price. A ceiling exists because a typo in
    centimes is otherwise indistinguishable from a real quote.
    """
    if price_centimes < MIN_PRICE or price_centimes > MAX_PRICE:
        raise ValueError("price_centimes")

    cleaned = " ".join((message or "").split())
    if len(cleaned) > MAX_MESSAGE:
        raise ValueError("message")

    return NewOffer(price_centimes=price_centimes, message=cleaned)


def can_send_offer(*, free_leads_left: int, balance_centimes: int, fee_centimes: int) -> bool:
    """Whether he can afford the lead this offer might turn into.

    This is the guard, and it sits *here* — before the offer is sent — rather
    than at acceptance. At acceptance it is the client pressing the button, and
    refusing him over somebody else's empty wallet is not a thing the product
    may do (see `core.job.charge_for_lead`). So the tradesman is stopped at the
    only moment where the person being stopped is the person who can fix it.
    """
    return free_leads_left > 0 or balance_centimes >= fee_centimes
