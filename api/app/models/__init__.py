"""Every model, imported once so Alembic's autogenerate sees the whole schema."""

from app.models.base import Base, PkMixin, TimestampMixin, utcnow
from app.models.catalog import City, Trade
from app.models.credit import CreditAccount, CreditTransaction, TopupRequest
from app.models.dispute import Dispute, DisputeMessage, Report
from app.models.job import Job, Review
from app.models.offer import Offer
from app.models.provider import ProviderPhoto, ProviderProfile, provider_trades
from app.models.request import RequestPhoto, ServiceRequest
from app.models.system import AuditLog, Notification, PlatformSetting
from app.models.user import User

__all__ = [
    "AuditLog",
    "Base",
    "City",
    "CreditAccount",
    "CreditTransaction",
    "Dispute",
    "DisputeMessage",
    "Job",
    "Notification",
    "Offer",
    "PkMixin",
    "PlatformSetting",
    "ProviderPhoto",
    "ProviderProfile",
    "Report",
    "RequestPhoto",
    "Review",
    "ServiceRequest",
    "TimestampMixin",
    "TopupRequest",
    "Trade",
    "User",
    "provider_trades",
    "utcnow",
]
