"""Posting, reading and cancelling a job request."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.enums import OfferStatus, RequestStatus, Role
from app.core.errors import DomainError, ErrorCode
from app.core.policy import SettingKey
from app.core.service_request import validate_request
from app.models.base import utcnow
from app.models.catalog import City, Trade
from app.models.offer import Offer
from app.models.request import RequestPhoto, ServiceRequest
from app.models.user import User
from app.repositories.catalog import SettingsRepository
from app.repositories.requests import RequestRepository
from app.schemas.request import NewRequestIn


class RequestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RequestRepository(db)
        self.settings = SettingsRepository(db)

    def list_own(
        self, user: User, *, page: int = 1, per_page: int = 20
    ) -> tuple[list[ServiceRequest], int]:
        return self.repo.list_for_client(user.id, page=page, per_page=per_page)

    def get_own(self, user: User, request_id: int) -> ServiceRequest:
        request = self.repo.get(request_id)

        # Somebody else's request is *not found*, not "forbidden": the id space
        # is guessable and a 403 confirms one exists.
        if request is None or request.client_id != user.id:
            raise DomainError(ErrorCode.NOT_FOUND)
        return request

    def list_offers(self, user: User, request_id: int) -> list[Offer]:
        """Every offer his request has received, newest first.

        Everything, not only the live ones: `offers_count` is what C2 shouts,
        and a list that quietly drops the withdrawn and the rejected makes that
        number a lie. A closed request is also a record of who answered it and
        who he did not pick.
        """
        self.get_own(user, request_id)  # 404s if it is not his.
        return self.repo.list_offers(request_id)

    def open_count(self, user: User) -> int:
        return self.repo.count_open_for_client(user.id)

    def create(self, user: User, payload: NewRequestIn) -> ServiceRequest:
        if user.role is not Role.CLIENT:
            raise DomainError(ErrorCode.FORBIDDEN, role=user.role.value)

        cap = self.settings.get_int(SettingKey.MAX_OPEN_REQUESTS_PER_CLIENT)
        if self.open_count(user) >= cap:
            # Not a validation failure on any one field: the request is fine,
            # there are simply too many of them already.
            raise DomainError(ErrorCode.CONFLICT, reason="too_many_open_requests", max=cap)

        new = validate_request(
            trade_id=payload.trade_id,
            city_id=payload.city_id,
            title=payload.title,
            description=payload.description,
            address=payload.address,
            latitude=payload.latitude,
            longitude=payload.longitude,
            urgency=payload.urgency,
            budget_min_centimes=payload.budget_min_centimes,
            budget_max_centimes=payload.budget_max_centimes,
            photo_paths=payload.photo_paths,
        )

        trade = self.db.get(Trade, new.trade_id)
        if trade is None or not trade.is_active:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="trade_id")

        city = self.db.get(City, new.city_id)
        if city is None or not city.is_active:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="city_id")

        days = self.settings.get_int(SettingKey.REQUEST_EXPIRY_DAYS)
        request = ServiceRequest(
            client_id=user.id,
            trade_id=new.trade_id,
            city_id=new.city_id,
            title=new.title,
            description=new.description,
            address=new.address,
            latitude=new.latitude,
            longitude=new.longitude,
            urgency=new.urgency,
            budget_min_centimes=new.budget_min_centimes,
            budget_max_centimes=new.budget_max_centimes,
            status=RequestStatus.OPEN,
            offers_count=0,
            expires_at=utcnow() + timedelta(days=days),
        )
        self.db.add(request)
        self.db.flush()

        for order, path in enumerate(new.photo_paths):
            request.photos.append(RequestPhoto(url=f"/api/v1/uploads/{path}", sort_order=order))

        self.db.commit()
        return self.get_own(user, request.id)

    def decline_offer(self, user: User, request_id: int, offer_id: int) -> Offer:
        """Turn one offer down without choosing another.

        Separate from accepting on purpose: a client who knows this price is
        wrong should be able to clear it out of his list, and a tradesman is
        better off learning it now than sitting in a queue that has silently
        moved past him.
        """
        request = self.get_own(user, request_id)

        if request.status is not RequestStatus.OPEN:
            raise DomainError(ErrorCode.CONFLICT, status=request.status.value)

        offer = self.db.get(Offer, offer_id)
        if offer is None or offer.request_id != request.id:
            raise DomainError(ErrorCode.NOT_FOUND)

        if offer.status is not OfferStatus.PENDING:
            raise DomainError(ErrorCode.CONFLICT, status=offer.status.value)

        offer.status = OfferStatus.REJECTED
        offer.responded_at = utcnow()

        self.db.commit()
        self.db.refresh(offer)
        return offer

    def update(self, user: User, request_id: int, payload: NewRequestIn) -> ServiceRequest:
        """Rewrite a request nobody has answered yet.

        The moment one offer exists, editing is off: a tradesman priced the
        job as it was written, and changing the job under his quote is how a
        450 DH answer to "unblock a sink" becomes an answer to "retile the
        bathroom". After that the way to change the work is to cancel and post
        again, which costs him nothing and costs the tradesmen their guess.
        """
        request = self.get_own(user, request_id)

        if request.status is not RequestStatus.OPEN:
            raise DomainError(ErrorCode.CONFLICT, status=request.status.value)
        if request.offers_count > 0:
            raise DomainError(ErrorCode.CONFLICT, reason="already_answered")

        new = validate_request(
            trade_id=payload.trade_id,
            city_id=payload.city_id,
            title=payload.title,
            description=payload.description,
            address=payload.address,
            latitude=payload.latitude,
            longitude=payload.longitude,
            urgency=payload.urgency,
            budget_min_centimes=payload.budget_min_centimes,
            budget_max_centimes=payload.budget_max_centimes,
            photo_paths=payload.photo_paths,
        )

        trade = self.db.get(Trade, new.trade_id)
        if trade is None or not trade.is_active:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="trade_id")

        city = self.db.get(City, new.city_id)
        if city is None or not city.is_active:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="city_id")

        request.trade_id = new.trade_id
        request.city_id = new.city_id
        request.title = new.title
        request.description = new.description
        request.address = new.address
        request.latitude = new.latitude
        request.longitude = new.longitude
        request.urgency = new.urgency
        request.budget_min_centimes = new.budget_min_centimes
        request.budget_max_centimes = new.budget_max_centimes

        # Photos are replaced wholesale: the wizard sends the full set it holds,
        # so a diff would only be a way to disagree with it.
        request.photos.clear()
        self.db.flush()
        for order, path in enumerate(new.photo_paths):
            request.photos.append(RequestPhoto(url=f"/api/v1/uploads/{path}", sort_order=order))

        self.db.commit()
        return self.get_own(user, request_id)

    def cancel(self, user: User, request_id: int, *, reason: str | None) -> ServiceRequest:
        request = self.get_own(user, request_id)

        if request.status is not RequestStatus.OPEN:
            # An assigned request is cancelled through the job, where the
            # tradesman finds out. Cancelling it here would leave him working.
            raise DomainError(ErrorCode.CONFLICT, status=request.status.value)

        request.status = RequestStatus.CANCELLED
        request.cancelled_at = utcnow()
        request.cancel_reason = " ".join((reason or "").split()) or None

        self.db.commit()
        return self.get_own(user, request_id)
