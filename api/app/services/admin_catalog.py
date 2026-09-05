"""A6 — editing the two lists everything else points at.

There is no delete in this module, and that is the design rather than an
omission. A trade has requests, offers, jobs and profiles hanging off it; a
city has all of that plus every tradesman who works there. Removing the row
would either take the history with it or leave dangling references, and both
are worse than a list with one extra entry in it. Deactivating stops the trade
being offered at C1 and closes its feed, and changes nothing that already
happened.

Every write is audited, for the same reason A7's are: these are the numbers
and the names the whole product runs on.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.catalog_rules import CityFields, TradeFields, validate_city, validate_trade
from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode
from app.models.catalog import City, Trade
from app.models.user import User
from app.repositories.catalog import AdminCatalogRepository, Usage
from app.services import audit
from app.services.audit import AuditAction


class AdminCatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AdminCatalogRepository(db)

    # -- reading ---------------------------------------------------------

    def trades(self) -> tuple[list[Trade], dict[int, Usage]]:
        return self.repo.trades(), self.repo.trade_usage()

    def cities(self) -> tuple[list[City], dict[int, Usage]]:
        return self.repo.cities(), self.repo.city_usage()

    # -- trades ----------------------------------------------------------

    def create_trade(
        self, admin: User, payload: dict[str, Any], *, ip: str | None = None
    ) -> Trade:
        self._require_admin(admin)
        fields = self._validated_trade(payload)

        if self.repo.slug_taken(Trade, fields.slug):
            raise DomainError(ErrorCode.CONFLICT, field="slug")

        trade = Trade(
            slug=fields.slug,
            name_ar=fields.name_ar,
            name_fr=fields.name_fr,
            name_en=fields.name_en,
            icon=fields.icon,
            lead_fee_centimes=fields.lead_fee_centimes,
            sort_order=fields.sort_order,
            is_active=True,
        )
        self.db.add(trade)
        self.db.flush()

        self._record(admin, AuditAction.TRADE_CREATED, "trade", trade.id, None,
                     _trade_state(trade), ip)
        self.db.commit()
        return trade

    def update_trade(
        self, admin: User, trade_id: int, payload: dict[str, Any], *, ip: str | None = None
    ) -> Trade:
        """Everything but the slug.

        The slug is in `/services/:slug`, in whatever anybody has bookmarked
        and in every link that has been shared. Editing it turns all of those
        into a 404 silently, so renaming a trade means editing its three names
        — which is what a reader actually sees.
        """
        self._require_admin(admin)
        trade = self.repo.trade(trade_id)
        if trade is None:
            raise DomainError(ErrorCode.NOT_FOUND)

        fields = self._validated_trade({**payload, "slug": trade.slug})
        before = _trade_state(trade)

        trade.name_ar = fields.name_ar
        trade.name_fr = fields.name_fr
        trade.name_en = fields.name_en
        trade.icon = fields.icon
        trade.lead_fee_centimes = fields.lead_fee_centimes
        trade.sort_order = fields.sort_order

        self._record_change(
            admin, AuditAction.TRADE_UPDATED, "trade", trade.id, before,
            _trade_state(trade), ip
        )
        self.db.commit()
        return trade

    def set_trade_active(
        self, admin: User, trade_id: int, *, active: bool, ip: str | None = None
    ) -> Trade:
        self._require_admin(admin)
        trade = self.repo.trade(trade_id)
        if trade is None:
            raise DomainError(ErrorCode.NOT_FOUND)

        before = trade.is_active
        trade.is_active = active
        self._record_change(
            admin, AuditAction.TRADE_UPDATED, "trade", trade.id,
            {"is_active": before}, {"is_active": active}, ip
        )
        self.db.commit()
        return trade

    # -- cities ----------------------------------------------------------

    def create_city(
        self, admin: User, payload: dict[str, Any], *, ip: str | None = None
    ) -> City:
        self._require_admin(admin)
        fields = self._validated_city(payload)

        if self.repo.slug_taken(City, fields.slug):
            raise DomainError(ErrorCode.CONFLICT, field="slug")

        city = City(
            slug=fields.slug,
            name_ar=fields.name_ar,
            name_fr=fields.name_fr,
            name_en=fields.name_en,
            latitude=fields.latitude,
            longitude=fields.longitude,
            is_active=True,
        )
        self.db.add(city)
        self.db.flush()

        self._record(admin, AuditAction.CITY_CREATED, "city", city.id, None,
                     _city_state(city), ip)
        self.db.commit()
        return city

    def update_city(
        self, admin: User, city_id: int, payload: dict[str, Any], *, ip: str | None = None
    ) -> City:
        self._require_admin(admin)
        city = self.repo.city(city_id)
        if city is None:
            raise DomainError(ErrorCode.NOT_FOUND)

        fields = self._validated_city({**payload, "slug": city.slug})
        before = _city_state(city)

        city.name_ar = fields.name_ar
        city.name_fr = fields.name_fr
        city.name_en = fields.name_en
        city.latitude = fields.latitude
        city.longitude = fields.longitude

        self._record_change(
            admin, AuditAction.CITY_UPDATED, "city", city.id, before,
            _city_state(city), ip
        )
        self.db.commit()
        return city

    def set_city_active(
        self, admin: User, city_id: int, *, active: bool, ip: str | None = None
    ) -> City:
        self._require_admin(admin)
        city = self.repo.city(city_id)
        if city is None:
            raise DomainError(ErrorCode.NOT_FOUND)

        before = city.is_active
        city.is_active = active
        self._record_change(
            admin, AuditAction.CITY_UPDATED, "city", city.id,
            {"is_active": before}, {"is_active": active}, ip
        )
        self.db.commit()
        return city

    # -- shared ----------------------------------------------------------

    @staticmethod
    def _require_admin(admin: User) -> None:
        if admin.role is not Role.ADMIN:
            raise DomainError(ErrorCode.FORBIDDEN, role=admin.role.value)

    @staticmethod
    def _validated_trade(payload: dict[str, Any]) -> TradeFields:
        try:
            return validate_trade(
                slug=payload["slug"],
                name_ar=payload["name_ar"],
                name_fr=payload["name_fr"],
                name_en=payload["name_en"],
                icon=payload["icon"],
                lead_fee_centimes=payload.get("lead_fee_centimes"),
                sort_order=payload["sort_order"],
            )
        except ValueError as error:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field=str(error)) from error

    @staticmethod
    def _validated_city(payload: dict[str, Any]) -> CityFields:
        try:
            return validate_city(
                slug=payload["slug"],
                name_ar=payload["name_ar"],
                name_fr=payload["name_fr"],
                name_en=payload["name_en"],
                latitude=payload["latitude"],
                longitude=payload["longitude"],
            )
        except ValueError as error:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field=str(error)) from error

    def _record(
        self,
        admin: User,
        action: str,
        target_type: str,
        target_id: int,
        before: dict[str, Any] | None,
        after: dict[str, Any],
        ip: str | None,
    ) -> None:
        audit.record(
            self.db,
            actor=admin,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before=before,
            after=after,
            ip=ip,
        )

    def _record_change(
        self,
        admin: User,
        action: str,
        target_type: str,
        target_id: int,
        before: dict[str, Any],
        after: dict[str, Any],
        ip: str | None,
    ) -> None:
        """Only what actually moved, and nothing at all when nothing did.

        A6's log is read to answer "when did this trade's fee change" — an
        entry per save, listing eight unchanged fields, is a log that cannot
        answer it.
        """
        moved = {key: value for key, value in after.items() if before.get(key) != value}
        if not moved:
            return

        self._record(
            admin,
            action,
            target_type,
            target_id,
            {key: before.get(key) for key in moved},
            moved,
            ip,
        )


def _trade_state(trade: Trade) -> dict[str, Any]:
    return {
        "slug": trade.slug,
        "name_ar": trade.name_ar,
        "name_fr": trade.name_fr,
        "name_en": trade.name_en,
        "icon": trade.icon,
        "lead_fee_centimes": trade.lead_fee_centimes,
        "sort_order": trade.sort_order,
        "is_active": trade.is_active,
    }


def _city_state(city: City) -> dict[str, Any]:
    return {
        "slug": city.slug,
        "name_ar": city.name_ar,
        "name_fr": city.name_fr,
        "name_en": city.name_en,
        "latitude": city.latitude,
        "longitude": city.longitude,
        "is_active": city.is_active,
    }
