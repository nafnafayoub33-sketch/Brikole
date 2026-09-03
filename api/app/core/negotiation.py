"""The handshake that turns a conversation into a job.

The old flow was one press: the client accepted an offer and the platform
charged the tradesman on the spot. It was simple and it was wrong in one
expensive way — the client was committing to a price he had had no chance to
discuss, and the tradesman was being charged for a job whose terms he had never
confirmed.

So the deal is agreed in the chat and then signed twice. Both sides can change
the price or the terms; **both** have to say yes to the same thing before the
job exists and anybody is charged.

The mechanism is a version number rather than two booleans, and that is the
whole trick. You do not agree to "the deal", you agree to *version 4 of the
deal*. Change the price and it becomes version 5, which nobody has agreed to
yet — so a client who accepted 400 DH is never quietly held to the 500 DH the
tradesman typed a minute later. Two booleans and a `reset()` somewhere would
have been the same idea with a bug in it waiting for the day somebody adds a
third editable field and forgets the reset.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import DomainError, ErrorCode
from app.core.money import validate_amount

TERMS_MAX = 2000


@dataclass(frozen=True, slots=True)
class Terms:
    """What is on the table right now."""

    price_centimes: int
    terms: str
    version: int
    client_agreed_version: int | None
    provider_agreed_version: int | None

    @property
    def client_has_agreed(self) -> bool:
        return self.client_agreed_version == self.version

    @property
    def provider_has_agreed(self) -> bool:
        return self.provider_agreed_version == self.version

    @property
    def sealed(self) -> bool:
        """Both sides, on the same version. This is what creates the job."""
        return self.client_has_agreed and self.provider_has_agreed


def validate_terms(text: str) -> str:
    """What the price covers, in the tradesman's own words. May be empty —
    plenty of jobs are just a price — but never longer than a page."""
    cleaned = text.strip()
    if len(cleaned) > TERMS_MAX:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="terms", max_length=TERMS_MAX)
    return cleaned


def propose(current: Terms, *, price_centimes: int, terms: str) -> Terms:
    """Put a new price or new terms on the table.

    Every proposal clears both signatures, including the proposer's own: he has
    not agreed to his new number either until he says so, and letting a
    proposal count as its own acceptance would let one side change the price
    after the other had signed and have the job created on the spot.
    """
    validate_amount(price_centimes)
    cleaned = validate_terms(terms)

    if price_centimes == current.price_centimes and cleaned == current.terms:
        raise DomainError(ErrorCode.CONFLICT, reason="terms_unchanged")

    return Terms(
        price_centimes=price_centimes,
        terms=cleaned,
        version=current.version + 1,
        client_agreed_version=None,
        provider_agreed_version=None,
    )


def agree(current: Terms, *, as_client: bool, version: int) -> Terms:
    """Sign what is on the table.

    The caller says which version he is signing, and a stale one is refused
    rather than silently upgraded: the screen he pressed on was showing a
    different price from the one in the database, and agreeing to a number he
    never saw is the exact failure this whole design exists to prevent.
    """
    if version != current.version:
        raise DomainError(
            ErrorCode.CONFLICT, reason="terms_moved", version=current.version
        )

    already = current.client_has_agreed if as_client else current.provider_has_agreed
    if already:
        raise DomainError(ErrorCode.CONFLICT, reason="already_agreed")

    if as_client:
        return Terms(
            price_centimes=current.price_centimes,
            terms=current.terms,
            version=current.version,
            client_agreed_version=version,
            provider_agreed_version=current.provider_agreed_version,
        )

    return Terms(
        price_centimes=current.price_centimes,
        terms=current.terms,
        version=current.version,
        client_agreed_version=current.client_agreed_version,
        provider_agreed_version=version,
    )


def withdraw(current: Terms, *, as_client: bool) -> Terms:
    """Take a signature back, while the other side has not signed yet.

    Once both have signed the job exists, money has moved and this is no longer
    the screen that undoes it — that is a cancellation, with a reason, on C4.
    """
    if current.sealed:
        raise DomainError(ErrorCode.CONFLICT, reason="already_sealed")

    if as_client:
        return Terms(
            price_centimes=current.price_centimes,
            terms=current.terms,
            version=current.version,
            client_agreed_version=None,
            provider_agreed_version=current.provider_agreed_version,
        )

    return Terms(
        price_centimes=current.price_centimes,
        terms=current.terms,
        version=current.version,
        client_agreed_version=current.client_agreed_version,
        provider_agreed_version=None,
    )
