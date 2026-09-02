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
    TransactionType,
)
from app.core.money import dirhams
from app.models.base import utcnow
from app.models.credit import CreditAccount, CreditTransaction
from app.models.dispute import Dispute
from app.models.job import Job
from app.models.offer import Offer
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
