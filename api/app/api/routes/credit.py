"""M9 and A5 — his balance and the transfers that fill it."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.core import boost as boost_rules
from app.core.enums import Role
from app.core.topup import PRESET_AMOUNTS
from app.deps import CurrentUser, DbSession, require_roles
from app.models.base import utcnow
from app.models.credit import CreditAccount, TopupRequest
from app.models.provider import ProviderProfile
from app.schemas.common import Page
from app.schemas.credit import (
    BoostOut,
    CreditPageOut,
    LedgerEntryOut,
    NewTopupIn,
    PendingTopupOut,
    RejectTopupIn,
    TopupOut,
    TopupProviderOut,
)
from app.services.credit import CreditService

router = APIRouter(tags=["credit"])


@router.get(
    "/pro/credit/page",
    response_model=CreditPageOut,
    dependencies=[Depends(require_roles(Role.PROVIDER))],
)
def credit_page(user: CurrentUser, db: DbSession) -> CreditPageOut:
    """M9 in one request: the balance, the bank details, his claims, his ledger."""
    service = CreditService(db)
    profile, account, topups, ledger = service.page(user)

    return CreditPageOut(
        balance_centimes=account.balance_centimes,
        free_leads_left=account.free_leads_left,
        default_lead_fee_centimes=service.offers.default_fee(),
        can_take_work=service.offers.can_take_work(profile),
        boost=_boost(service, profile, account.balance_centimes),
        bank=service.bank_details(),
        preset_amounts=list(PRESET_AMOUNTS),
        topups=[_topup(topup) for topup in topups],
        ledger=[LedgerEntryOut.model_validate(row) for row in ledger],
    )


@router.post(
    "/pro/boost",
    response_model=BoostOut,
    dependencies=[Depends(require_roles(Role.PROVIDER))],
)
def buy_boost(user: CurrentUser, db: DbSession) -> BoostOut:
    """Buy thirty days of placement. Answers 402 when the balance is short —
    nobody is waiting on this one, so he is told to top up rather than put
    into debt for something he chose."""
    service = CreditService(db)
    profile = service.buy_boost(user)
    account = service.repo.account_for(profile.id)
    return _boost(service, profile, account.balance_centimes if account else 0)


def _boost(service: CreditService, profile: ProviderProfile, balance: int) -> BoostOut:
    price = service.boost_price()
    return BoostOut(
        active=boost_rules.is_active(profile.boosted_until, utcnow()),
        expires_at=profile.boosted_until,
        price_centimes=price,
        days=boost_rules.BOOST_DAYS,
        affordable=balance >= price,
    )


@router.post(
    "/pro/topups",
    response_model=TopupOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.PROVIDER))],
)
def submit_topup(payload: NewTopupIn, user: CurrentUser, db: DbSession) -> TopupOut:
    """Records the claim. Moves no money — only A5 does that."""
    return _topup(CreditService(db).submit_topup(user, payload))


@router.get(
    "/admin/topups",
    response_model=Page[PendingTopupOut],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def topup_queue(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[PendingTopupOut]:
    """A5. Oldest first — it is a queue."""
    rows, total = CreditService(db).queue(page=page, per_page=per_page)
    return Page[PendingTopupOut](
        items=[_pending(topup, profile, account) for topup, profile, account in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/admin/topups/{topup_id}/approve",
    response_model=TopupOut,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def approve_topup(
    topup_id: int, user: CurrentUser, db: DbSession, request: Request
) -> TopupOut:
    return _topup(CreditService(db).approve(user, topup_id, ip=_ip(request)))


@router.post(
    "/admin/topups/{topup_id}/reject",
    response_model=TopupOut,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def reject_topup(
    topup_id: int,
    payload: RejectTopupIn,
    user: CurrentUser,
    db: DbSession,
    request: Request,
) -> TopupOut:
    return _topup(
        CreditService(db).reject(user, topup_id, reason=payload.reason, ip=_ip(request))
    )


def _topup(topup: TopupRequest) -> TopupOut:
    return TopupOut(
        id=topup.id,
        amount_centimes=topup.amount_centimes,
        reference=topup.reference,
        status=topup.status,
        created_at=topup.created_at,
        reviewed_at=topup.reviewed_at,
        rejection_reason=topup.rejection_reason,
        receipt_path=topup.receipt_url,
    )


def _pending(
    topup: TopupRequest, profile: ProviderProfile, account: CreditAccount | None
) -> PendingTopupOut:
    return PendingTopupOut(
        **_topup(topup).model_dump(),
        provider=TopupProviderOut(
            id=profile.id,
            full_name=profile.user.full_name,
            phone=profile.user.phone,
            balance_centimes=account.balance_centimes if account else 0,
        ),
    )


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None
