"""M8 — the tradesman editing his own shop window.

Two lines the tests exist to hold: he may change everything a client reads
about him, and nothing that decided whether he got here.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.enums import ProviderStatus, Role
from app.core.money import dirhams
from app.models.base import utcnow
from app.models.provider import ProviderProfile
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    rabat = make_city(db, "rabat")
    plombier = make_trade(db, "plombier")
    peintre = make_trade(db, "peintre")

    profile = make_provider(
        db,
        phone="+212700000001",
        city=casa,
        trades=[plombier],
        name="Karim Zeroual",
        headline="Plomberie et dépannage",
    )
    profile.id_card_url = "cin/karim.jpg"

    pending = make_provider(
        db,
        phone="+212700000002",
        city=casa,
        trades=[plombier],
        status=ProviderStatus.PENDING,
    )
    make_user(db, phone="+212611111111", role=Role.CLIENT)
    db.commit()

    return {
        "profile": profile,
        "pending": pending,
        "casa": casa,
        "rabat": rabat,
        "plombier": plombier,
        "peintre": peintre,
        "token": auth(token_for(client, api_prefix, "0700000001")),
        "pending_token": auth(token_for(client, api_prefix, "0700000002")),
        "client": auth(token_for(client, api_prefix, "0611111111")),
    }


def edit(client, api_prefix, stage, **overrides):
    body = {
        "trade_ids": [stage["plombier"].id],
        "city_id": stage["casa"].id,
        "radius_km": 10,
        "headline": "Plomberie et dépannage",
        "bio": "Vingt ans dans le quartier.",
        "years_experience": 20,
        "starting_price_centimes": dirhams(150),
    }
    body.update(overrides)
    return client.patch(f"{api_prefix}/pro/profile", json=body, headers=stage["token"])


def pause(client, api_prefix, stage, *, accepting_work=False, back_on=None):
    return client.patch(
        f"{api_prefix}/pro/profile/availability",
        json={"accepting_work": accepting_work, "back_on": back_on},
        headers=stage["token"],
    )


class TestWhoMayEdit:
    def test_a_client_is_refused(self, client, api_prefix, stage):
        response = client.patch(
            f"{api_prefix}/pro/profile", json={}, headers=stage["client"]
        )
        assert response.status_code == 403

    def test_a_pending_applicant_is_sent_back_to_his_application(
        self, client, api_prefix, stage
    ):
        """While he is pending, the screen he needs is M2 — and the thing he
        edits there is the application itself."""
        response = client.patch(
            f"{api_prefix}/pro/profile",
            json={
                "trade_ids": [stage["plombier"].id],
                "city_id": stage["casa"].id,
                "radius_km": 10,
                "headline": "x",
                "bio": "",
                "years_experience": 1,
            },
            headers=stage["pending_token"],
        )
        assert response.status_code == 409


class TestTheShopWindow:
    def test_he_can_change_what_a_client_reads(self, client, api_prefix, stage):
        body = edit(
            client,
            api_prefix,
            stage,
            headline="Plombier 7j/7",
            bio="  Deux   décennies dans le quartier.  ",
            years_experience=22,
            radius_km=25,
            starting_price_centimes=dirhams(200),
        ).json()

        assert body["headline"] == "Plombier 7j/7"
        assert body["bio"] == "Deux décennies dans le quartier."
        assert body["years_experience"] == 22
        assert body["radius_km"] == 25
        assert body["starting_price_centimes"] == dirhams(200)

    def test_changing_his_trade_moves_his_feed(self, client, api_prefix, stage):
        """The feed is a query, not a stored list, so there is nothing to
        rebuild — but it is the promise the spec makes, so it is tested."""
        edit(client, api_prefix, stage, trade_ids=[stage["peintre"].id])

        body = client.get(f"{api_prefix}/pro/profile", headers=stage["token"]).json()
        assert [trade["slug"] for trade in body["trades"]] == ["peintre"]

    def test_changing_his_city_moves_it_too(self, client, api_prefix, stage):
        body = edit(client, api_prefix, stage, city_id=stage["rabat"].id).json()
        assert body["city"]["slug"] == "rabat"

    def test_he_stays_approved(self, client, api_prefix, db, stage):
        """Sharing the application's code path is how an edit sends an
        approved tradesman back into the queue."""
        edit(client, api_prefix, stage, headline="Plombier 7j/7")

        db.expire_all()
        assert (
            db.get(ProviderProfile, stage["profile"].id).status is ProviderStatus.APPROVED
        )

    def test_his_id_card_is_not_editable(self, client, api_prefix, db, stage):
        """His identity was checked once at A2. Letting him swap the card
        afterwards makes that check mean nothing — the endpoint does not take
        one at all."""
        edit(client, api_prefix, stage, id_card_path="cin/somebody-else.jpg")

        db.expire_all()
        assert db.get(ProviderProfile, stage["profile"].id).id_card_url == "cin/karim.jpg"

    def test_an_inactive_trade_is_refused(self, client, api_prefix, db, stage):
        stage["peintre"].is_active = False
        db.commit()

        response = edit(client, api_prefix, stage, trade_ids=[stage["peintre"].id])
        assert response.status_code == 422
        assert response.json()["details"]["field"] == "trade_ids"

    def test_a_trade_that_does_not_exist_is_refused(self, client, api_prefix, stage):
        assert edit(client, api_prefix, stage, trade_ids=[999999]).status_code == 422

    def test_no_trades_at_all_is_refused(self, client, api_prefix, stage):
        """A tradesman in no trade has an empty feed and appears in no grid."""
        assert edit(client, api_prefix, stage, trade_ids=[]).status_code == 422


class TestThePortfolio:
    def test_a_photo_is_added_and_removed(self, client, api_prefix, stage):
        added = client.post(
            f"{api_prefix}/pro/profile/photos",
            json={"path": "portfolio/one.jpg"},
            headers=stage["token"],
        )
        assert added.status_code == 201
        photos = added.json()["photos"]
        assert len(photos) == 1
        assert photos[0]["url"].endswith("portfolio/one.jpg")

        removed = client.delete(
            f"{api_prefix}/pro/profile/photos/{photos[0]['id']}", headers=stage["token"]
        )
        assert removed.status_code == 200
        assert removed.json()["photos"] == []

    def test_somebody_elses_photo_is_a_404(self, client, api_prefix, stage):
        """The id space is guessable, and a 403 would confirm it exists."""
        response = client.delete(
            f"{api_prefix}/pro/profile/photos/999999", headers=stage["token"]
        )
        assert response.status_code == 404

    def test_the_gallery_has_a_ceiling(self, client, api_prefix, stage):
        for index in range(10):
            client.post(
                f"{api_prefix}/pro/profile/photos",
                json={"path": f"portfolio/{index}.jpg"},
                headers=stage["token"],
            )

        response = client.post(
            f"{api_prefix}/pro/profile/photos",
            json={"path": "portfolio/eleven.jpg"},
            headers=stage["token"],
        )
        assert response.status_code == 422


class TestGoingAway:
    def test_he_starts_taking_work(self, client, api_prefix, stage):
        body = client.get(f"{api_prefix}/pro/profile", headers=stage["token"]).json()
        assert body["availability"] == {
            "accepting_work": True,
            "back_on": None,
            "is_available": True,
        }

    def test_pausing_takes_him_out_of_search(self, client, api_prefix, stage):
        assert client.get(f"{api_prefix}/providers").json()["total"] == 1

        pause(client, api_prefix, stage)

        assert client.get(f"{api_prefix}/providers").json()["total"] == 0

    def test_and_out_of_the_trade_counts(self, client, api_prefix, stage):
        """Or the page says "1 plumber" and then shows none."""
        pause(client, api_prefix, stage)

        counts = {
            row["slug"]: row["providers_count"]
            for row in client.get(f"{api_prefix}/trades").json()
        }
        assert counts["plombier"] == 0

    def test_but_his_own_page_still_opens(self, client, api_prefix, stage):
        """He exists. A client holding his link deserves "back on the 20th"
        rather than a dead page."""
        pause(
            client, api_prefix, stage, back_on=str((utcnow() + timedelta(days=15)).date())
        )

        response = client.get(f"{api_prefix}/providers/{stage['profile'].id}")
        assert response.status_code == 200
        assert response.json()["availability"]["is_available"] is False
        assert response.json()["availability"]["back_on"] is not None

    def test_a_pause_that_has_ended_puts_him_back(self, client, api_prefix, db, stage):
        """Nothing sweeps it: available is computed, so the date doing its job
        needs no job to run."""
        pause(client, api_prefix, stage, back_on=str((utcnow() + timedelta(days=2)).date()))
        assert client.get(f"{api_prefix}/providers").json()["total"] == 0

        db.expire_all()
        profile = db.get(ProviderProfile, stage["profile"].id)
        assert profile is not None
        profile.back_on = (utcnow() - timedelta(days=1)).date()
        db.commit()

        assert client.get(f"{api_prefix}/providers").json()["total"] == 1

    def test_coming_back_early_clears_the_date(self, client, api_prefix, stage):
        """Keeping it would show "back on the 12th" beside a man who is
        already working."""
        pause(client, api_prefix, stage, back_on=str((utcnow() + timedelta(days=9)).date()))
        body = pause(client, api_prefix, stage, accepting_work=True).json()

        assert body["availability"] == {
            "accepting_work": True,
            "back_on": None,
            "is_available": True,
        }

    def test_a_return_date_already_gone_is_refused(self, client, api_prefix, stage):
        response = pause(
            client, api_prefix, stage, back_on=str((utcnow() - timedelta(days=1)).date())
        )
        assert response.status_code == 422
        assert response.json()["details"]["field"] == "back_on"

    def test_further_than_a_year_is_refused(self, client, api_prefix, stage):
        response = pause(
            client, api_prefix, stage, back_on=str((utcnow() + timedelta(days=400)).date())
        )
        assert response.status_code == 422

    def test_a_pending_applicant_reads_as_unavailable(self, client, api_prefix, stage):
        """His switch says "taking work" and the honest answer is still no:
        nobody can reach him yet."""
        body = client.get(
            f"{api_prefix}/pro/profile", headers=stage["pending_token"]
        ).json()

        assert body["availability"]["accepting_work"] is True
        assert body["availability"]["is_available"] is False
