"""A client's own requests, the offers they have drawn, and A4's browser."""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import RequestStatus
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User

#: Everything C2 and C3 render off a request, loaded in one round trip each
#: rather than one per row.
_FULL = (
    selectinload(ServiceRequest.photos),
    selectinload(ServiceRequest.trade),
    selectinload(ServiceRequest.city),
)


#: Digits a request id can have. `BIGINT` holds nineteen; anything longer is
#: somebody pasting the wrong thing into the box.
_MAX_ID_DIGITS = 19


class RequestRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, request_id: int) -> ServiceRequest | None:
        return self.db.execute(
            select(ServiceRequest).where(ServiceRequest.id == request_id).options(*_FULL)
        ).scalar_one_or_none()

    def list_for_client(
        self, client_id: int, *, page: int = 1, per_page: int = 20
    ) -> tuple[list[ServiceRequest], int]:
        base = select(ServiceRequest).where(ServiceRequest.client_id == client_id)
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        rows = list(
            self.db.execute(
                base.options(*_FULL)
                # Newest first, with the id breaking ties so pages never overlap.
                .order_by(ServiceRequest.created_at.desc(), ServiceRequest.id.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            .scalars()
            .unique()
        )
        return rows, total

    def count_open_for_client(self, client_id: int) -> int:
        return self.db.execute(
            select(func.count())
            .select_from(ServiceRequest)
            .where(
                ServiceRequest.client_id == client_id,
                ServiceRequest.status == RequestStatus.OPEN,
            )
        ).scalar_one()

    # -- A4: the admin's browser -----------------------------------------

    def page(
        self,
        *,
        query: str | None = None,
        status: RequestStatus | None = None,
        city_id: int | None = None,
        trade_id: int | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> tuple[list[tuple[ServiceRequest, User]], int]:
        """Every request, narrowed, newest first — with its client attached.

        The client comes back on the same query rather than one lookup per
        row: this list is read while somebody is on the phone, and twenty-five
        extra round trips is the difference between answering and stalling.
        """
        stmt = select(ServiceRequest, User).join(
            User, User.id == ServiceRequest.client_id
        )

        if query:
            stmt = stmt.where(_matches(query))
        if status is not None:
            stmt = stmt.where(ServiceRequest.status == status)
        if city_id is not None:
            stmt = stmt.where(ServiceRequest.city_id == city_id)
        if trade_id is not None:
            stmt = stmt.where(ServiceRequest.trade_id == trade_id)

        total = int(
            self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        )

        rows = self.db.execute(
            stmt.options(
                selectinload(ServiceRequest.trade), selectinload(ServiceRequest.city)
            )
            .order_by(ServiceRequest.created_at.desc(), ServiceRequest.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()
        return [(request, user) for request, user in rows], total

    def list_offers(self, request_id: int) -> list[Offer]:
        """Newest first, with the tradesman behind each one."""
        return list(
            self.db.execute(
                select(Offer)
                .where(Offer.request_id == request_id)
                .options(
                    selectinload(Offer.provider).selectinload(ProviderProfile.user),
                    selectinload(Offer.provider).selectinload(ProviderProfile.city),
                )
                .order_by(Offer.created_at.desc(), Offer.id.desc())
            )
            .scalars()
            .unique()
        )


def _matches(query: str) -> ColumnElement[bool]:
    """One box: a request id, a title, a client's name, or his phone.

    Support is given whatever the caller has to hand, which is a phone number
    far more often than a request id. Phones are stored E.164 and spoken
    nationally, so `0612…` has to find `+212612…`. A bare number is *also*
    tried as an id, because "request 1082" is the other half of the calls —
    both, rather than a mode switch nobody would find.

    `%` and `_` are escaped so a stray underscore is not quietly a wildcard.
    """
    needle = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{needle}%"

    clauses: list[ColumnElement[bool]] = [
        ServiceRequest.title.like(pattern, escape="\\"),
        User.full_name.like(pattern, escape="\\"),
        User.phone.like(pattern, escape="\\"),
    ]

    digits = needle.lstrip("+")
    if digits.startswith("0") and digits[1:].isdigit():
        clauses.append(User.phone.like(f"%+212{digits[1:]}%", escape="\\"))
    # Bounded before it reaches the column: a forty-digit "id" is not a
    # request, and MySQL raises on a BIGINT it cannot hold rather than
    # returning nothing.
    if needle.isdigit() and len(needle) <= _MAX_ID_DIGITS:
        clauses.append(ServiceRequest.id == int(needle))

    return or_(*clauses)
