"""M9 and A5 — the balance, its ledger, and the transfers that fill it.

The invariant this file protects: `CreditAccount.balance_centimes` is a cache
of `credit_transactions`. Every change to it is written together with the row
that explains it, in one transaction. There is exactly one place in here that
moves a balance, and it writes the ledger row two lines later.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import boost as boost_rules
from app.core.enums import Role, TopupStatus, TransactionType
from app.core.errors import DomainError, ErrorCode
from app.core.policy import SettingKey
from app.core.topup import validate_topup
from app.models.base import utcnow
from app.models.credit import CreditAccount, CreditTransaction, TopupRequest
from app.models.provider import ProviderProfile
from app.models.user import User
from app.repositories.catalog import SettingsRepository
from app.repositories.credit import CreditRepository
from app.schemas.credit import BankDetailsOut, NewTopupIn
from app.services import audit
from app.services.audit import AuditAction
from app.services.offers import OfferService

#: One at a time. Two pending claims from the same tradesman are two rows an
#: admin has to reconcile against one bank statement, and the second is almost
#: always him thinking the first did not go through.
ONE_PENDING = "topup_already_pending"


class CreditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CreditRepository(db)
        self.settings = SettingsRepository(db)
        self.offers = OfferService(db)

    # -- M9 --------------------------------------------------------------

    def bank_details(self) -> BankDetailsOut:
        raw = self.settings.get(SettingKey.BANK_TRANSFER)
        values = raw if isinstance(raw, dict) else {}
        return BankDetailsOut(
            bank_name=str(values.get("bank_name", "")),
            account_holder=str(values.get("account_holder", "")),
            rib=str(values.get("rib", "")),
            instructions=str(values.get("instructions", "")),
        )

    def page(self, user: User) -> tuple[
        ProviderProfile, CreditAccount, list[TopupRequest], list[CreditTransaction]
    ]:
        profile = self.offers.profile_for(user)
        account = self.offers.credit(profile)
        return (
            profile,
            account,
            self.repo.topups_for(profile.id),
            self.repo.ledger(account.id),
        )

    # -- paid placement --------------------------------------------------

    def boost_price(self) -> int:
        return self.settings.get_int(SettingKey.BOOST_MONTHLY)

    def buy_boost(self, user: User) -> ProviderProfile:
        """Thirty days at the top of the list, taken from his balance.

        **This one refuses when he is short**, where the lead fee does not. The
        difference is who is waiting: a lead fee lands on a handshake two people
        have already made, and refusing there breaks the only flow that earns
        the platform anything. Nobody at all is waiting on a boost, so he is
        told to top up rather than put into debt for something he chose.
        """
        profile = self.offers.profile_for(user)
        account = self.offers.credit(profile)
        price = self.boost_price()

        try:
            bought = boost_rules.buy(
                boosted_until=profile.boosted_until,
                balance_centimes=account.balance_centimes,
                price_centimes=price,
                now=utcnow(),
            )
        except boost_rules.BoostRefused as error:
            raise DomainError(
                ErrorCode.INSUFFICIENT_CREDIT,
                needed_centimes=price,
                balance_centimes=account.balance_centimes,
            ) from error

        account.balance_centimes = bought.balance_after_centimes
        self.db.add(
            CreditTransaction(
                account_id=account.id,
                type=TransactionType.BOOST,
                amount_centimes=-bought.price_centimes,
                balance_after_centimes=bought.balance_after_centimes,
                reason="boost_bought",
            )
        )
        profile.boosted_until = bought.expires_at

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def submit_topup(self, user: User, payload: NewTopupIn) -> TopupRequest:
        """Record the claim. **This moves no money.**"""
        profile = self.offers.profile_for(user)

        if self.repo.has_pending(profile.id):
            raise DomainError(ErrorCode.CONFLICT, reason=ONE_PENDING)

        try:
            new = validate_topup(
                amount_centimes=payload.amount_centimes, reference=payload.reference
            )
        except ValueError as error:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field=str(error)) from error

        topup = TopupRequest(
            provider_id=profile.id,
            amount_centimes=new.amount_centimes,
            reference=new.reference,
            receipt_url=payload.receipt_path,
            status=TopupStatus.PENDING,
        )
        self.db.add(topup)
        self.db.commit()
        self.db.refresh(topup)
        return topup

    # -- A5 --------------------------------------------------------------

    def queue(self, *, page: int = 1, per_page: int = 20) -> tuple[
        list[tuple[TopupRequest, ProviderProfile, CreditAccount | None]], int
    ]:
        return self.repo.queue(page=page, per_page=per_page)

    def approve(self, admin: User, topup_id: int, *, ip: str | None = None) -> TopupRequest:
        """Confirm the transfer landed, and credit the balance for it.

        The only place in the product that adds money. The ledger row is
        written in the same transaction as the balance it explains — a balance
        with no matching row is the bug this whole module is shaped to prevent.
        """
        topup = self._claim(admin, topup_id)

        account = self.repo.account_for(topup.provider_id)
        if account is None:
            account = CreditAccount(
                provider_id=topup.provider_id, balance_centimes=0, free_leads_left=0
            )
            self.db.add(account)
            self.db.flush()

        before = account.balance_centimes
        account.balance_centimes = before + topup.amount_centimes
        self.db.add(
            CreditTransaction(
                account_id=account.id,
                type=TransactionType.TOPUP,
                amount_centimes=topup.amount_centimes,
                balance_after_centimes=account.balance_centimes,
                reason="topup_approved",
                topup_id=topup.id,
                actor_id=admin.id,
            )
        )

        topup.status = TopupStatus.APPROVED
        topup.reviewed_by_id = admin.id
        topup.reviewed_at = utcnow()

        audit.record(
            self.db,
            actor=admin,
            action=AuditAction.TOPUP_APPROVED,
            target_type="topup_request",
            target_id=topup.id,
            before={"status": TopupStatus.PENDING.value, "balance_centimes": before},
            after={
                "status": TopupStatus.APPROVED.value,
                "balance_centimes": account.balance_centimes,
            },
            note=topup.reference,
            ip=ip,
        )

        self.db.commit()
        self.db.refresh(topup)
        return topup

    def reject(
        self, admin: User, topup_id: int, *, reason: str, ip: str | None = None
    ) -> TopupRequest:
        """Decline it. Moves nothing, and says why."""
        cleaned = " ".join(reason.split())
        if not cleaned:
            # It is the only thing M9 can tell him to fix.
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="reason")

        topup = self._claim(admin, topup_id)
        topup.status = TopupStatus.REJECTED
        topup.reviewed_by_id = admin.id
        topup.reviewed_at = utcnow()
        topup.rejection_reason = cleaned

        audit.record(
            self.db,
            actor=admin,
            action=AuditAction.TOPUP_REJECTED,
            target_type="topup_request",
            target_id=topup.id,
            before={"status": TopupStatus.PENDING.value},
            after={"status": TopupStatus.REJECTED.value},
            note=cleaned,
            ip=ip,
        )

        self.db.commit()
        self.db.refresh(topup)
        return topup

    def _claim(self, admin: User, topup_id: int) -> TopupRequest:
        if admin.role is not Role.ADMIN:
            raise DomainError(ErrorCode.FORBIDDEN, role=admin.role.value)

        topup = self.db.get(TopupRequest, topup_id)
        if topup is None:
            raise DomainError(ErrorCode.NOT_FOUND)

        if topup.status is not TopupStatus.PENDING:
            # Two admins on one queue. Answering 409 beats crediting twice.
            raise DomainError(ErrorCode.CONFLICT, status=topup.status.value)

        return topup
