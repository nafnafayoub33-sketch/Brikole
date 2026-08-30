"""The balance, the ledger behind it, and topping it up (M9 and A5)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import TopupStatus, TransactionType
from app.core.topup import MAX_REFERENCE
from app.schemas.common import ApiModel


class BankDetailsOut(ApiModel):
    """Where he actually sends the money. Edited by an admin at A7.

    Empty strings when nobody has filled them in yet, and M9 says so rather
    than showing him a blank card to transfer into.
    """

    bank_name: str
    account_holder: str
    rib: str
    instructions: str


class LedgerEntryOut(ApiModel):
    id: int
    type: TransactionType
    #: Signed: negative took money out.
    amount_centimes: int
    balance_after_centimes: int
    #: A machine-readable note, translated for display on the web side.
    reason: str
    job_id: int | None
    created_at: datetime


class TopupOut(ApiModel):
    id: int
    amount_centimes: int
    reference: str
    status: TopupStatus
    created_at: datetime
    reviewed_at: datetime | None
    rejection_reason: str | None
    #: Private bucket — a path, never a URL. Only A5 fetches the bytes.
    receipt_path: str | None


class NewTopupIn(BaseModel):
    amount_centimes: int = Field(gt=0)
    reference: str = Field(min_length=1, max_length=MAX_REFERENCE)
    receipt_path: str | None = None


class CreditPageOut(ApiModel):
    """Everything M9 renders, in one request."""

    balance_centimes: int
    free_leads_left: int
    default_lead_fee_centimes: int
    can_take_work: bool

    bank: BankDetailsOut
    preset_amounts: list[int]

    #: Newest first. A pending one is what M9 puts at the top.
    topups: list[TopupOut]
    ledger: list[LedgerEntryOut]


# -- A5 ------------------------------------------------------------------


class TopupProviderOut(ApiModel):
    id: int
    full_name: str
    phone: str
    balance_centimes: int


class PendingTopupOut(TopupOut):
    """A5's queue row: the claim, and who made it."""

    provider: TopupProviderOut


class RejectTopupIn(BaseModel):
    #: What the tradesman reads at M9 to fix it. A rejection with no reason is
    #: refused by the service, not merely discouraged here.
    reason: str = Field(min_length=1, max_length=500)
