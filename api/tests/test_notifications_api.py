"""C6 — the client's inbox, and the events that fill it.

The table has existed since the schema was written and nothing ever wrote a
row. Half of these tests are about the writes happening at all; the other half
are about the inbox belonging to exactly one person.
"""

from __future__ import annotations

import pytest

from app.core.enums import (
    DisputeStatus,
    JobStatus,
    NotificationKind,
    OfferStatus,
    RequestStatus,
    Role,
)
from app.core.money import dirhams
from app.models.credit import CreditAccount
from app.models.dispute import Dispute
from app.models.offer import Offer
from app.models.request import ServiceRequest
from app.models.system import Notification
from tests.test_account_api import make_job
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")

    provider = make_provider(
        db, phone="+212700000001", city=city, trades=[trade], name="Karim Zeroual"
    )
    db.add(
        CreditAccount(
            provider_id=provider.id, balance_centimes=dirhams(50), free_leads_left=0
        )
    )
    person = make_user(db, phone="+212611111111", role=Role.CLIENT)
    other = make_user(db, phone="+212611111112", role=Role.CLIENT)
    make_user(db, phone="+212655000001", role=Role.MODERATOR)
    db.flush()

    request = ServiceRequest(
        client_id=person.id,
        trade_id=trade.id,
        city_id=city.id,
        title="Fuite sous l'évier",
        description="L'eau coule dès que j'ouvre le robinet.",
        address="12 rue Al Massira",
        status=RequestStatus.OPEN,
    )
    db.add(request)
    db.commit()

    return {
        "person": person,
        "other": other,
        "provider": provider,
        "request": request,
        "trade": trade,
        "token": auth(token_for(client, api_prefix, "0611111111")),
        "other_token": auth(token_for(client, api_prefix, "0611111112")),
        "pro_token": auth(token_for(client, api_prefix, "0700000001")),
        "mod_token": auth(token_for(client, api_prefix, "0655000001")),
    }


def inbox(client, api_prefix, headers):
    return client.get(f"{api_prefix}/notifications", headers=headers).json()


def kinds(db, user_id: int) -> list[str]:
    return [
        row.kind.value
        for row in db.query(Notification).filter(Notification.user_id == user_id).all()
    ]


def send_offer(client, api_prefix, stage, price_dh: int = 300):
    return client.post(
        f"{api_prefix}/pro/requests/{stage['request'].id}/offer",
        json={"price_centimes": dirhams(price_dh), "message": "Je peux passer demain."},
        headers=stage["pro_token"],
    )


class TestWhatFillsIt:
    def test_an_offer_tells_the_client(self, client, api_prefix, db, stage):
        assert send_offer(client, api_prefix, stage).status_code in (200, 201)

        body = inbox(client, api_prefix, stage["token"])
        assert body["total"] == 1
        assert body["items"][0]["kind"] == NotificationKind.OFFER_RECEIVED.value

    def test_it_carries_ids_and_numbers_rather_than_a_sentence(
        self, client, api_prefix, stage
    ):
        """The web owns the wording in three languages. A row holding "Karim a
        envoyé une offre" is a row that stays French forever."""
        send_offer(client, api_prefix, stage, price_dh=450)

        payload = inbox(client, api_prefix, stage["token"])["items"][0]["payload"]
        assert payload["request_id"] == stage["request"].id
        assert payload["price_centimes"] == dirhams(450)
        assert payload["provider_name"] == "Karim Zeroual"

    def test_editing_an_offer_does_not_notify_again(self, client, api_prefix, stage):
        """A notification per price tweak is how a client learns to stop
        looking at the bell."""
        send_offer(client, api_prefix, stage, price_dh=300)
        send_offer(client, api_prefix, stage, price_dh=250)

        assert inbox(client, api_prefix, stage["token"])["total"] == 1

    def test_starting_the_job_tells_the_client(self, client, api_prefix, db, stage):
        job = make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.ASSIGNED,
        )
        db.commit()

        response = client.post(
            f"{api_prefix}/jobs/{job.id}/start", headers=stage["pro_token"]
        )
        assert response.status_code == 200
        assert NotificationKind.JOB_STARTED.value in kinds(db, stage["person"].id)

    def test_finishing_it_asks_him_to_confirm(self, client, api_prefix, db, stage):
        job = make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.IN_PROGRESS,
        )
        db.commit()

        client.post(f"{api_prefix}/jobs/{job.id}/finish", headers=stage["pro_token"])
        assert NotificationKind.JOB_DONE.value in kinds(db, stage["person"].id)

    def test_the_tradesman_is_not_told_about_his_own_move(
        self, client, api_prefix, db, stage
    ):
        """Both of those are his move. The news is for the other side."""
        job = make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.ASSIGNED,
        )
        db.commit()

        client.post(f"{api_prefix}/jobs/{job.id}/start", headers=stage["pro_token"])
        assert kinds(db, stage["provider"].user_id) == []

    def test_an_answer_on_a_dispute_reaches_the_other_side(
        self, client, api_prefix, db, stage
    ):
        job = make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.CONFIRMED,
        )
        dispute = Dispute(
            job_id=job.id,
            opened_by_id=stage["person"].id,
            against_id=stage["provider"].user_id,
            reason="work_not_done",
            description="Rien fait.",
            status=DisputeStatus.OPEN,
        )
        db.add(dispute)
        db.commit()

        client.post(
            f"{api_prefix}/disputes/{dispute.id}/messages",
            json={"body": "J'étais bien passé."},
            headers=stage["pro_token"],
        )

        assert NotificationKind.DISPUTE_UPDATE.value in kinds(db, stage["person"].id)

    def test_and_never_the_person_who_just_spoke(self, client, api_prefix, db, stage):
        job = make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.CONFIRMED,
        )
        dispute = Dispute(
            job_id=job.id,
            opened_by_id=stage["person"].id,
            against_id=stage["provider"].user_id,
            reason="work_not_done",
            description="Rien fait.",
            status=DisputeStatus.OPEN,
        )
        db.add(dispute)
        db.commit()

        client.post(
            f"{api_prefix}/disputes/{dispute.id}/messages",
            json={"body": "Toujours rien."},
            headers=stage["token"],
        )

        assert kinds(db, stage["person"].id) == []

    def test_an_internal_note_notifies_nobody(self, client, api_prefix, db, stage):
        """Telling a client something was said that he cannot read is worse
        than saying nothing."""
        job = make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.CONFIRMED,
        )
        dispute = Dispute(
            job_id=job.id,
            opened_by_id=stage["person"].id,
            against_id=stage["provider"].user_id,
            reason="work_not_done",
            description="Rien fait.",
            status=DisputeStatus.OPEN,
        )
        db.add(dispute)
        db.commit()

        client.post(
            f"{api_prefix}/disputes/{dispute.id}/messages",
            json={"body": "Photos douteuses.", "is_internal": True},
            headers=stage["mod_token"],
        )

        assert kinds(db, stage["person"].id) == []
        assert kinds(db, stage["provider"].user_id) == []

    def test_a_notification_dies_with_the_thing_that_caused_it(
        self, client, api_prefix, db, stage
    ):
        """It is written in the same transaction, so a refused offer leaves no
        row promising one."""
        offer = Offer(
            request_id=stage["request"].id,
            provider_id=stage["provider"].id,
            price_centimes=dirhams(300),
            message="",
            status=OfferStatus.ACCEPTED,
        )
        db.add(offer)
        db.commit()

        # A second send onto an accepted offer is refused outright.
        assert send_offer(client, api_prefix, stage).status_code == 409
        assert kinds(db, stage["person"].id) == []


class TestTheInbox:
    def test_it_is_his_alone(self, client, api_prefix, stage):
        send_offer(client, api_prefix, stage)

        assert inbox(client, api_prefix, stage["other_token"])["total"] == 0

    def test_newest_first(self, client, api_prefix, db, stage):
        send_offer(client, api_prefix, stage)
        job = make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.ASSIGNED,
        )
        db.commit()
        client.post(f"{api_prefix}/jobs/{job.id}/start", headers=stage["pro_token"])

        items = inbox(client, api_prefix, stage["token"])["items"]
        assert items[0]["kind"] == NotificationKind.JOB_STARTED.value

    def test_a_stranger_gets_nothing(self, client, api_prefix):
        assert client.get(f"{api_prefix}/notifications").status_code == 401


class TestReadAndUnread:
    def test_a_new_one_is_unread(self, client, api_prefix, stage):
        send_offer(client, api_prefix, stage)

        body = client.get(f"{api_prefix}/notifications/unread", headers=stage["token"])
        assert body.json()["count"] == 1

    def test_unread_is_not_read_as_an_id(self, client, api_prefix, stage):
        """The route is declared before `/{id}/read` could swallow it."""
        response = client.get(f"{api_prefix}/notifications/unread", headers=stage["token"])
        assert response.status_code == 200

    def test_reading_the_list_marks_nothing(self, client, api_prefix, stage):
        """A glance at the bell must not erase what he has not looked at."""
        send_offer(client, api_prefix, stage)
        inbox(client, api_prefix, stage["token"])

        body = client.get(f"{api_prefix}/notifications/unread", headers=stage["token"])
        assert body.json()["count"] == 1

    def test_opening_one_marks_it(self, client, api_prefix, stage):
        send_offer(client, api_prefix, stage)
        one = inbox(client, api_prefix, stage["token"])["items"][0]

        response = client.post(
            f"{api_prefix}/notifications/{one['id']}/read", headers=stage["token"]
        )
        assert response.status_code == 200
        assert response.json()["read_at"] is not None

        body = client.get(f"{api_prefix}/notifications/unread", headers=stage["token"])
        assert body.json()["count"] == 0

    def test_reading_it_twice_keeps_the_first_time(self, client, api_prefix, stage):
        """Re-stamping it would move a thing that already happened."""
        send_offer(client, api_prefix, stage)
        one = inbox(client, api_prefix, stage["token"])["items"][0]

        first = client.post(
            f"{api_prefix}/notifications/{one['id']}/read", headers=stage["token"]
        ).json()
        second = client.post(
            f"{api_prefix}/notifications/{one['id']}/read", headers=stage["token"]
        ).json()

        assert first["read_at"] == second["read_at"]

    def test_mark_all_read_clears_the_badge(self, client, api_prefix, db, stage):
        send_offer(client, api_prefix, stage)
        job = make_job(
            db,
            client_user=stage["person"],
            provider=stage["provider"],
            status=JobStatus.ASSIGNED,
        )
        db.commit()
        client.post(f"{api_prefix}/jobs/{job.id}/start", headers=stage["pro_token"])

        assert (
            client.get(
                f"{api_prefix}/notifications/unread", headers=stage["token"]
            ).json()["count"]
            == 2
        )

        response = client.post(f"{api_prefix}/notifications/read", headers=stage["token"])
        assert response.status_code == 204

        assert (
            client.get(
                f"{api_prefix}/notifications/unread", headers=stage["token"]
            ).json()["count"]
            == 0
        )

    def test_it_clears_only_his_own(self, client, api_prefix, db, stage):
        send_offer(client, api_prefix, stage)
        db.add(
            Notification(
                user_id=stage["other"].id,
                kind=NotificationKind.JOB_DONE,
                payload={"job_id": 1},
            )
        )
        db.commit()

        client.post(f"{api_prefix}/notifications/read", headers=stage["token"])

        assert (
            client.get(
                f"{api_prefix}/notifications/unread", headers=stage["other_token"]
            ).json()["count"]
            == 1
        )

    def test_somebody_elses_notification_is_a_404(self, client, api_prefix, stage):
        """The id space is guessable, and a 403 would confirm it exists."""
        send_offer(client, api_prefix, stage)
        one = inbox(client, api_prefix, stage["token"])["items"][0]

        response = client.post(
            f"{api_prefix}/notifications/{one['id']}/read", headers=stage["other_token"]
        )
        assert response.status_code == 404
