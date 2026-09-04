"""Paid placement: what it costs, how long it lasts, and what it may not buy.

The one rule worth stating out loud is the one about what is *not* for sale.
A boost moves a tradesman up the list and puts a label on his card saying it
did. It does not touch his rating, it does not hide a competitor, and it does
not change what a client is told about him. A marketplace that sells the
appearance of quality has sold the only thing it had.

Framework-free, so the arithmetic of "he paid on the 3rd and again on the
10th" can be argued about without a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.money import dirhams

#: A month, and a month is thirty days. Calendar months would make February
#: cheaper than March for no reason a tradesman could be told.
BOOST_DAYS = 30

#: What thirty days of placement costs. Small on purpose: it is meant to be an
#: easy yes for a man who is already listed for free, not a gate in front of
#: him.
BOOST_MONTHLY_CENTIMES = dirhams(20)


class BoostRefused(Exception):
    """He cannot have it yet. Unlike the lead fee, this one really does refuse.

    Refusing a lead fee would break a handshake two people had already made;
    refusing a boost breaks nothing. Nobody is waiting, no work is pending, and
    he can top up and come back — so the balance is checked *before* the money
    moves rather than allowed to go negative.
    """


@dataclass(frozen=True, slots=True)
class Boost:
    """What buying one costs and when it runs out."""

    price_centimes: int
    expires_at: datetime
    balance_after_centimes: int


def is_active(boosted_until: datetime | None, now: datetime) -> bool:
    return boosted_until is not None and boosted_until > now


def buy(
    *,
    boosted_until: datetime | None,
    balance_centimes: int,
    price_centimes: int,
    now: datetime,
    days: int = BOOST_DAYS,
) -> Boost:
    """Thirty more days, and the money for them.

    **Stacked, not restarted.** A tradesman who renews on the 25th of a month
    he paid for on the 1st keeps the five days he has left; the new month is
    added to the end of the old one. Restarting from today would quietly take
    those days off him, and he would find out by counting.
    """
    if balance_centimes < price_centimes:
        raise BoostRefused

    # Written as the comparison rather than through `is_active`, because the
    # narrowing is the point: `boosted_until` is only the start date when it
    # is both set and still in the future.
    start = boosted_until if boosted_until is not None and boosted_until > now else now
    return Boost(
        price_centimes=price_centimes,
        expires_at=start + timedelta(days=days),
        balance_after_centimes=balance_centimes - price_centimes,
    )
