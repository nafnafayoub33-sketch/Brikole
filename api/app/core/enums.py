"""Domain enumerations.

These are the vocabulary of the product. Models, schemas and rules all import
them from here so a status string is never spelled twice.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    CLIENT = "client"
    PROVIDER = "provider"
    MODERATOR = "moderator"
    ADMIN = "admin"


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class ProviderStatus(StrEnum):
    """A tradesman's approval state. Only APPROVED is visible to clients."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class Urgency(StrEnum):
    TODAY = "today"
    THIS_WEEK = "this_week"
    FLEXIBLE = "flexible"


class RequestStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    DONE = "done"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OfferStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class JobStatus(StrEnum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class CancelledBy(StrEnum):
    CLIENT = "client"
    PROVIDER = "provider"
    ADMIN = "admin"


class TransactionType(StrEnum):
    """Every row in the credit ledger is one of these."""

    LEAD_FEE = "lead_fee"
    TOPUP = "topup"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    FREE_LEAD = "free_lead"


class MessageKind(StrEnum):
    """A line in a conversation.

    `SYSTEM` is the platform narrating what happened — a new price, a
    signature, the job being created — so the history reads as one thread
    rather than as chat with the important parts kept somewhere else.
    """

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


class TopupStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DisputeStatus(StrEnum):
    OPEN = "open"
    CLAIMED = "claimed"
    RESOLVED = "resolved"


class DisputeReason(StrEnum):
    NO_SHOW = "no_show"
    WORK_NOT_DONE = "work_not_done"
    DAMAGE = "damage"
    PRICE_DISAGREEMENT = "price_disagreement"
    BEHAVIOUR = "behaviour"
    OTHER = "other"


class DisputeVerdict(StrEnum):
    CLIENT_AT_FAULT = "client_at_fault"
    PROVIDER_AT_FAULT = "provider_at_fault"
    NO_FAULT = "no_fault"


class NotificationKind(StrEnum):
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    JOB_STARTED = "job_started"
    JOB_DONE = "job_done"
    REVIEW_RECEIVED = "review_received"
    PROVIDER_APPROVED = "provider_approved"
    PROVIDER_REJECTED = "provider_rejected"
    TOPUP_APPROVED = "topup_approved"
    TOPUP_REJECTED = "topup_rejected"
    DISPUTE_UPDATE = "dispute_update"
    CREDIT_LOW = "credit_low"
