"""C7, M11 and D4 — a person's own account.

Three screens, one row, one set of endpoints. The two lines these tests hold:
he may change everything a screen shows about him except the number that *is*
him, and he may not walk away from work somebody else is waiting on.
"""

from __future__ import annotations

import pytest

from app.core.enums import (
    DisputeStatus,
    JobStatus,
    OfferStatus,
    RequestStatus,
    Role,
    UserStatus,
)
from app.core.money import dirhams
from app.models.dispute import Dispute
from app.models.job import Job
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


def make_job(
    db,
    *,
    client_user: User,
    provider: ProviderProfile,
    status: JobStatus,
) -> Job:
    """A job with a real request and offer behind it.

    The foreign keys are real: a fixture that invents ids only proves the test
    can lie.
    """
    request = ServiceRequest(
        client_id=client_user.id,
        trade_id=provider.trades[0].id,
        city_id=provider.city_id,
        title="Fuite sous l'évier",
        description="L'eau coule dès que j'ouvre le robinet.",
        address="12 rue Al Massira",
        status=RequestStatus.ASSIGNED,
    )
    db.add(request)
    db.flush()

    offer = Offer(
        request_id=request.id,
        provider_id=provider.id,
        price_centimes=dirhams(300),
        message="",
        status=OfferStatus.ACCEPTED,
    )
    db.add(offer)
    db.flush()

    job = Job(
        request_id=request.id,
        offer_id=offer.id,
        client_id=client_user.id,
        provider_id=provider.id,
        agreed_price_centimes=dirhams(300),
        status=status,
    )
    db.add(job)
    db.flush()
    return job


@pytest.fixture
def stage(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    rabat = make_city(db, "rabat")
    trade = make_trade(db, "plombier")

    person = make_user(db, phone="+212611111111", role=Role.CLIENT)
    person.city_id = casa.id

    provider = make_provider(db, phone="+212700000001", city=casa, trades=[trade])
    moderator = make_user(db, phone="+212655000001", role=Role.MODERATOR)
    db.commit()

    return {
        "person": person,
        "provider": provider,
        "moderator": moderator,
        "casa": casa,
        "rabat": rabat,
        "trade": trade,
        "token": auth(token_for(client, api_prefix, "0611111111")),
        "provider_token": auth(token_for(client, api_prefix, "0700000001")),
        "mod_token": auth(token_for(client, api_prefix, "0655000001")),
    }


def edit(client, api_prefix, headers, **overrides):
    body = {"full_name": "Youssef Alami", "city_id": None, "language": "ar"}
    body.update(overrides)
    return client.patch(f"{api_prefix}/account", json=body, headers=headers)


class TestWhatHeMayChange:
    def test_he_changes_his_name_city_and_language(self, client, api_prefix, stage):
        body = edit(
            client,
            api_prefix,
            stage["token"],
            full_name="  Youssef   El   Alami  ",
            city_id=stage["rabat"].id,
            language="fr",
        ).json()

        assert body["full_name"] == "Youssef El Alami"
        assert body["city_id"] == stage["rabat"].id
        assert body["language"] == "fr"

    def test_it_answers_with_the_same_shape_as_me(self, client, api_prefix, stage):
        """So the web app can drop it into the session it already holds."""
        edited = edit(client, api_prefix, stage["token"], language="en").json()
        fetched = client.get(f"{api_prefix}/auth/me", headers=stage["token"]).json()
        assert edited == fetched

    def test_his_photo_becomes_a_url(self, client, api_prefix, stage):
        body = edit(
            client, api_prefix, stage["token"], avatar_path="avatars/youssef.jpg"
        ).json()
        assert body["avatar_url"].endswith("avatars/youssef.jpg")

    def test_leaving_the_photo_out_keeps_it(self, client, api_prefix, stage):
        """An edit that forgets to re-send the photo must not wipe it."""
        edit(client, api_prefix, stage["token"], avatar_path="avatars/youssef.jpg")
        body = edit(client, api_prefix, stage["token"], full_name="Youssef Alami").json()
        assert body["avatar_url"].endswith("avatars/youssef.jpg")

    def test_clearing_his_city_is_allowed(self, client, api_prefix, stage):
        body = edit(client, api_prefix, stage["token"], city_id=None).json()
        assert body["city_id"] is None

    def test_every_role_uses_the_same_endpoint(self, client, api_prefix, stage):
        """C7, M11 and D4 are one screen wearing three layouts."""
        for headers in (stage["token"], stage["provider_token"], stage["mod_token"]):
            assert edit(client, api_prefix, headers).status_code == 200


class TestWhatHeMayNot:
    def test_the_phone_is_not_a_field(self, client, api_prefix, db, stage):
        """Not "phone, ignored" — absent. An endpoint that accepts one is an
        endpoint that can take over an account."""
        edit(client, api_prefix, stage["token"], phone="+212699999999")

        db.expire_all()
        person = db.get(User, stage["person"].id)
        assert person is not None
        assert person.phone == "+212611111111"

    def test_the_role_is_not_a_field_either(self, client, api_prefix, db, stage):
        edit(client, api_prefix, stage["token"], role="admin")

        db.expire_all()
        person = db.get(User, stage["person"].id)
        assert person is not None
        assert person.role is Role.CLIENT

    def test_an_empty_name_is_refused(self, client, api_prefix, stage):
        assert edit(client, api_prefix, stage["token"], full_name="   ").status_code == 422

    def test_a_language_the_app_does_not_speak_is_refused(self, client, api_prefix, stage):
        assert edit(client, api_prefix, stage["token"], language="es").status_code == 422

    def test_a_city_that_is_switched_off_is_refused(self, client, api_prefix, db, stage):
        stage["rabat"].is_active = False
        db.commit()

        response = edit(client, api_prefix, stage["token"], city_id=stage["rabat"].id)
        assert response.status_code == 422
        assert response.json()["details"]["field"] == "city_id"

    def test_a_stranger_is_refused(self, client, api_prefix):
        assert edit(client, api_prefix, {}).status_code == 401


class TestClosingIt:
    def test_a_clean_account_can_go(self, client, api_prefix, db, stage):
        assert (
            client.get(f"{api_prefix}/account/commitments", headers=stage["token"]).json()[
                "can_delete"
            ]
            is True
        )

        assert client.delete(f"{api_prefix}/account", headers=stage["token"]).status_code == 204

        db.expire_all()
        person = db.get(User, stage["person"].id)
        assert person is not None
        assert person.status is UserStatus.DELETED

    def test_the_row_survives_him(self, client, api_prefix, db, stage):
        """Every job, review and audit row points here. Removing the row would
        cascade through the history of people who did nothing wrong."""
        client.delete(f"{api_prefix}/account", headers=stage["token"])
        assert db.get(User, stage["person"].id) is not None

    def test_his_tokens_stop_working(self, client, api_prefix, stage):
        client.delete(f"{api_prefix}/account", headers=stage["token"])
        assert client.get(f"{api_prefix}/auth/me", headers=stage["token"]).status_code == 401

    def test_a_deleted_tradesman_leaves_the_search(self, client, api_prefix, stage):
        assert client.get(f"{api_prefix}/providers").json()["total"] == 1

        client.delete(f"{api_prefix}/account", headers=stage["provider_token"])

        assert client.get(f"{api_prefix}/providers").json()["total"] == 0

    def test_a_job_in_progress_holds_him(self, client, api_prefix, db, stage):
        """A tradesman is on his way to a house. Closing the account leaves the
        other side holding a row that points at nobody."""
        make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.IN_PROGRESS,
        )
        db.commit()

        commitments = client.get(
            f"{api_prefix}/account/commitments", headers=stage["token"]
        ).json()
        assert commitments["live_jobs"] == 1
        assert commitments["can_delete"] is False

        response = client.delete(f"{api_prefix}/account", headers=stage["token"])
        assert response.status_code == 409
        assert response.json()["details"]["blocker"] == "jobs"

    def test_a_job_he_has_finished_but_nobody_confirmed_holds_him_too(
        self, client, api_prefix, db, stage
    ):
        """`done` is the moment a disappearing account does the most damage:
        the review, the credit and the dispute window all still hang off it."""
        make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.DONE,
        )
        db.commit()

        assert client.delete(f"{api_prefix}/account", headers=stage["token"]).status_code == 409

    def test_the_tradesmans_side_counts_as_well(self, client, api_prefix, db, stage):
        """The same row is both sides of the marketplace."""
        make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.ASSIGNED,
        )
        db.commit()

        body = client.get(
            f"{api_prefix}/account/commitments", headers=stage["provider_token"]
        ).json()
        assert body["live_jobs"] == 1

    def test_a_finished_job_does_not(self, client, api_prefix, db, stage):
        make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.CONFIRMED,
        )
        db.commit()

        assert client.delete(f"{api_prefix}/account", headers=stage["token"]).status_code == 204

    def test_an_open_dispute_holds_him(self, client, api_prefix, db, stage):
        """Deleting mid-dispute deletes one side's case, and the moderator is
        left with half a story."""
        job = make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.CONFIRMED,
        )
        db.add(
            Dispute(
                job_id=job.id,
                opened_by_id=stage["person"].id,
                against_id=stage["provider"].user_id,
                reason="work_not_done",
                description="Rien fait.",
                status=DisputeStatus.OPEN,
            )
        )
        db.commit()

        commitments = client.get(
            f"{api_prefix}/account/commitments", headers=stage["token"]
        ).json()
        assert commitments["live_disputes"] == 1

        response = client.delete(f"{api_prefix}/account", headers=stage["token"])
        assert response.status_code == 409
        assert response.json()["details"]["blocker"] == "disputes"
