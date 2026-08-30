"""M4, M5 and M6 — the feed, the offer, and the offers he has sent."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import OfferStatus, ProviderStatus, RequestStatus, Role
from app.core.errors import DomainError, ErrorCode
from app.core.offer import can_send_offer, validate_offer
from app.core.policy import SettingKey, lead_fee_for
from app.models.base import utcnow
from app.models.credit import CreditAccount
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User
from app.repositories.catalog import SettingsRepository
from app.repositories.offers import OfferRepository
from app.schemas.offer import NewOfferIn


class OfferService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OfferRepository(db)
        self.settings = SettingsRepository(db)

    # -- who is asking ---------------------------------------------------

    def profile_for(self, user: User) -> ProviderProfile:
        """His approved profile, or the reason he has no feed.

        A pending or rejected tradesman is not shown work: he would answer it,
        and the client would receive an offer from somebody the platform has
        not vouched for.
        """
        if user.role is not Role.PROVIDER:
            raise DomainError(ErrorCode.FORBIDDEN, role=user.role.value)

        profile = self.db.execute(
            select(ProviderProfile).where(ProviderProfile.user_id == user.id)
        ).scalar_one_or_none()
        if profile is None:
            raise DomainError(ErrorCode.NOT_FOUND)
        if profile.status is not ProviderStatus.APPROVED:
            raise DomainError(ErrorCode.FORBIDDEN, reason="not_approved",
                              status=profile.status.value)
        return profile

    # -- money -----------------------------------------------------------

    def default_fee(self) -> int:
        return self.settings.get_int(SettingKey.DEFAULT_LEAD_FEE)

    def fee_for_request(self, request: ServiceRequest) -> int:
        return lead_fee_for(request.trade.lead_fee_centimes, self.default_fee())

    def credit(self, profile: ProviderProfile) -> CreditAccount:
        account = self.repo.credit_account(profile.id)
        if account is None:
            # Every approved tradesman is given one at M1; a missing account is
            # a bug, and treating it as free credit would hide it.
            account = CreditAccount(
                provider_id=profile.id, balance_centimes=0, free_leads_left=0
            )
            self.db.add(account)
            self.db.commit()
        return account

    def can_take_work(self, profile: ProviderProfile) -> bool:
        account = self.credit(profile)
        return can_send_offer(
            free_leads_left=account.free_leads_left,
            balance_centimes=account.balance_centimes,
            fee_centimes=self.default_fee(),
        )

    def _require_credit(self, profile: ProviderProfile, fee_centimes: int) -> None:
        account = self.credit(profile)
        if not can_send_offer(
            free_leads_left=account.free_leads_left,
            balance_centimes=account.balance_centimes,
            fee_centimes=fee_centimes,
        ):
            raise DomainError(
                ErrorCode.INSUFFICIENT_CREDIT,
                balance_centimes=account.balance_centimes,
                fee_centimes=fee_centimes,
            )

    # -- M4 --------------------------------------------------------------

    def feed(
        self,
        user: User,
        *,
        trade_id: int | None = None,
        urgency: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[ProviderProfile, list[ServiceRequest], dict[int, Offer], int]:
        """Work he could take — and nothing at all when he cannot take any.

        Showing a tradesman with an empty balance a feed he cannot answer is
        the cruellest version of this screen: he reads it, picks one, writes a
        price, and only then is told no.
        """
        profile = self.profile_for(user)
        self._require_credit(profile, self.default_fee())

        rows, total = self.repo.feed(
            profile, trade_id=trade_id, urgency=urgency, page=page, per_page=per_page
        )
        mine = self.repo.his_offers_on(profile.id, [row.id for row in rows])
        return profile, rows, mine, total

    # -- M5 --------------------------------------------------------------

    def request_detail(self, user: User, request_id: int) -> tuple[
        ProviderProfile, ServiceRequest, Offer | None
    ]:
        profile = self.profile_for(user)
        request = self.repo.open_request(request_id)

        # Not in his trades or not in his city is *not found*: it was never his
        # to see, and saying "forbidden" would confirm it exists.
        if (
            request is None
            or request.city_id != profile.city_id
            or request.trade_id not in {trade.id for trade in profile.trades}
        ):
            raise DomainError(ErrorCode.NOT_FOUND)

        # The same gate as the feed, and for the same reason. Without it a
        # blocked tradesman reaches this page by URL or by a stale link, writes
        # a price, and is refused only on send — which is the exact thing the
        # feed closing was meant to prevent. Charged against *this* request's
        # fee, since we have the request in hand.
        self._require_credit(profile, self.fee_for_request(request))

        return profile, request, self.repo.his_offer_on(profile.id, request_id)

    def send_offer(self, user: User, request_id: int, payload: NewOfferIn) -> Offer:
        """Write or replace his offer on a request.

        One offer per tradesman per request, so a second send edits the first
        rather than stacking under it — which is also what the unique index
        says, and this is the friendly half of it.
        """
        profile, request, existing = self.request_detail(user, request_id)

        if request.status is not RequestStatus.OPEN:
            raise DomainError(ErrorCode.CONFLICT, status=request.status.value)

        fee = self.fee_for_request(request)
        self._require_credit(profile, fee)

        try:
            new = validate_offer(
                price_centimes=payload.price_centimes, message=payload.message
            )
        except ValueError as error:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field=str(error)) from error

        available = _clean_available_from(payload.available_from)

        if existing is not None:
            if existing.status is OfferStatus.ACCEPTED:
                raise DomainError(ErrorCode.CONFLICT, reason="already_accepted")
            existing.price_centimes = new.price_centimes
            existing.message = new.message
            existing.available_from = available
            # Editing a withdrawn offer puts it back in front of the client.
            existing.status = OfferStatus.PENDING
            existing.responded_at = None
            offer = existing
        else:
            offer = Offer(
                request_id=request.id,
                provider_id=profile.id,
                price_centimes=new.price_centimes,
                message=new.message,
                available_from=available,
                status=OfferStatus.PENDING,
            )
            self.db.add(offer)
            request.offers_count += 1

        self.db.commit()
        self.db.refresh(offer)
        return offer

    def withdraw_offer(self, user: User, offer_id: int) -> Offer:
        profile = self.profile_for(user)
        offer = self.db.get(Offer, offer_id)
        if offer is None or offer.provider_id != profile.id:
            raise DomainError(ErrorCode.NOT_FOUND)

        if offer.status is not OfferStatus.PENDING:
            # An accepted offer is a job now, and a job is cancelled at M7 —
            # where the client finds out.
            raise DomainError(ErrorCode.CONFLICT, status=offer.status.value)

        offer.status = OfferStatus.WITHDRAWN
        offer.responded_at = utcnow()
        self.db.commit()
        return offer

    # -- M6 --------------------------------------------------------------

    def list_his(
        self, user: User, *, page: int = 1, per_page: int = 20
    ) -> tuple[list[Offer], dict[int, int], int]:
        profile = self.profile_for(user)
        rows, total = self.repo.list_his(profile.id, page=page, per_page=per_page)
        jobs = self.repo.jobs_for_offers([offer.id for offer in rows])
        return rows, jobs, total


def _clean_available_from(value: datetime | None) -> datetime | None:
    """A date in the past is a typo, not a promise.

    Nudged to now rather than refused: he is standing in someone's kitchen
    typing on a phone, and rejecting the whole offer over a mistyped day is a
    worse outcome than quietly reading it as "straight away".
    """
    if value is None:
        return None
    naive = value.replace(tzinfo=None) if value.tzinfo else value
    return max(naive, utcnow() - timedelta(minutes=1))
