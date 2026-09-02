"""The seed writes demo data, and demo data still has to be true.

Two lies shipped from this file before A1 put the numbers on a screen next to
each other: leads sold with no ledger behind them, and every account stamped
with the hour the seed ran. Both are pinned here.
"""

from __future__ import annotations

import random
from datetime import timedelta

import pytest

from app.core.enums import JobStatus, OfferStatus, Role, TransactionType
from app.core.money import dirhams
from app.demo_seed import backfill_lead_ledger, backfill_signup_dates
from app.models.base import utcnow
from app.models.credit import CreditAccount, CreditTransaction
from app.models.job import Job
from app.models.offer import Offer
from app.models.request import ServiceRequest
from tests.test_auth_api import make_user
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def history(db):
    """A tradesman with a year of finished work and no ledger at all."""
    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")
    provider = make_provider(
        db, phone="+212700000001", city=city, trades=[trade], name="Karim Zeroual"
    )
    client_user = make_user(db, phone="+212611111111", role=Role.CLIENT)
    account = CreditAccount(
        provider_id=provider.id, balance_centimes=dirhams(50), free_leads_left=0
    )
    db.add(account)
    db.flush()

    started = utcnow().replace(tzinfo=None) - timedelta(days=400)

    def job_at(days: int, *, fee: int) -> Job:
        request = ServiceRequest(
            client_id=client_user.id,
            trade_id=trade.id,
            city_id=city.id,
            title="Fuite",
            description="L'eau coule dès que j'ouvre le robinet.",
            address="12 rue Al Massira",
        )
        db.add(request)
        db.flush()
        offer = Offer(
            request_id=request.id,
            provider_id=provider.id,
            price_centimes=dirhams(300),
            message="",
            status=OfferStatus.ACCEPTED,
            lead_fee_centimes=fee,
        )
        db.add(offer)
        db.flush()
        row = Job(
            request_id=request.id,
            offer_id=offer.id,
            client_id=client_user.id,
            provider_id=provider.id,
            agreed_price_centimes=dirhams(300),
            status=JobStatus.CONFIRMED,
        )
        db.add(row)
        db.flush()
        row.created_at = started + timedelta(days=days)
        request.created_at = row.created_at
        offer.created_at = row.created_at
        db.flush()
        return row

    jobs = [job_at(day, fee=dirhams(10)) for day in (0, 40, 120, 300)]
    db.flush()
    return {"account": account, "provider": provider, "jobs": jobs, "client": client_user}


def ledger(db, account: CreditAccount) -> list[CreditTransaction]:
    return list(
        db.query(CreditTransaction)
        .filter(CreditTransaction.account_id == account.id)
        .order_by(CreditTransaction.created_at, CreditTransaction.id)
        .all()
    )


def test_every_lead_the_seed_sold_gets_the_row_that_explains_it(db, history):
    written = backfill_lead_ledger(db)
    assert written > 0

    fees = [
        row for row in ledger(db, history["account"]) if row.type == TransactionType.LEAD_FEE
    ]
    assert len(fees) == len(history["jobs"])
    assert {row.job_id for row in fees} == {job.id for job in history["jobs"]}


def test_the_replay_lands_on_the_balance_the_account_already_has(db, history):
    account = history["account"]
    before = account.balance_centimes

    backfill_lead_ledger(db)

    rows = ledger(db, account)
    assert rows[-1].balance_after_centimes == before
    assert account.balance_centimes == before


def test_the_money_that_paid_for_the_leads_exists_too(db, history):
    """Replaying only the fees would put a year of work hundreds under."""
    backfill_lead_ledger(db)

    rows = ledger(db, history["account"])
    assert sum(row.amount_centimes for row in rows) == history["account"].balance_centimes

    running = 0
    for row in rows:
        running += row.amount_centimes
        assert row.balance_after_centimes == running
        assert running >= 0, "a replayed history never dips below zero"


def test_a_second_run_writes_nothing(db, history):
    first = backfill_lead_ledger(db)
    balance = history["account"].balance_centimes

    assert backfill_lead_ledger(db) == 0
    assert history["account"].balance_centimes == balance
    assert len(ledger(db, history["account"])) == first


def test_a_ledger_somebody_lived_is_never_rewritten(db, history):
    """A top-up approved on A5 is real history. The seed leaves it alone."""
    account = history["account"]
    db.add(
        CreditTransaction(
            account_id=account.id,
            type=TransactionType.TOPUP,
            amount_centimes=dirhams(50),
            balance_after_centimes=account.balance_centimes,
            reason="topup_approved",
        )
    )
    db.flush()

    assert backfill_lead_ledger(db) == 0
    assert len(ledger(db, account)) == 1
    assert account.balance_centimes == dirhams(50)


def test_nobody_signs_up_after_their_own_first_job(db, history):
    """The seed stamps `created_at` with the hour it ran; A1 reads it as growth."""
    rng = random.Random(7)
    backfill_signup_dates(db, rng=rng)

    first = min(job.created_at for job in history["jobs"])
    assert history["client"].created_at <= first
    provider_user = db.get(type(history["client"]), history["provider"].user_id)
    assert provider_user is not None
    assert provider_user.created_at <= first


def test_spreading_the_dates_is_stable(db, history):
    backfill_signup_dates(db, rng=random.Random(7))
    dates = {user.id: user.created_at for user in db.query(type(history["client"])).all()}

    assert backfill_signup_dates(db, rng=random.Random(99)) == 0
    after = {user.id: user.created_at for user in db.query(type(history["client"])).all()}
    assert after == dates
