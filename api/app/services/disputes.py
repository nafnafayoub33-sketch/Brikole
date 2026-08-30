"""C8, D1 and D2 — opening an argument, and settling it.

The constraint that shapes every method here: **a moderator sees no money.**
He can hand the lead fee back, because the platform took it and he is the one
who decides it was taken for nothing — but he never learns a balance, a
top-up or a total. That separation is why the role is not a weaker admin, and
it is enforced by what these methods return, not by what a screen renders.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dispute import (
    DISPUTABLE,
    at_fault_party,
    refund_allowed,
    validate_dispute,
    within_window,
)
from app.core.enums import (
    DisputeStatus,
    DisputeVerdict,
    Role,
    TransactionType,
    UserStatus,
)
from app.core.errors import DomainError, ErrorCode
from app.core.policy import SettingKey
from app.models.base import utcnow
from app.models.credit import CreditAccount, CreditTransaction
from app.models.dispute import Dispute, DisputeMessage
from app.models.job import Job
from app.models.offer import Offer
from app.models.user import User
from app.repositories.catalog import SettingsRepository
from app.repositories.disputes import DisputeRepository
from app.repositories.jobs import JobRepository
from app.schemas.dispute import DisputeMessageIn, NewDisputeIn, ResolveDisputeIn
from app.services import audit
from app.services.audit import AuditAction

#: How long a suspension handed down here lasts. A moderator may pause somebody
#: for two days; taking an account away for good is an admin's decision.
SUSPENSION_HOURS = 48

STAFF = frozenset({Role.MODERATOR, Role.ADMIN})


class DisputeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DisputeRepository(db)
        self.jobs = JobRepository(db)
        self.settings = SettingsRepository(db)

    # -- C8 --------------------------------------------------------------

    def open(self, user: User, job_id: int, payload: NewDisputeIn) -> Dispute:
        job = self.jobs.get(job_id)
        if job is None:
            raise DomainError(ErrorCode.NOT_FOUND)

        opener, against = self._sides(user, job)

        if job.status not in DISPUTABLE:
            # Nothing has happened yet to argue about, or somebody already
            # cancelled and that settled it.
            raise DomainError(ErrorCode.CONFLICT, status=job.status.value)

        days = self.settings.get_int(SettingKey.DISPUTE_WINDOW_DAYS)
        if not within_window(job.finished_at, utcnow(), days=days):
            raise DomainError(ErrorCode.CONFLICT, reason="outside_window", days=days)

        if self.repo.for_job(job.id) is not None:
            raise DomainError(ErrorCode.CONFLICT, reason="already_open")

        try:
            new = validate_dispute(
                reason=payload.reason,
                description=payload.description,
                evidence_paths=payload.evidence_paths,
            )
        except ValueError as error:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field=str(error)) from error

        dispute = Dispute(
            job_id=job.id,
            opened_by_id=opener.id,
            against_id=against.id,
            reason=new.reason,
            description=new.description,
            status=DisputeStatus.OPEN,
        )
        self.db.add(dispute)
        self.db.flush()

        # Evidence rides in as the first message, so the thread reads in order
        # rather than having a separate box nobody scrolls to.
        for path in new.evidence_paths:
            self.db.add(
                DisputeMessage(
                    dispute_id=dispute.id,
                    author_id=user.id,
                    body="",
                    attachment_url=path,
                    is_internal=False,
                )
            )

        self.db.commit()
        self.db.refresh(dispute)
        return dispute

    # -- reading ---------------------------------------------------------

    def mine(self, user: User, *, page: int = 1, per_page: int = 20) -> tuple[list[Dispute], int]:
        return self.repo.mine(user.id, page=page, per_page=per_page)

    def queue(
        self, user: User, *, tab: str = "open", page: int = 1, per_page: int = 20
    ) -> tuple[list[Dispute], int]:
        self._require_staff(user)

        if tab == "mine":
            condition = Dispute.claimed_by_id == user.id
        elif tab == "resolved":
            condition = Dispute.status == DisputeStatus.RESOLVED
        else:
            condition = Dispute.status == DisputeStatus.OPEN

        return self.repo.queue(condition, page=page, per_page=per_page)

    def get(self, user: User, dispute_id: int) -> Dispute:
        dispute = self.repo.get(dispute_id)
        if dispute is None:
            raise DomainError(ErrorCode.NOT_FOUND)

        if user.role in STAFF:
            return dispute
        if user.id in (dispute.opened_by_id, dispute.against_id):
            return dispute
        raise DomainError(ErrorCode.NOT_FOUND)

    def visible_messages(self, user: User, dispute: Dispute) -> list[DisputeMessage]:
        """Internal notes are filtered here, not in the serialiser and never in
        the screen: a note a moderator wrote about somebody must not be one
        forgotten `if` away from that person reading it."""
        if user.role in STAFF:
            return list(dispute.messages)
        return [message for message in dispute.messages if not message.is_internal]

    # -- D1 --------------------------------------------------------------

    def claim(self, user: User, dispute_id: int) -> Dispute:
        """Take the case, so a second moderator does not arbitrate it too."""
        self._require_staff(user)
        dispute = self.get(user, dispute_id)

        if dispute.status is DisputeStatus.RESOLVED:
            raise DomainError(ErrorCode.CONFLICT, status=dispute.status.value)
        if dispute.claimed_by_id is not None and dispute.claimed_by_id != user.id:
            raise DomainError(ErrorCode.CONFLICT, reason="already_claimed")

        dispute.status = DisputeStatus.CLAIMED
        dispute.claimed_by_id = user.id
        dispute.claimed_at = utcnow()
        self.db.commit()
        self.db.refresh(dispute)
        return dispute

    # -- messages --------------------------------------------------------

    def add_message(self, user: User, dispute_id: int, payload: DisputeMessageIn) -> DisputeMessage:
        dispute = self.get(user, dispute_id)

        if dispute.status is DisputeStatus.RESOLVED:
            raise DomainError(ErrorCode.CONFLICT, status=dispute.status.value)

        internal = payload.is_internal and user.role in STAFF
        if payload.is_internal and user.role not in STAFF:
            # Not silently downgraded: a party asking for an internal note is
            # either confused or probing, and both deserve an answer.
            raise DomainError(ErrorCode.FORBIDDEN, reason="internal_note")

        body = " ".join(payload.body.split())
        if not body:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="body")

        message = DisputeMessage(
            dispute_id=dispute.id, author_id=user.id, body=body, is_internal=internal
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    # -- D2 --------------------------------------------------------------

    def resolve(
        self, user: User, dispute_id: int, payload: ResolveDisputeIn, *, ip: str | None = None
    ) -> Dispute:
        """Decide it, and carry out the one or two things a verdict may do."""
        self._require_staff(user)
        dispute = self.get(user, dispute_id)

        if dispute.status is DisputeStatus.RESOLVED:
            raise DomainError(ErrorCode.CONFLICT, status=dispute.status.value)
        if dispute.claimed_by_id != user.id:
            # Deciding a case somebody else is working is how two moderators
            # reach two verdicts on one argument.
            raise DomainError(ErrorCode.CONFLICT, reason="not_claimed_by_you")

        note = " ".join(payload.note.split())
        if not note:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="note")

        if payload.refund_lead_fee and not refund_allowed(payload.verdict):
            # A refund is not a way of splitting the difference.
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                field="refund_lead_fee",
                verdict=payload.verdict.value,
            )

        job = self.repo.job_for(dispute)

        refunded = False
        if payload.refund_lead_fee:
            refunded = self._refund_lead_fee(job, user, dispute)

        suspended: str | None = None
        if payload.suspend_at_fault:
            suspended = self._suspend_at_fault(dispute, job, payload.verdict, note)

        dispute.status = DisputeStatus.RESOLVED
        dispute.verdict = payload.verdict
        dispute.resolution_note = note
        dispute.lead_fee_refunded = refunded
        dispute.resolved_at = utcnow()

        audit.record(
            self.db,
            actor=user,
            action=AuditAction.DISPUTE_RESOLVED,
            target_type="dispute",
            target_id=dispute.id,
            before={"status": DisputeStatus.CLAIMED.value},
            after={
                "status": DisputeStatus.RESOLVED.value,
                "verdict": payload.verdict.value,
                "lead_fee_refunded": refunded,
                "suspended": suspended,
            },
            note=note,
            ip=ip,
        )

        self.db.commit()
        self.db.refresh(dispute)
        return dispute

    def _refund_lead_fee(self, job: Job, actor: User, dispute: Dispute) -> bool:
        """Hand the fee back, with the ledger row that explains it.

        Returns False when there is nothing to give back — a free lead cost him
        nothing, and saying "refunded" about zero would be a lie on the record.
        """
        offer = self.db.get(Offer, job.offer_id)
        fee = offer.lead_fee_centimes if offer is not None else None
        if not fee:
            return False

        credit = self.db.execute(
            select(CreditAccount).where(CreditAccount.provider_id == job.provider_id)
        ).scalar_one_or_none()
        if credit is None:
            return False

        credit.balance_centimes += fee
        self.db.add(
            CreditTransaction(
                account_id=credit.id,
                type=TransactionType.REFUND,
                amount_centimes=fee,
                balance_after_centimes=credit.balance_centimes,
                reason="dispute_refund",
                offer_id=offer.id if offer else None,
                job_id=job.id,
                actor_id=actor.id,
            )
        )
        # The fee is spent once. Clearing it stops a second dispute on the same
        # job handing it back twice.
        if offer is not None:
            offer.lead_fee_centimes = 0
        return True

    def _suspend_at_fault(
        self, dispute: Dispute, job: Job, verdict: DisputeVerdict, note: str
    ) -> str | None:
        side = at_fault_party(verdict)
        if side is None:
            return None

        target = (
            self.repo.user(job.client_id)
            if side == "client"
            else self.jobs.provider_for(job).user
        )
        if target is None:
            return None

        target.status = UserStatus.SUSPENDED
        target.suspended_until = utcnow() + timedelta(hours=SUSPENSION_HOURS)
        target.suspension_reason = note
        return side

    # -- helpers ---------------------------------------------------------

    def _sides(self, user: User, job: Job) -> tuple[User, User]:
        """Who is opening it, and against whom."""
        if user.role is Role.CLIENT and job.client_id == user.id:
            provider = self.jobs.provider_for(job)
            return user, provider.user

        if user.role is Role.PROVIDER:
            profile = self.repo.profile_for_user(user.id)
            if profile is not None and profile.id == job.provider_id:
                client = self.repo.user(job.client_id)
                if client is None:
                    raise DomainError(ErrorCode.NOT_FOUND)
                return user, client

        # Not his job. Not found rather than forbidden, as everywhere else.
        raise DomainError(ErrorCode.NOT_FOUND)

    def _require_staff(self, user: User) -> None:
        if user.role not in STAFF:
            raise DomainError(ErrorCode.FORBIDDEN, role=user.role.value)
