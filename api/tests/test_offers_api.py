"""M4, M5 and M6 — the feed, sending an offer, and the credit that gates both."""

from __future__ import annotations

import pytest

from app.core.enums import OfferStatus, ProviderStatus, RequestStatus, Role
from app.core.money import dirhams
from app.models.credit import CreditAccount
from app.models.offer import Offer
from app.models.request import ServiceRequest
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    """A plumber in Casablanca, and three open requests around him."""
    casa = make_city(db, "casablanca")
    rabat = make_city(db, "rabat")
    plombier = make_trade(db, "plombier")
    peintre = make_trade(db, "peintre")

    provider = make_provider(
        db, phone="+212700000001", city=casa, trades=[plombier], name="Karim Zeroual"
    )
    db.add(CreditAccount(provider_id=provider.id, balance_centimes=dirhams(50), free_leads_left=0))

    make_user(db, phone="+212611111111", role=Role.CLIENT)
    db.commit()

    client_token = token_for(client, api_prefix, "0611111111")

    def post_request(city, trade, title, **extra):
        body = {
            "trade_id": trade.id,
            "city_id": city.id,
            "title": title,
            "description": "L'eau coule dès que j'ouvre le robinet, depuis hier soir.",
            "address": "12 rue Al Massira",
            "urgency": "today",
            "photo_paths": [],
        }
        body.update(extra)
        return client.post(
            f"{api_prefix}/client/requests", json=body, headers=auth(client_token)
        ).json()

    mine = post_request(casa, plombier, "Fuite sous l'évier")
    other_trade = post_request(casa, peintre, "Repeindre le salon", urgency="flexible")
    other_city = post_request(rabat, plombier, "Chauffe-eau en panne")

    return {
        "provider": provider,
        "token": token_for(client, api_prefix, "0700000001"),
        "client_token": client_token,
        "mine": mine,
        "other_trade": other_trade,
        "other_city": other_city,
        "casa": casa,
        "plombier": plombier,
    }


def feed(client, api_prefix, stage, **params):
    return client.get(
        f"{api_prefix}/pro/requests", params=params, headers=auth(stage["token"])
    )


# -- M4 ------------------------------------------------------------------


def test_the_feed_is_his_trades_in_his_city_and_nothing_else(client, api_prefix, stage):
    """A plumber in Meknès is no use to a homeowner in Rabat, and the reverse."""
    body = feed(client, api_prefix, stage).json()
    assert [row["id"] for row in body["items"]] == [stage["mine"]["id"]]


def test_the_feed_shows_what_he_decides_from(client, api_prefix, stage):
    row = feed(client, api_prefix, stage).json()["items"][0]
    assert row["title"] == "Fuite sous l'évier"
    assert row["trade"]["slug"] == "plombier"
    assert row["city"]["slug"] == "casablanca"
    assert row["urgency"] == "today"
    assert row["offers_count"] == 0
    assert row["excerpt"].startswith("L'eau coule")


def test_the_feed_never_carries_the_address(client, api_prefix, stage):
    """It is not his until his offer is accepted."""
    row = feed(client, api_prefix, stage).json()["items"][0]
    assert "address" not in row


def test_the_feed_can_be_filtered_by_trade_and_urgency(client, api_prefix, stage):
    assert feed(client, api_prefix, stage, trade_id=stage["plombier"].id).json()["total"] == 1
    assert feed(client, api_prefix, stage, urgency="flexible").json()["total"] == 0


def test_an_empty_balance_closes_the_feed(client, api_prefix, db, stage):
    """He is not shown work he cannot take — reading it, picking one and being
    refused at the end is the cruellest version of this screen."""
    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    account.balance_centimes = dirhams(9)
    db.commit()

    response = feed(client, api_prefix, stage)
    assert response.status_code == 402
    assert response.json()["code"] == "insufficient_credit"


def test_a_free_lead_keeps_the_feed_open_with_no_money(client, api_prefix, db, stage):
    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    account.balance_centimes = 0
    account.free_leads_left = 3
    db.commit()

    assert feed(client, api_prefix, stage).status_code == 200


def test_a_tradesman_awaiting_approval_has_no_feed(client, api_prefix, db, stage):
    stage["provider"].status = ProviderStatus.PENDING
    db.commit()

    response = feed(client, api_prefix, stage)
    assert response.status_code == 403
    assert response.json()["details"]["reason"] == "not_approved"


def test_a_client_has_no_feed(client, api_prefix, stage):
    response = client.get(
        f"{api_prefix}/pro/requests", headers=auth(stage["client_token"])
    )
    assert response.status_code == 403


# -- M5 ------------------------------------------------------------------


def detail(client, api_prefix, stage, request_id=None):
    return client.get(
        f"{api_prefix}/pro/requests/{request_id or stage['mine']['id']}",
        headers=auth(stage["token"]),
    )


def test_the_detail_states_the_fee_before_he_writes_a_price(client, api_prefix, stage):
    body = detail(client, api_prefix, stage).json()
    assert body["lead_fee_centimes"] == dirhams(10)
    assert body["my_offer"] is None
    assert body["description"].startswith("L'eau coule")


def test_the_detail_never_carries_the_address_either(client, api_prefix, stage):
    assert "address" not in detail(client, api_prefix, stage).json()


def test_a_request_outside_his_trades_is_not_found(client, api_prefix, stage):
    """Not 403 — it was never his to see, and 403 would confirm it exists."""
    assert detail(client, api_prefix, stage, stage["other_trade"]["id"]).status_code == 404
    assert detail(client, api_prefix, stage, stage["other_city"]["id"]).status_code == 404


def send(client, api_prefix, stage, **body):
    payload = {"price_centimes": dirhams(300), "message": "Je passe demain matin."}
    payload.update(body)
    return client.post(
        f"{api_prefix}/pro/requests/{stage['mine']['id']}/offer",
        json=payload,
        headers=auth(stage["token"]),
    )


def test_sending_an_offer_takes_no_money_yet(client, api_prefix, db, stage):
    """The fee is charged when a client accepts, never at this moment."""
    response = send(client, api_prefix, stage)
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"

    db.expire_all()
    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    assert account.balance_centimes == dirhams(50)
    offer = db.query(Offer).filter_by(provider_id=stage["provider"].id).one()
    assert offer.lead_fee_centimes is None


def test_sending_an_offer_counts_it_on_the_request(client, api_prefix, db, stage):
    send(client, api_prefix, stage)
    db.expire_all()
    assert db.get(ServiceRequest, stage["mine"]["id"]).offers_count == 1


def test_a_second_send_edits_the_first_rather_than_stacking(client, api_prefix, db, stage):
    send(client, api_prefix, stage)
    again = send(client, api_prefix, stage, price_centimes=dirhams(280))
    assert again.status_code == 201
    assert again.json()["price_centimes"] == dirhams(280)

    db.expire_all()
    assert db.query(Offer).filter_by(provider_id=stage["provider"].id).count() == 1
    assert db.get(ServiceRequest, stage["mine"]["id"]).offers_count == 1


def test_an_empty_balance_blocks_the_offer_too(client, api_prefix, db, stage):
    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    account.balance_centimes = 0
    db.commit()

    response = send(client, api_prefix, stage)
    assert response.status_code == 402
    assert response.json()["details"]["fee_centimes"] == dirhams(10)


def test_a_price_below_the_floor_is_refused(client, api_prefix, stage):
    response = send(client, api_prefix, stage, price_centimes=dirhams(1))
    assert response.status_code == 422
    assert response.json()["details"]["field"] == "price_centimes"


def test_an_offer_on_a_cancelled_request_is_refused(client, api_prefix, db, stage):
    db.get(ServiceRequest, stage["mine"]["id"]).status = RequestStatus.CANCELLED
    db.commit()
    assert send(client, api_prefix, stage).status_code == 409


def test_withdrawing_takes_it_off_the_clients_page(client, api_prefix, db, stage):
    offer_id = send(client, api_prefix, stage).json()["id"]
    response = client.post(
        f"{api_prefix}/pro/offers/{offer_id}/withdraw", headers=auth(stage["token"])
    )
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"

    db.expire_all()
    assert db.get(Offer, offer_id).responded_at is not None


def test_re_sending_after_a_withdrawal_puts_it_back(client, api_prefix, stage):
    offer_id = send(client, api_prefix, stage).json()["id"]
    client.post(f"{api_prefix}/pro/offers/{offer_id}/withdraw", headers=auth(stage["token"]))

    again = send(client, api_prefix, stage, price_centimes=dirhams(260))
    assert again.json()["status"] == "pending"
    assert again.json()["id"] == offer_id


def test_an_accepted_offer_cannot_be_withdrawn(client, api_prefix, db, stage):
    """It is a job now, and a job is cancelled at M7 — where the client finds out."""
    offer_id = send(client, api_prefix, stage).json()["id"]
    db.get(Offer, offer_id).status = OfferStatus.ACCEPTED
    db.commit()

    response = client.post(
        f"{api_prefix}/pro/offers/{offer_id}/withdraw", headers=auth(stage["token"])
    )
    assert response.status_code == 409


def test_somebody_elses_offer_cannot_be_withdrawn(client, api_prefix, db, stage):
    offer_id = send(client, api_prefix, stage).json()["id"]

    other = make_provider(
        db, phone="+212700000002", city=stage["casa"], trades=[stage["plombier"]], name="Autre"
    )
    db.add(CreditAccount(provider_id=other.id, balance_centimes=dirhams(50), free_leads_left=0))
    db.commit()

    response = client.post(
        f"{api_prefix}/pro/offers/{offer_id}/withdraw",
        headers=auth(token_for(client, api_prefix, "0700000002")),
    )
    assert response.status_code == 404


def test_an_empty_balance_closes_the_request_page_too(client, api_prefix, db, stage):
    """Reachable by URL or a stale link. Without this he reads it, writes a
    price, and is refused only on send — the exact thing closing the feed was
    meant to prevent."""
    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    account.balance_centimes = 0
    db.commit()

    response = detail(client, api_prefix, stage)
    assert response.status_code == 402
    assert response.json()["code"] == "insufficient_credit"


def test_he_can_still_withdraw_once_his_balance_runs_out(client, api_prefix, db, stage):
    """His offer outlives his credit, and an offer he can no longer edit is one
    he must still be able to take back."""
    offer_id = send(client, api_prefix, stage).json()["id"]

    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    account.balance_centimes = 0
    db.commit()

    response = client.post(
        f"{api_prefix}/pro/offers/{offer_id}/withdraw", headers=auth(stage["token"])
    )
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"


# -- M6 ------------------------------------------------------------------


def test_his_offers_come_back_with_the_request_behind_each(client, api_prefix, stage):
    send(client, api_prefix, stage)
    body = client.get(f"{api_prefix}/pro/offers", headers=auth(stage["token"])).json()

    assert body["total"] == 1
    offer = body["items"][0]
    assert offer["request_title"] == "Fuite sous l'évier"
    assert offer["trade"]["slug"] == "plombier"
    assert offer["price_centimes"] == dirhams(300)
    assert offer["job_id"] is None


def test_the_feed_marks_the_ones_he_has_already_answered(client, api_prefix, stage):
    """Otherwise M4 sends him to a form that turns out to be an edit."""
    offer_id = send(client, api_prefix, stage).json()["id"]
    row = feed(client, api_prefix, stage).json()["items"][0]
    assert row["my_offer_id"] == offer_id
    assert row["my_offer_price_centimes"] == dirhams(300)


# -- M3 ------------------------------------------------------------------


def test_the_credit_summary_says_whether_he_can_work(client, api_prefix, db, stage):
    body = client.get(f"{api_prefix}/pro/credit", headers=auth(stage["token"])).json()
    assert body["balance_centimes"] == dirhams(50)
    assert body["default_lead_fee_centimes"] == dirhams(10)
    assert body["can_take_work"] is True

    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    account.balance_centimes = 0
    db.commit()

    body = client.get(f"{api_prefix}/pro/credit", headers=auth(stage["token"])).json()
    assert body["can_take_work"] is False


def test_the_feed_needs_an_account(client, api_prefix):
    assert client.get(f"{api_prefix}/pro/requests").status_code == 401
