"""Every staff action the audit log can carry.

A vocabulary rather than a service's detail: `core/staff_work.py` groups these
into kinds of work, and a rule in `core` reaching into a service for the names
would have the layering backwards. `services/audit.py` re-exports it, so every
call site reads the same as it always did.
"""

from __future__ import annotations


class AuditAction:
    PROVIDER_APPROVED = "provider.approved"
    PROVIDER_REJECTED = "provider.rejected"
    TOPUP_APPROVED = "topup.approved"
    TOPUP_REJECTED = "topup.rejected"
    DISPUTE_RESOLVED = "dispute.resolved"
    SETTING_CHANGED = "setting.changed"
    REPORT_HANDLED = "report.handled"
    USER_SUSPENDED = "user.suspended"
    USER_REACTIVATED = "user.reactivated"
    USER_ROLE_CHANGED = "user.role_changed"
    STAFF_CREATED = "staff.created"
    REQUEST_CANCELLED = "request.cancelled"
    TRADE_CREATED = "trade.created"
    TRADE_UPDATED = "trade.updated"
    CITY_CREATED = "city.created"
    CITY_UPDATED = "city.updated"
