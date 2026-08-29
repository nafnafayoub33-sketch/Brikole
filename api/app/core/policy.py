"""The numbers the product runs on.

These are the *defaults*. An admin edits them at A7 and the values land in
`platform_settings`; this module is what the platform falls back to, and what
the seed writes on a fresh install. Keeping them in one framework-free place
means a rule can be unit-tested without a database.
"""

from __future__ import annotations

from app.core.money import dirhams


class SettingKey:
    """Keys in `platform_settings`. Strings, so A7 can edit them generically."""

    DEFAULT_LEAD_FEE = "default_lead_fee_centimes"
    FREE_LEADS_NEW_PROVIDER = "free_leads_new_provider"
    MAX_OPEN_REQUESTS_PER_CLIENT = "max_open_requests_per_client"
    OFFER_EXPIRY_DAYS = "offer_expiry_days"
    REQUEST_EXPIRY_DAYS = "request_expiry_days"
    AUTO_CONFIRM_DAYS = "auto_confirm_days"
    DISPUTE_WINDOW_DAYS = "dispute_window_days"
    DEFAULT_RADIUS_KM = "default_radius_km"
    BANK_TRANSFER = "bank_transfer"
    MAINTENANCE_MODE = "maintenance_mode"


#: Charged to the tradesman when a client accepts his offer, unless the trade
#: overrides it. Not a commission — the platform never sees the job price.
DEFAULT_LEAD_FEE_CENTIMES = dirhams(10)

#: A new tradesman works this many jobs before the fee starts applying.
FREE_LEADS_NEW_PROVIDER = 20

#: Stops one client flooding the feed.
MAX_OPEN_REQUESTS_PER_CLIENT = 3

OFFER_EXPIRY_DAYS = 7
REQUEST_EXPIRY_DAYS = 30

#: A finished job the client never confirms is confirmed for him after this.
AUTO_CONFIRM_DAYS = 7

#: How long after a job is done either side may still open a dispute.
DISPUTE_WINDOW_DAYS = 7

DEFAULT_RADIUS_KM = 10
MAX_RADIUS_KM = 100

MAX_REQUEST_PHOTOS = 6
MAX_PORTFOLIO_PHOTOS = 10

MIN_RATING = 1
MAX_RATING = 5

DEFAULTS: dict[str, object] = {
    SettingKey.DEFAULT_LEAD_FEE: DEFAULT_LEAD_FEE_CENTIMES,
    SettingKey.FREE_LEADS_NEW_PROVIDER: FREE_LEADS_NEW_PROVIDER,
    SettingKey.MAX_OPEN_REQUESTS_PER_CLIENT: MAX_OPEN_REQUESTS_PER_CLIENT,
    SettingKey.OFFER_EXPIRY_DAYS: OFFER_EXPIRY_DAYS,
    SettingKey.REQUEST_EXPIRY_DAYS: REQUEST_EXPIRY_DAYS,
    SettingKey.AUTO_CONFIRM_DAYS: AUTO_CONFIRM_DAYS,
    SettingKey.DISPUTE_WINDOW_DAYS: DISPUTE_WINDOW_DAYS,
    SettingKey.DEFAULT_RADIUS_KM: DEFAULT_RADIUS_KM,
    SettingKey.MAINTENANCE_MODE: False,
    SettingKey.BANK_TRANSFER: {
        "bank_name": "",
        "account_holder": "",
        "rib": "",
        "instructions": "",
    },
}


def lead_fee_for(trade_fee_centimes: int | None, default_centimes: int) -> int:
    """A trade's own fee when it has one, the platform default otherwise."""
    return trade_fee_centimes if trade_fee_centimes is not None else default_centimes
