"""Charging a tradesman for a lead, in the one place it happens.

A lead is charged for exactly once, and there are now two moments it can
happen at:

* the two of them shake hands and the job is created, or
* the tradesman hands over his phone number in the chat before that.

They are the same event — a real lead was delivered — so they cost the same
and they are written the same way. Splitting them into two prices is the
mistake that would matter: if revealing a number were cheaper than accepting a
job, every tradesman's best move would be to send his number and never accept
anything, and the platform would earn the smaller number on every job it ever
brokered instead of the larger one.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.job import charge_for_lead
from app.core.policy import SettingKey, lead_fee_for
from app.models.credit import CreditAccount, CreditTransaction
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.repositories.catalog import SettingsRepository


@dataclass(frozen=True, slots=True)
class Charge:
    """What the tradesman was actually charged, and what it left him."""

    fee_centimes: int
    #: Zero when a free lead covered it. The fee above is still what the lead
    #: was worth, and what gets frozen onto the offer.
    taken_centimes: int
    balance_after_centimes: int


def fee_for(db: Session, request: ServiceRequest) -> int:
    """What this request's trade charges for a lead."""
    settings = SettingsRepository(db)
    return lead_fee_for(
        request.trade.lead_fee_centimes, settings.get_int(SettingKey.DEFAULT_LEAD_FEE)
    )


def charge(
    db: Session,
    *,
    provider: ProviderProfile,
    offer: Offer,
    request: ServiceRequest,
    job_id: int | None = None,
    reason: str | None = None,
) -> Charge:
    """Take the fee and write the row that explains it, together.

    **A short balance never refuses.** The balance is allowed to go negative
    and the debt recorded: on the handshake there are two people who have just
    agreed, and on a reveal the number is already out of the bag by the time
    anybody could refuse. The pressure belongs upstream, at M5, where the
    person stopped is the one who can fix it.
    """
    credit = db.execute(
        select(CreditAccount).where(CreditAccount.provider_id == provider.id)
    ).scalar_one_or_none()
    if credit is None:
        # Every approved tradesman is given one at M1; a missing account is a
        # bug, not a free lead.
        credit = CreditAccount(provider_id=provider.id, balance_centimes=0, free_leads_left=0)
        db.add(credit)
        db.flush()

    fee = fee_for(db, request)
    taken = charge_for_lead(
        free_leads_left=credit.free_leads_left,
        balance_centimes=credit.balance_centimes,
        fee_centimes=fee,
    )

    credit.balance_centimes = taken.balance_after_centimes
    credit.free_leads_left = taken.free_leads_after
    db.add(
        CreditTransaction(
            account_id=credit.id,
            type=taken.transaction_type,
            amount_centimes=taken.amount_centimes,
            balance_after_centimes=taken.balance_after_centimes,
            reason=reason or taken.reason,
            offer_id=offer.id,
            job_id=job_id,
        )
    )

    return Charge(
        fee_centimes=0 if taken.amount_centimes == 0 else fee,
        taken_centimes=-taken.amount_centimes,
        balance_after_centimes=taken.balance_after_centimes,
    )
