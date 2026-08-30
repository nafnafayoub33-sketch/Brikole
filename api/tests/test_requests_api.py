"""C1, C2, C3 — posting a request, and who can see it."""

from __future__ import annotations

import pytest

from app.core.enums import OfferStatus, RequestStatus, Role
from app.core.money import dirhams
from app.core.policy import MAX_OPEN_REQUESTS_PER_CLIENT
from app.models.offer import Offer
from app.models.request import ServiceRequest
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def setup(client, api_prefix, db):
    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")
    make_user(db, phone="+212611111111", role=Role.CLIENT)
    db.commit()
    return {
        "city": city,
        "trade": trade,
        "token": token_for(client, api_prefix, "0611111111"),
    }


def body(setup, **overrides):
    payload = {
        "trade_id": setup["trade"].id,
        "city_id": setup["city"].id,
        "title": "Fuite sous l'évier",
        "description": "L'eau coule dès que j'ouvre le robinet, depuis hier soir.",
        "address": "12 rue Al Massira, Maârif",
        "urgency": "today",
        "budget_min_centimes": dirhams(100),
        "budget_max_centimes": dirhams(400),
        "photo_paths": ["public/requests/1/a.jpg"],
    }
    payload.update(overrides)
    return payload


def post(client, api_prefix, setup, **overrides):
    return client.post(
        f"{api_prefix}/client/requests", json=body(setup, **overrides), headers=auth(setup["token"])
    )


def test_posting_a_request_opens_it(client, api_prefix, setup):
    response = post(client, api_prefix, setup)
    assert response.status_code == 201, response.text

    request = response.json()
    assert request["status"] == "open"
    assert request["title"] == "Fuite sous l'évier"
    assert request["trade"]["slug"] == "plombier"
    assert request["city"]["slug"] == "casablanca"
    assert request["offers_count"] == 0
    assert len(request["photos"]) == 1
    # It stops being answerable at some point rather than sitting there forever.
    assert request["expires_at"]


def test_he_sees_his_own_requests_newest_first(client, api_prefix, setup):
    post(client, api_prefix, setup, title="La première")
    post(client, api_prefix, setup, title="La deuxième")

    payload = client.get(f"{api_prefix}/client/requests", headers=auth(setup["token"])).json()
    assert payload["total"] == 2
    assert [item["title"] for item in payload["items"]] == ["La deuxième", "La première"]


def test_somebody_elses_request_is_not_found_rather_than_forbidden(client, api_prefix, db, setup):
    """The id space is guessable, and a 403 confirms one exists."""
    mine = post(client, api_prefix, setup).json()

    make_user(db, phone="+212622222222", role=Role.CLIENT)
    db.commit()
    other = token_for(client, api_prefix, "0622222222")

    response = client.get(f"{api_prefix}/client/requests/{mine['id']}", headers=auth(other))
    assert response.status_code == 404


def test_the_cap_is_a_conflict_not_a_field_error(client, api_prefix, setup):
    """The request is fine. There are simply too many of them already."""
    for index in range(MAX_OPEN_REQUESTS_PER_CLIENT):
        assert post(client, api_prefix, setup, title=f"Demande {index}").status_code == 201

    refused = post(client, api_prefix, setup, title="Une de trop")
    assert refused.status_code == 409
    assert refused.json()["details"]["reason"] == "too_many_open_requests"
    assert refused.json()["details"]["max"] == MAX_OPEN_REQUESTS_PER_CLIENT


def test_cancelling_frees_a_slot(client, api_prefix, setup):
    ids = [
        post(client, api_prefix, setup, title=f"Demande {index}").json()["id"]
        for index in range(MAX_OPEN_REQUESTS_PER_CLIENT)
    ]
    assert post(client, api_prefix, setup).status_code == 409

    cancelled = client.post(
        f"{api_prefix}/client/requests/{ids[0]}/cancel",
        json={"reason": "  Réglé   tout seul  "},
        headers=auth(setup["token"]),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancel_reason"] == "Réglé tout seul"

    assert post(client, api_prefix, setup).status_code == 201


def test_cancelling_twice_is_a_conflict(client, api_prefix, setup):
    request_id = post(client, api_prefix, setup).json()["id"]
    url = f"{api_prefix}/client/requests/{request_id}/cancel"

    assert client.post(url, json={}, headers=auth(setup["token"])).status_code == 200
    assert client.post(url, json={}, headers=auth(setup["token"])).status_code == 409


def test_an_assigned_request_is_not_cancelled_from_here(client, api_prefix, db, setup):
    """A tradesman is already working; cancelling it here would leave him to it."""
    from app.models.request import ServiceRequest

    request_id = post(client, api_prefix, setup).json()["id"]
    db.get(ServiceRequest, request_id).status = RequestStatus.ASSIGNED
    db.commit()

    response = client.post(
        f"{api_prefix}/client/requests/{request_id}/cancel",
        json={},
        headers=auth(setup["token"]),
    )
    assert response.status_code == 409


def test_a_trade_that_does_not_exist_is_refused(client, api_prefix, setup):
    response = post(client, api_prefix, setup, trade_id=999_999)
    assert response.status_code == 422
    assert response.json()["details"]["field"] == "trade_id"


def test_an_inactive_city_is_refused(client, api_prefix, db, setup):
    setup["city"].is_active = False
    db.commit()

    response = post(client, api_prefix, setup)
    assert response.status_code == 422
    assert response.json()["details"]["field"] == "city_id"


def test_a_backwards_budget_is_refused(client, api_prefix, setup):
    response = post(
        client,
        api_prefix,
        setup,
        budget_min_centimes=dirhams(400),
        budget_max_centimes=dirhams(100),
    )
    assert response.status_code == 422
    assert response.json()["details"]["field"] == "budget_max_centimes"


@pytest.mark.parametrize(
    ("role", "phone"), [(Role.PROVIDER, "+212700000001"), (Role.ADMIN, "+212600000001")]
)
def test_only_a_client_posts_requests(client, api_prefix, db, setup, role, phone):
    make_user(db, phone=phone, role=role)
    db.commit()
    token = token_for(client, api_prefix, phone)

    response = client.post(f"{api_prefix}/client/requests", json=body(setup), headers=auth(token))
    assert response.status_code == 403


def test_posting_needs_an_account(client, api_prefix, setup):
    assert client.post(f"{api_prefix}/client/requests", json=body(setup)).status_code == 401


# --- C3: the offers his request drew ------------------------------------


def make_offer(db, *, request_id, provider, price_dh, status=OfferStatus.PENDING, message=""):
    offer = Offer(
        request_id=request_id,
        provider_id=provider.id,
        price_centimes=dirhams(price_dh),
        message=message,
        status=status,
    )
    db.add(offer)
    db.flush()
    return offer


@pytest.fixture
def with_offers(client, api_prefix, db, setup):
    """One request, three tradesmen, three prices."""
    request_id = post(client, api_prefix, setup).json()["id"]

    cheap = make_provider(
        db,
        phone="+212700000010",
        city=setup["city"],
        trades=[setup["trade"]],
        name="Rachid Alaoui",
        rating=4.2,
        rating_count=18,
        jobs_done=40,
    )
    dear = make_provider(
        db,
        phone="+212700000011",
        city=setup["city"],
        trades=[setup["trade"]],
        name="Hamid Bennani",
        rating=4.9,
        rating_count=120,
        jobs_done=310,
    )
    gone = make_provider(
        db,
        phone="+212700000012",
        city=setup["city"],
        trades=[setup["trade"]],
        name="Younes Idrissi",
    )

    make_offer(db, request_id=request_id, provider=cheap, price_dh=250, message="Je passe demain.")
    make_offer(db, request_id=request_id, provider=dear, price_dh=450)
    make_offer(db, request_id=request_id, provider=gone, price_dh=300, status=OfferStatus.WITHDRAWN)

    db.get(ServiceRequest, request_id).offers_count = 3
    db.commit()
    return request_id


def test_the_offers_come_back_with_the_tradesman_behind_each(
    client, api_prefix, setup, with_offers
):
    response = client.get(
        f"{api_prefix}/client/requests/{with_offers}/offers", headers=auth(setup["token"])
    )
    assert response.status_code == 200, response.text

    offers = response.json()
    assert len(offers) == 3

    by_name = {offer["provider"]["full_name"]: offer for offer in offers}
    assert by_name["Hamid Bennani"]["price_centimes"] == dirhams(450)
    assert by_name["Hamid Bennani"]["provider"]["rating_avg"] == 4.9
    assert by_name["Hamid Bennani"]["provider"]["jobs_done"] == 310
    assert by_name["Rachid Alaoui"]["message"] == "Je passe demain."
    assert by_name["Rachid Alaoui"]["provider"]["city"]["slug"] == "casablanca"


def test_a_withdrawn_offer_is_shown_rather_than_dropped(client, api_prefix, setup, with_offers):
    """`offers_count` says three. A list of two would make that a lie."""
    offers = client.get(
        f"{api_prefix}/client/requests/{with_offers}/offers", headers=auth(setup["token"])
    ).json()

    request = client.get(
        f"{api_prefix}/client/requests/{with_offers}", headers=auth(setup["token"])
    ).json()

    assert len(offers) == request["offers_count"]
    assert {offer["status"] for offer in offers} == {"pending", "withdrawn"}


def test_a_request_with_no_offers_answers_with_an_empty_list(client, api_prefix, setup):
    request_id = post(client, api_prefix, setup).json()["id"]

    response = client.get(
        f"{api_prefix}/client/requests/{request_id}/offers", headers=auth(setup["token"])
    )
    assert response.status_code == 200
    assert response.json() == []


def test_somebody_elses_offers_are_not_found(client, api_prefix, db, setup, with_offers):
    make_user(db, phone="+212611111112", role=Role.CLIENT)
    db.commit()
    other = token_for(client, api_prefix, "0611111112")

    response = client.get(f"{api_prefix}/client/requests/{with_offers}/offers", headers=auth(other))
    # Not 403: the id space is guessable, and a 403 would confirm it exists.
    assert response.status_code == 404


def test_reading_offers_needs_an_account(client, api_prefix, with_offers):
    assert client.get(f"{api_prefix}/client/requests/{with_offers}/offers").status_code == 401


# --- C3: declining one offer, and editing before any arrive -------------


def test_declining_one_offer_leaves_the_others_alone(client, api_prefix, db, setup, with_offers):
    offers = client.get(
        f"{api_prefix}/client/requests/{with_offers}/offers", headers=auth(setup["token"])
    ).json()
    target = next(o for o in offers if o["status"] == "pending")

    response = client.post(
        f"{api_prefix}/client/requests/{with_offers}/offers/{target['id']}/decline",
        headers=auth(setup["token"]),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

    after = client.get(
        f"{api_prefix}/client/requests/{with_offers}/offers", headers=auth(setup["token"])
    ).json()
    assert sum(1 for o in after if o["status"] == "pending") == 1
    # And the request is still open for the ones he has not answered.
    db.expire_all()
    assert db.get(ServiceRequest, with_offers).status is RequestStatus.OPEN


def test_an_offer_cannot_be_declined_twice(client, api_prefix, setup, with_offers):
    offers = client.get(
        f"{api_prefix}/client/requests/{with_offers}/offers", headers=auth(setup["token"])
    ).json()
    target = next(o for o in offers if o["status"] == "pending")
    url = f"{api_prefix}/client/requests/{with_offers}/offers/{target['id']}/decline"

    assert client.post(url, headers=auth(setup["token"])).status_code == 200
    assert client.post(url, headers=auth(setup["token"])).status_code == 409


def test_somebody_elses_offer_cannot_be_declined(client, api_prefix, db, setup, with_offers):
    offers = client.get(
        f"{api_prefix}/client/requests/{with_offers}/offers", headers=auth(setup["token"])
    ).json()
    target = next(o for o in offers if o["status"] == "pending")

    make_user(db, phone="+212611111119", role=Role.CLIENT)
    db.commit()
    other = token_for(client, api_prefix, "0611111119")

    response = client.post(
        f"{api_prefix}/client/requests/{with_offers}/offers/{target['id']}/decline",
        headers=auth(other),
    )
    assert response.status_code == 404


def test_a_request_can_be_rewritten_while_nobody_has_answered(
    client, api_prefix, db, setup
):
    request_id = post(client, api_prefix, setup).json()["id"]

    response = client.patch(
        f"{api_prefix}/client/requests/{request_id}",
        json=body(setup, title="Chauffe-eau en panne", urgency="flexible"),
        headers=auth(setup["token"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Chauffe-eau en panne"
    assert response.json()["urgency"] == "flexible"


def test_editing_replaces_the_photos_wholesale(client, api_prefix, setup):
    request_id = post(client, api_prefix, setup).json()["id"]

    updated = client.patch(
        f"{api_prefix}/client/requests/{request_id}",
        json=body(setup, photo_paths=["public/requests/1/b.jpg", "public/requests/1/c.jpg"]),
        headers=auth(setup["token"]),
    ).json()
    assert [photo["url"].rsplit("/", 1)[-1] for photo in updated["photos"]] == [
        "b.jpg",
        "c.jpg",
    ]


def test_once_one_offer_exists_the_request_is_frozen(client, api_prefix, setup, with_offers):
    """A tradesman priced the job as it was written. Changing it under his quote
    turns a 450 DH answer to "unblock a sink" into an answer to something else."""
    response = client.patch(
        f"{api_prefix}/client/requests/{with_offers}",
        json=body(setup, title="Refaire toute la salle de bain"),
        headers=auth(setup["token"]),
    )
    assert response.status_code == 409
    assert response.json()["details"]["reason"] == "already_answered"


def test_a_cancelled_request_cannot_be_rewritten(client, api_prefix, db, setup):
    request_id = post(client, api_prefix, setup).json()["id"]
    db.get(ServiceRequest, request_id).status = RequestStatus.CANCELLED
    db.commit()

    response = client.patch(
        f"{api_prefix}/client/requests/{request_id}",
        json=body(setup),
        headers=auth(setup["token"]),
    )
    assert response.status_code == 409


def test_somebody_elses_request_cannot_be_rewritten(client, api_prefix, db, setup):
    request_id = post(client, api_prefix, setup).json()["id"]

    make_user(db, phone="+212611111120", role=Role.CLIENT)
    db.commit()
    other = token_for(client, api_prefix, "0611111120")

    response = client.patch(
        f"{api_prefix}/client/requests/{request_id}",
        json=body(setup, title="Pas à moi"),
        headers=auth(other),
    )
    assert response.status_code == 404
