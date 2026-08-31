"""A7 — changing how the platform behaves, on the record.

Every write here is audited with the value before and the value after. A
setting changed without that row is a number nobody can explain in three
months, and these are the numbers the business runs on.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode
from app.core.policy import DEFAULTS
from app.core.settings_rules import EDITABLE, validate_setting
from app.models.system import PlatformSetting
from app.models.user import User
from app.repositories.catalog import SettingsRepository
from app.services import audit
from app.services.audit import AuditAction


class PlatformSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = SettingsRepository(db)

    def list_all(self) -> list[tuple[str, Any, PlatformSetting | None]]:
        """Every editable key, with the stored row when one exists.

        Keys nobody has touched come back on their shipped default with no row
        behind them, so A7 can say "this is the default" rather than implying
        somebody chose it.
        """
        return [
            (key, self.settings.get(key), self.db.get(PlatformSetting, key))
            for key in sorted(EDITABLE)
        ]

    def update(
        self, admin: User, values: dict[str, Any], *, ip: str | None = None
    ) -> list[tuple[str, Any, PlatformSetting | None]]:
        if admin.role is not Role.ADMIN:
            raise DomainError(ErrorCode.FORBIDDEN, role=admin.role.value)

        # Validate the whole batch before writing any of it: a form that saves
        # three fields and rejects the fourth leaves the admin guessing which
        # of them landed.
        cleaned: dict[str, Any] = {}
        for key, value in values.items():
            try:
                cleaned[key] = validate_setting(key, value)
            except ValueError as error:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field=key) from error

        for key, value in cleaned.items():
            row = self.db.get(PlatformSetting, key)
            before = row.value if row is not None else DEFAULTS.get(key)
            if before == value:
                # Not a change, so not a line in the log. An audit trail padded
                # with no-ops is one nobody reads.
                continue

            self.settings.set(key, value, actor_id=admin.id)
            audit.record(
                self.db,
                actor=admin,
                action=AuditAction.SETTING_CHANGED,
                target_type="platform_setting",
                target_id=None,
                before={key: before},
                after={key: value},
                note=key,
                ip=ip,
            )

        self.db.commit()
        return self.list_all()
