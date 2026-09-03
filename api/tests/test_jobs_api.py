"""The handshake that makes a job, and the job that comes out of it.

There is no accept button any more. A job is created when the client and the
tradesman have both signed the same terms in the chat (C9 / M12), so `shake`
below is what every test here goes through — the same single transaction,
reached the way the product now reaches it.
"""

from __future__ import annotations

import pytest

from app.core.enums import OfferStatus, ProviderStatus, RequestStatus, Role
from app.core.money import dirhams
from app.models.credit import CreditAccount, CreditTransaction
from app.models.offer import Offer
from app.models.request import ServiceRequest
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    """A client with an open request, and two tradesmen who have answered it."""
    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")
    make_user(db, phone="+212611111111", role=Role.CLIENT)

    winner = make_provider(
        db, phone="+212700000001", city=city, trades=[trade], name="Karim Zeroual"
    )
    loser = make_provider(
        db, phone="+212700000002", city=city, trades=[trade], name="Hamid Bennani"
    )
    for profile in (winner, loser):
        db.add(
            CreditAccount(provider_id=profile.id, balance_centimes=dirhams(50), free_leads_left=0)
        )
    db.commit()

    token = token_for(client, api_prefix, "0611111111")
    request = client.post(
        f"{api_prefix}/client/requests",
        json={
            "trade_id": trade.id,
            "city_id": city.id,
            "title": "Fuite sous l'évier",
            "description": "L'eau coule dès que j'ouvre le robinet, depuis hier soir.",
            "address": "12 rue Al Massira",
            "urgency": "today",
            "photo_paths": [],
        },
        headers=auth(token),
    ).json()

    offers = {}
    for profile, price in ((winner, 300), (loser, 450)):
        offer = Offer(
            request_id=request["id"],
            provider_id=profile.id,
            price_centimes=dirhams(price),
            message="",
            status=OfferStatus.PENDING,
        )
        db.add(offer)
        db.flush()
        offers[profile.id] = offer.id
    db.execute(
        ServiceRequest.__table__.update()
        .where(ServiceRequest.__table__.c.id == request["id"])
        .values(offers_count=2)
    )
    db.commit()

    return {
        "token": token,
        "request_id": request["id"],
        "winner": winner,
        "loser": loser,
        "offers": offers,
        "city": city,
        "trade": trade,
    }


def open_chat(client, api_prefix, stage, *, offer_id=None, token=None):
    offer_id = offer_id or stage["offers"][stage["winner"].id]
    return client.post(
        f"{api_prefix}/offers/{offer_id}/conversation",
        headers=auth(token or stage["token"]),
    )


def accept(client, api_prefix, stage, *, offer_id=None, token=None, profile=None):
    """Open the chat and have both sides sign. Returns the job, or the refusal
    from whichever step refused, so the caller reads one response either way."""
    opened = open_chat(client, api_prefix, stage, offer_id=offer_id, token=token)
    if opened.status_code != 200:
        return opened

    conversation = opened.json()
    version = conversation["version"]
    signed = client.post(
        f"{api_prefix}/conversations/{conversation['id']}/agree",
        json={"version": version},
        headers=auth(token or stage["token"]),
    )
    if signed.status_code != 200:
        return signed

    profile = profile or stage["winner"]
    pro_token = token_for(client, api_prefix, profile.user.phone[4:].rjust(10, "0"))
    sealed = client.post(
        f"{api_prefix}/conversations/{conversation['id']}/agree",
        json={"version": version},
        headers=auth(pro_token),
    )
    if sealed.status_code != 200 or sealed.json().get("job_id") is None:
        return sealed

    return client.get(
        f"{api_prefix}/jobs/{sealed.json()['job_id']}",
        headers=auth(token or stage["token"]),
    )


def test_accepting_settles_the_offer_the_request_and_the_job_at_once(
    client, api_prefix, db, stage
):
    response = accept(client, api_prefix, stage)
    assert response.status_code == 200, response.text

    job = response.json()
    assert job["status"] == "assigned"
    assert job["agreed_price_centimes"] == dirhams(300)
    assert job["provider"]["full_name"] == "Karim Zeroual"

    db.expire_all()
    assert db.get(ServiceRequest, stage["request_id"]).status is RequestStatus.ASSIGNED
    assert db.get(Offer, stage["offers"][stage["winner"].id]).status is OfferStatus.ACCEPTED
    # The one he did not pick is declined by the same action, not left hanging.
    assert db.get(Offer, stage["offers"][stage["loser"].id]).status is OfferStatus.REJECTED


def test_the_client_gets_the_tradesmans_phone_and_the_full_address(
    client, api_prefix, stage
):
    """This is the whole point of C4: two people who have agreed to meet."""
    job = accept(client, api_prefix, stage).json()
    assert job["provider"]["phone"] == "+212700000001"
    assert job["address"] == "12 rue Al Massira"


def test_the_client_is_never_told_what_the_lead_cost(client, api_prefix, stage):
    job = accept(client, api_prefix, stage).json()
    assert job["lead_fee_centimes"] is None


def test_the_fee_is_taken_with_a_ledger_row_behind_it(client, api_prefix, db, stage):
    accept(client, api_prefix, stage)

    account = db.query(CreditAccount).filter_by(provider_id=stage["winner"].id).one()
    assert account.balance_centimes == dirhams(40)  # 50 - the 10 DH default

    row = db.query(CreditTransaction).filter_by(account_id=account.id).one()
    assert row.amount_centimes == -dirhams(10)
    assert row.balance_after_centimes == dirhams(40)
    assert row.reason == "offer_accepted"
    assert row.job_id is not None


def test_a_free_lead_is_spent_before_any_money(client, api_prefix, db, stage):
    account = db.query(CreditAccount).filter_by(provider_id=stage["winner"].id).one()
    account.free_leads_left = 5
    db.commit()

    accept(client, api_prefix, stage)

    db.expire_all()
    account = db.query(CreditAccount).filter_by(provider_id=stage["winner"].id).one()
    assert account.free_leads_left == 4
    assert account.balance_centimes == dirhams(50)  # untouched
    assert db.query(CreditTransaction).filter_by(account_id=account.id).one().reason == "free_lead"


def test_an_empty_balance_does_not_block_the_client(client, api_prefix, db, stage):
    account = db.query(CreditAccount).filter_by(provider_id=stage["winner"].id).one()
    account.balance_centimes = 0
    db.commit()

    assert accept(client, api_prefix, stage).status_code == 200

    db.expire_all()
    account = db.query(CreditAccount).filter_by(provider_id=stage["winner"].id).one()
    assert account.balance_centimes == -dirhams(10)


def test_a_second_acceptance_is_refused(client, api_prefix, stage):
    """The other offer was declined the moment the first deal was sealed, so
    there is nothing left to open a chat on."""
    assert accept(client, api_prefix, stage).status_code == 200

    again = open_chat(
        client, api_prefix, stage, offer_id=stage["offers"][stage["loser"].id]
    )
    assert again.status_code == 409


def test_a_withdrawn_offer_cannot_be_accepted(client, api_prefix, db, stage):
    """He had the page open while the tradesman changed his mind."""
    offer_id = stage["offers"][stage["winner"].id]
    db.get(Offer, offer_id).status = OfferStatus.WITHDRAWN
    db.commit()

    response = open_chat(client, api_prefix, stage, offer_id=offer_id)
    assert response.status_code == 409
    assert response.json()["details"]["reason"] == "offer_not_pending"


def test_a_suspended_tradesman_cannot_be_accepted(client, api_prefix, db, stage):
    stage["winner"].status = ProviderStatus.SUSPENDED
    db.commit()

    response = accept(client, api_prefix, stage)
    assert response.status_code == 409
    assert response.json()["details"]["reason"] == "provider_unavailable"


def test_somebody_else_cannot_open_a_chat_on_your_request(
    client, api_prefix, db, stage
):
    make_user(db, phone="+212611111112", role=Role.CLIENT)
    db.commit()
    other = token_for(client, api_prefix, "0611111112")

    assert open_chat(client, api_prefix, stage, token=other).status_code == 404


# -- the lifecycle ------------------------------------------------------


@pytest.fixture
def assigned(client, api_prefix, stage):
    job = accept(client, api_prefix, stage).json()
    return {**stage, "job_id": job["id"]}


def pro_token(client, api_prefix, phone="0700000001"):
    return token_for(client, api_prefix, phone)


def move(client, api_prefix, job_id, action, token, json=None):
    return client.post(
        f"{api_prefix}/jobs/{job_id}/{action}", json=json or {}, headers=auth(token)
    )


def test_the_job_runs_start_to_confirmed(client, api_prefix, db, assigned):
    pro = pro_token(client, api_prefix)
    job_id = assigned["job_id"]

    assert move(client, api_prefix, job_id, "start", pro).json()["status"] == "in_progress"
    assert move(client, api_prefix, job_id, "finish", pro).json()["status"] == "done"

    confirmed = move(client, api_prefix, job_id, "confirm", assigned["token"]).json()
    assert confirmed["status"] == "confirmed"

    db.expire_all()
    # Confirming is what makes it a finished job on his profile, and what takes
    # the request off the board.
    assert db.get(ServiceRequest, assigned["request_id"]).status is RequestStatus.DONE
    assert assigned["winner"].jobs_done == 1


def test_a_client_cannot_start_or_finish_the_work(client, api_prefix, assigned):
    for action in ("start", "finish"):
        response = move(client, api_prefix, assigned["job_id"], action, assigned["token"])
        assert response.status_code == 403


def test_a_tradesman_cannot_confirm_his_own_work(client, api_prefix, assigned):
    pro = pro_token(client, api_prefix)
    assert move(client, api_prefix, assigned["job_id"], "confirm", pro).status_code == 403


def test_confirming_before_the_work_is_done_is_refused(client, api_prefix, assigned):
    response = move(client, api_prefix, assigned["job_id"], "confirm", assigned["token"])
    assert response.status_code == 409


def test_a_tradesman_must_say_why_he_cancelled(client, api_prefix, db, assigned):
    """His cancellation rate is built from these."""
    pro = pro_token(client, api_prefix)
    blank = move(client, api_prefix, assigned["job_id"], "cancel", pro, {"reason": "  "})
    assert blank.status_code == 422

    ok = move(
        client, api_prefix, assigned["job_id"], "cancel", pro, {"reason": "Panne de voiture"}
    )
    assert ok.json()["status"] == "cancelled"
    assert ok.json()["cancelled_by"] == "provider"

    db.expire_all()
    assert assigned["winner"].jobs_cancelled == 1


def test_the_client_may_cancel_without_a_reason(client, api_prefix, assigned):
    response = move(client, api_prefix, assigned["job_id"], "cancel", assigned["token"])
    assert response.status_code == 200
    assert response.json()["cancelled_by"] == "client"


def test_a_stranger_cannot_read_the_job(client, api_prefix, db, assigned):
    make_user(db, phone="+212611111113", role=Role.CLIENT)
    db.commit()
    other = token_for(client, api_prefix, "0611111113")

    response = client.get(f"{api_prefix}/jobs/{assigned['job_id']}", headers=auth(other))
    assert response.status_code == 404


def test_the_tradesman_sees_what_the_lead_cost_him(client, api_prefix, assigned):
    job = client.get(
        f"{api_prefix}/jobs/{assigned['job_id']}", headers=auth(pro_token(client, api_prefix))
    ).json()
    assert job["lead_fee_centimes"] == dirhams(10)
    assert job["client"]["phone"] == "+212611111111"


# -- C5 -----------------------------------------------------------------


@pytest.fixture
def finished(client, api_prefix, assigned):
    pro = pro_token(client, api_prefix)
    move(client, api_prefix, assigned["job_id"], "start", pro)
    move(client, api_prefix, assigned["job_id"], "finish", pro)
    move(client, api_prefix, assigned["job_id"], "confirm", assigned["token"])
    return assigned


def review(client, api_prefix, job_id, token, **body):
    return client.post(f"{api_prefix}/jobs/{job_id}/review", json=body, headers=auth(token))


def test_rating_a_job_updates_the_profile_it_is_about(client, api_prefix, db, finished):
    response = review(
        client, api_prefix, finished["job_id"], finished["token"], rating=4, comment="Propre."
    )
    assert response.status_code == 201
    assert response.json()["review"]["rating"] == 4

    db.expire_all()
    # The stars on the card are derived from the reviews, never incremented.
    assert finished["winner"].rating_avg == 4.0
    assert finished["winner"].rating_count == 1


def test_a_job_is_rated_once(client, api_prefix, finished):
    review(client, api_prefix, finished["job_id"], finished["token"], rating=5)
    again = review(client, api_prefix, finished["job_id"], finished["token"], rating=1)
    assert again.status_code == 409


def test_unfinished_work_cannot_be_rated(client, api_prefix, assigned):
    response = review(client, api_prefix, assigned["job_id"], assigned["token"], rating=5)
    assert response.status_code == 409


def test_a_rating_outside_one_to_five_is_refused(client, api_prefix, finished):
    for rating in (0, 6):
        response = review(
            client, api_prefix, finished["job_id"], finished["token"], rating=rating
        )
        assert response.status_code == 422


def test_the_tradesman_cannot_rate_himself(client, api_prefix, finished):
    pro = pro_token(client, api_prefix)
    assert review(client, api_prefix, finished["job_id"], pro, rating=5).status_code == 403


def test_the_job_list_answers_from_whichever_side_you_are_on(client, api_prefix, assigned):
    mine = client.get(f"{api_prefix}/jobs", headers=auth(assigned["token"])).json()
    his = client.get(f"{api_prefix}/jobs", headers=auth(pro_token(client, api_prefix))).json()

    assert [job["id"] for job in mine["items"]] == [assigned["job_id"]]
    assert [job["id"] for job in his["items"]] == [assigned["job_id"]]


def test_reading_a_job_needs_an_account(client, api_prefix, assigned):
    assert client.get(f"{api_prefix}/jobs/{assigned['job_id']}").status_code == 401
