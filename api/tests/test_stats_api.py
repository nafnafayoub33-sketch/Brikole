"""A1 — the numbers the admin dashboard leads with."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.enums import (
    DisputeStatus,
    JobStatus,
    OfferStatus,
    ProviderStatus,
    RequestStatus,
    Role,
    TopupStatus,
    TransactionType,
)
from app.core.money import dirhams
from app.models.base import utcnow
from app.models.credit import CreditAccount, CreditTransaction, TopupRequest
from app.models.dispute import Dispute
from app.models.job import Job
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    """One of everything the dashboard counts."""
    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")

    approved = make_provider(
        db, phone="+212700000001", city=city, trades=[trade], name="Karim Zeroual"
    )
    make_provider(
        db,
        phone="+212700000002",
        city=city,
        trades=[trade],
        name="En attente",
        status=ProviderStatus.PENDING,
    )
    account = CreditAccount(
        provider_id=approved.id, balance_centimes=dirhams(40), free_leads_left=0
    )
    db.add(account)

    author = make_user(db, phone="+212611111111", role=Role.CLIENT)
    make_user(db, phone="+212600000001", role=Role.ADMIN)
    db.flush()

    def request_row(status):
        row = ServiceRequest(
            client_id=author.id,
            trade_id=trade.id,
            city_id=city.id,
            title="Fuite",
            description="L'eau coule dès que j'ouvre le robinet.",
            address="12 rue Al Massira",
            status=status,
        )
        db.add(row)
        db.flush()
        return row

    open_request = request_row(RequestStatus.OPEN)
    done_request = request_row(RequestStatus.DONE)

    offer = Offer(
        request_id=done_request.id,
        provider_id=approved.id,
        price_centimes=dirhams(300),
        message="",
        status=OfferStatus.ACCEPTED,
        lead_fee_centimes=dirhams(10),
    )
    db.add(offer)
    db.flush()

    job = Job(
        request_id=done_request.id,
        offer_id=offer.id,
        client_id=author.id,
        provider_id=approved.id,
        agreed_price_centimes=dirhams(300),
        status=JobStatus.CONFIRMED,
    )
    db.add(job)
    db.flush()

    # One paid lead and one free one: a free lead is a lead sold at zero.
    db.add(
        CreditTransaction(
            account_id=account.id,
            type=TransactionType.LEAD_FEE,
            amount_centimes=-dirhams(10),
            balance_after_centimes=dirhams(40),
            reason="offer_accepted",
            job_id=job.id,
        )
    )
    db.add(
        CreditTransaction(
            account_id=account.id,
            type=TransactionType.FREE_LEAD,
            amount_centimes=0,
            balance_after_centimes=dirhams(40),
            reason="free_lead",
        )
    )

    db.add(
        Dispute(
            job_id=job.id,
            opened_by_id=author.id,
            against_id=approved.user_id,
            reason="work_not_done",
            description="Il est parti sans finir.",
            status=DisputeStatus.OPEN,
        )
    )
    db.commit()

    return {
        "admin": token_for(client, api_prefix, "0600000001"),
        "client": token_for(client, api_prefix, "0611111111"),
        "open_request": open_request,
        "author": author,
    }


def stats(client, api_prefix, stage, token=None):
    return client.get(f"{api_prefix}/admin/stats", headers=auth(token or stage["admin"]))


def test_the_dashboard_counts_what_is_actually_there(client, api_prefix, stage):
    body = stats(client, api_prefix, stage).json()

    assert body["providers_awaiting_approval"] == 1
    assert body["open_requests"] == 1
    assert body["jobs_done"] == 1
    assert body["disputes_open"] == 1


def test_a_free_lead_is_a_lead_sold_at_zero(client, api_prefix, stage):
    """It counts as a lead delivered and adds nothing to the money."""
    body = stats(client, api_prefix, stage).json()
    assert body["leads_sold"] == 2
    assert body["leads_value_centimes"] == dirhams(10)


def test_the_value_is_shown_as_what_the_platform_took(client, api_prefix, stage):
    """Stored negative — it left the tradesman's balance — and read positive."""
    assert stats(client, api_prefix, stage).json()["leads_value_centimes"] > 0


def test_new_users_this_week_excludes_older_accounts(client, api_prefix, db, stage):
    stage["author"].created_at = utcnow() - timedelta(days=30)
    db.commit()

    body = stats(client, api_prefix, stage).json()
    # The admin and the two tradesmen's users remain inside the window.
    assert body["new_users_this_week"] == 3
    assert body["new_users_last_week"] == 0


def test_last_week_is_the_week_before_not_everything_older(client, api_prefix, db, stage):
    """Otherwise the comparison grows forever and always looks like a collapse."""
    stage["author"].created_at = utcnow() - timedelta(days=10)
    db.commit()

    body = stats(client, api_prefix, stage).json()
    assert body["new_users_last_week"] == 1

    stage["author"].created_at = utcnow() - timedelta(days=20)
    db.commit()
    assert stats(client, api_prefix, stage).json()["new_users_last_week"] == 0


def test_a_cancelled_request_is_not_an_open_one(client, api_prefix, db, stage):
    stage["open_request"].status = RequestStatus.CANCELLED
    db.commit()
    assert stats(client, api_prefix, stage).json()["open_requests"] == 0


def test_a_resolved_dispute_leaves_the_count(client, api_prefix, db, stage):
    db.query(Dispute).one().status = DisputeStatus.RESOLVED
    db.commit()
    assert stats(client, api_prefix, stage).json()["disputes_open"] == 0


def test_a_claimed_dispute_is_still_open_work(client, api_prefix, db, stage):
    """Somebody picked it up; nobody has decided it."""
    db.query(Dispute).one().status = DisputeStatus.CLAIMED
    db.commit()
    assert stats(client, api_prefix, stage).json()["disputes_open"] == 1


def test_only_an_admin_sees_the_dashboard(client, api_prefix, db, stage):
    make_user(db, phone="+212655000001", role=Role.MODERATOR)
    db.commit()

    for phone in ("0611111111", "0655000001"):
        response = stats(
            client, api_prefix, stage, token_for(client, api_prefix, phone)
        )
        assert response.status_code == 403

    assert client.get(f"{api_prefix}/admin/stats").status_code == 401


# -- money ------------------------------------------------------------------


def test_the_job_price_in_dispute_is_not_the_platforms_money(client, api_prefix, stage):
    """No escrow before phase 3: the price is argued over between two people.

    What the platform itself has at stake on that job is the lead fee it
    charged, and the two are reported apart so nobody reads the wrong one as
    revenue at risk.
    """
    money = stats(client, api_prefix, stage).json()["money"]

    assert money["in_dispute_centimes"] == dirhams(300)
    assert money["disputed_lead_fees_centimes"] == dirhams(10)
    assert money["taken_centimes"] == dirhams(10)


def test_a_job_with_two_disputes_counts_its_price_once(client, api_prefix, db, stage):
    """Summing over disputes instead of jobs would double it."""
    first = db.query(Dispute).one()
    db.add(
        Dispute(
            job_id=first.job_id,
            opened_by_id=first.against_id,
            against_id=first.opened_by_id,
            reason="no_show",
            description="Il n'a jamais ouvert la porte.",
            status=DisputeStatus.OPEN,
        )
    )
    db.commit()

    body = stats(client, api_prefix, stage).json()
    assert body["disputes_open"] == 2
    assert body["money"]["in_dispute_centimes"] == dirhams(300)


def test_a_resolved_dispute_releases_the_money(client, api_prefix, db, stage):
    db.query(Dispute).one().status = DisputeStatus.RESOLVED
    db.commit()

    money = stats(client, api_prefix, stage).json()["money"]
    assert money["in_dispute_centimes"] == 0
    assert money["disputed_lead_fees_centimes"] == 0


def test_credit_held_and_credit_owed_are_two_different_facts(client, api_prefix, db, stage):
    """One is the platform's float; the other is a debt it is carrying."""
    account = db.query(CreditAccount).one()
    body = stats(client, api_prefix, stage).json()
    assert body["money"]["credit_held_centimes"] == dirhams(40)
    assert body["money"]["credit_owed_centimes"] == 0

    account.balance_centimes = -dirhams(15)
    db.commit()

    money = stats(client, api_prefix, stage).json()["money"]
    assert money["credit_held_centimes"] == 0
    assert money["credit_owed_centimes"] == dirhams(15)


def test_a_topup_nobody_approved_is_not_money_yet(client, api_prefix, db, stage):
    """It is a bank transfer somebody claims to have made. A5 decides."""
    provider = db.query(ProviderProfile).order_by(ProviderProfile.id).first()
    assert provider is not None
    db.add(
        TopupRequest(
            provider_id=provider.id,
            amount_centimes=dirhams(200),
            reference="VIR-2026-08-31",
            status=TopupStatus.PENDING,
        )
    )
    db.commit()

    money = stats(client, api_prefix, stage).json()["money"]
    assert money["topups_waiting"] == 1
    assert money["topups_waiting_centimes"] == dirhams(200)
    assert money["credit_held_centimes"] == dirhams(40), "not on any balance yet"


# -- the trend --------------------------------------------------------------


def test_the_trend_carries_every_month_including_the_quiet_ones(client, api_prefix, stage):
    """A month with no work is a fact. Dropping the row closes the gap and
    draws a line that never happened."""
    months = stats(client, api_prefix, stage).json()["months"]

    assert len(months) == 13
    assert months == sorted(months, key=lambda point: point["month"])
    assert all(len(point["month"]) == 7 for point in months)
    assert sum(point["leads"] for point in months) == 2


# -- where the work is ------------------------------------------------------


def test_cities_carry_their_own_three_names(client, api_prefix, stage):
    """An admin adds a city at runtime, so its name is data, not a key."""
    city = stats(client, api_prefix, stage).json()["cities"][0]
    assert city["slug"] == "casablanca"
    assert city["name_ar"] and city["name_fr"] and city["name_en"]


def test_a_city_reports_work_money_and_who_is_there(client, api_prefix, stage):
    city = stats(client, api_prefix, stage).json()["cities"][0]

    assert city["jobs"] == 1
    assert city["value_centimes"] == dirhams(10)
    assert city["open_requests"] == 1
    assert city["providers"] == 1, "the pending application is not a tradesman yet"


def test_the_busiest_place_comes_first(client, api_prefix, db, stage):
    quiet = make_city(db, "agadir")
    db.commit()

    cities = stats(client, api_prefix, stage).json()["cities"]
    assert [row["slug"] for row in cities] == ["casablanca", quiet.slug]


def test_a_trade_counts_the_same_way_a_city_does(client, api_prefix, stage):
    trade = stats(client, api_prefix, stage).json()["trades"][0]
    assert trade["slug"] == "plombier"
    assert trade["jobs"] == 1
    assert trade["value_centimes"] == dirhams(10)


# -- does the marketplace work ----------------------------------------------


def test_the_funnel_narrows_at_every_step(client, api_prefix, stage):
    funnel = stats(client, api_prefix, stage).json()["funnel"]

    assert funnel["requests"] == 2
    assert funnel["with_offer"] == 1
    assert funnel["hired"] == 1
    assert funnel["confirmed"] == 1
    assert (
        funnel["requests"] >= funnel["with_offer"] >= funnel["hired"] >= funnel["confirmed"]
    )


def test_a_withdrawn_offer_never_answered_the_request(client, api_prefix, db, stage):
    """The tradesman took it back, so nobody replied. That is the failure the
    platform exists to prevent, and it has to show as one."""
    db.query(Offer).one().status = OfferStatus.WITHDRAWN
    db.commit()

    assert stats(client, api_prefix, stage).json()["funnel"]["with_offer"] == 0
