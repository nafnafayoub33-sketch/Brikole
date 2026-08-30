"""M1: the application, and the rules an admin's review depends on."""

from __future__ import annotations

import pytest

from app.core.enums import ProviderStatus, Role
from app.core.policy import FREE_LEADS_NEW_PROVIDER
from app.models.credit import CreditAccount
from app.models.provider import ProviderProfile
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade

VALID_BIO = "Quinze ans d'expérience, je travaille à Casablanca et alentours."


@pytest.fixture
def setup(client, api_prefix, db):
    city = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    painter = make_trade(db, "peintre")
    make_user(db, phone="+212700000001", role=Role.PROVIDER)
    db.commit()
    token = token_for(client, api_prefix, "0700000001")
    return {"city": city, "plumber": plumber, "painter": painter, "token": token}


def application(setup, **overrides):
    body = {
        "trade_ids": [setup["plumber"].id],
        "city_id": setup["city"].id,
        "radius_km": 20,
        "headline": "Plomberie et dépannage",
        "bio": VALID_BIO,
        "years_experience": 15,
        "starting_price_centimes": 15_000,
        "avatar_path": "public/avatars/1/a.jpg",
        "id_card_path": "private/id-cards/1/b.jpg",
        "photo_paths": ["public/portfolio/1/c.jpg"],
    }
    body.update(overrides)
    return body


def test_no_profile_yet_is_a_404_which_is_what_routes_him_to_the_form(
    client, api_prefix, setup
):
    response = client.get(f"{api_prefix}/pro/profile", headers=auth(setup["token"]))
    assert response.status_code == 404


def test_submitting_creates_it_pending(client, api_prefix, setup):
    response = client.post(
        f"{api_prefix}/pro/profile", json=application(setup), headers=auth(setup["token"])
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["status"] == "pending"
    assert body["headline"] == "Plomberie et dépannage"
    assert body["radius_km"] == 20
    assert body["city"]["slug"] == "casablanca"
    assert [t["slug"] for t in body["trades"]] == ["plombier"]
    assert body["id_card_path"] == "private/id-cards/1/b.jpg"
    assert len(body["photos"]) == 1


def test_a_new_application_never_appears_in_the_public_grid(client, api_prefix, setup):
    client.post(
        f"{api_prefix}/pro/profile", json=application(setup), headers=auth(setup["token"])
    )
    assert client.get(f"{api_prefix}/providers").json()["total"] == 0


def test_the_avatar_lands_on_the_account(client, api_prefix, setup):
    client.post(
        f"{api_prefix}/pro/profile", json=application(setup), headers=auth(setup["token"])
    )
    me = client.get(f"{api_prefix}/auth/me", headers=auth(setup["token"])).json()
    assert me["avatar_url"] == "/api/v1/uploads/public/avatars/1/a.jpg"


def test_a_new_tradesman_gets_his_free_leads(client, api_prefix, setup, db):
    client.post(
        f"{api_prefix}/pro/profile", json=application(setup), headers=auth(setup["token"])
    )
    account = db.query(CreditAccount).one()
    assert account.free_leads_left == FREE_LEADS_NEW_PROVIDER
    assert account.balance_centimes == 0


def test_an_application_with_no_identity_document_is_refused(client, api_prefix, setup):
    """It is the one thing an admin's review is actually about."""
    response = client.post(
        f"{api_prefix}/pro/profile",
        json=application(setup, id_card_path=None),
        headers=auth(setup["token"]),
    )
    assert response.status_code == 422
    assert response.json()["details"]["field"] == "id_card_path"


def test_a_trade_that_does_not_exist_is_refused(client, api_prefix, setup):
    response = client.post(
        f"{api_prefix}/pro/profile",
        json=application(setup, trade_ids=[999_999]),
        headers=auth(setup["token"]),
    )
    assert response.status_code == 422
    assert response.json()["details"]["field"] == "trade_ids"


def test_an_inactive_trade_is_refused(client, api_prefix, setup, db):
    setup["painter"].is_active = False
    db.commit()

    response = client.post(
        f"{api_prefix}/pro/profile",
        json=application(setup, trade_ids=[setup["painter"].id]),
        headers=auth(setup["token"]),
    )
    assert response.status_code == 422


def test_only_a_tradesman_has_this_area_at_all(client, api_prefix, db):
    make_user(db, phone="+212611111111", role=Role.CLIENT)
    db.commit()
    token = token_for(client, api_prefix, "0611111111")

    assert client.get(f"{api_prefix}/pro/profile", headers=auth(token)).status_code == 403


def test_a_rejected_application_can_be_corrected_and_the_reason_clears(
    client, api_prefix, setup, db
):
    client.post(
        f"{api_prefix}/pro/profile", json=application(setup), headers=auth(setup["token"])
    )

    profile = db.query(ProviderProfile).one()
    profile.status = ProviderStatus.REJECTED
    profile.rejection_reason = "La photo de la CIN est illisible"
    db.commit()

    seen = client.get(f"{api_prefix}/pro/profile", headers=auth(setup["token"])).json()
    assert seen["rejection_reason"] == "La photo de la CIN est illisible"

    again = client.post(
        f"{api_prefix}/pro/profile",
        json=application(setup, headline="Plomberie, dépannage 7j/7"),
        headers=auth(setup["token"]),
    )
    assert again.status_code == 201
    assert again.json()["status"] == "pending"
    assert again.json()["rejection_reason"] is None


def test_resubmitting_replaces_the_photos_rather_than_stacking_them(
    client, api_prefix, setup
):
    client.post(
        f"{api_prefix}/pro/profile",
        json=application(setup, photo_paths=["public/portfolio/1/a.jpg"]),
        headers=auth(setup["token"]),
    )
    second = client.post(
        f"{api_prefix}/pro/profile",
        json=application(
            setup, photo_paths=["public/portfolio/1/b.jpg", "public/portfolio/1/c.jpg"]
        ),
        headers=auth(setup["token"]),
    )
    assert [photo["url"] for photo in second.json()["photos"]] == [
        "/api/v1/uploads/public/portfolio/1/b.jpg",
        "/api/v1/uploads/public/portfolio/1/c.jpg",
    ]


def test_an_approved_tradesman_cannot_resubmit_himself_back_to_pending(
    client, api_prefix, setup, db
):
    """Once approved, the profile is edited at M8 — resubmitting the
    application would take him out of the grid he was let into."""
    client.post(
        f"{api_prefix}/pro/profile", json=application(setup), headers=auth(setup["token"])
    )
    profile = db.query(ProviderProfile).one()
    profile.status = ProviderStatus.APPROVED
    db.commit()

    response = client.post(
        f"{api_prefix}/pro/profile", json=application(setup), headers=auth(setup["token"])
    )
    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
