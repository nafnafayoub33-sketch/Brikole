"""C9 and M12 — the chat, and the handshake that turns it into a job.

The flow this covers is the one the platform lives on: two people talk, they
agree, and *then* the job exists and the fee is charged. Everything that
matters here is about what does **not** happen before that moment.
"""

from __future__ import annotations

import pytest

from app.core.enums import JobStatus, OfferStatus, RequestStatus, Role, TransactionType
from app.core.money import dirhams
from app.models.conversation import Message
from app.models.credit import CreditAccount, CreditTransaction
from app.models.job import Job
from app.models.offer import Offer
from app.models.request import ServiceRequest
from tests.test_auth_api import auth, make_user, token_for
from tests.test_offers_api import stage  # noqa: F401 — the fixture is the point


@pytest.fixture
def talking(client, api_prefix, db, stage):  # noqa: F811
    """An offer sent, and the conversation the client opened on it."""
    offer = client.post(
        f"{api_prefix}/pro/requests/{stage['mine']['id']}/offer",
        json={"price_centimes": dirhams(400), "message": "Je peux passer demain."},
        headers=auth(stage["token"]),
    )
    assert offer.status_code in (200, 201), offer.text
    offer_id = offer.json()["id"]

    opened = client.post(
        f"{api_prefix}/offers/{offer_id}/conversation",
        headers=auth(stage["client_token"]),
    )
    assert opened.status_code == 200, opened.text

    return {**stage, "offer_id": offer_id, "conversation": opened.json()}


def as_client(talking):
    return auth(talking["client_token"])


def as_pro(talking):
    return auth(talking["token"])


def thread(client, api_prefix, talking, headers):
    return client.get(
        f"{api_prefix}/conversations/{talking['conversation']['id']}", headers=headers
    )


def send(client, api_prefix, talking, headers, body, **extra):
    return client.post(
        f"{api_prefix}/conversations/{talking['conversation']['id']}/messages",
        json={"body": body, **extra},
        headers=headers,
    )


def propose(client, api_prefix, talking, headers, price, terms=""):
    return client.post(
        f"{api_prefix}/conversations/{talking['conversation']['id']}/propose",
        json={"price_centimes": price, "terms": terms},
        headers=headers,
    )


def agree(client, api_prefix, talking, headers, version):
    return client.post(
        f"{api_prefix}/conversations/{talking['conversation']['id']}/agree",
        json={"version": version},
        headers=headers,
    )


# -- opening ----------------------------------------------------------------


class TestOpening:
    def test_tapping_an_offer_commits_to_nothing(self, client, api_prefix, db, talking):
        """No job, no charge, and the request still open. This is the whole
        difference from the button it replaces."""
        assert db.query(Job).count() == 0
        assert db.query(CreditTransaction).count() == 0

        offer = db.get(Offer, talking["offer_id"])
        assert offer is not None
        assert offer.status is OfferStatus.PENDING

        request = db.get(ServiceRequest, talking["mine"]["id"])
        assert request is not None
        assert request.status is RequestStatus.OPEN

    def test_opening_twice_returns_the_same_thread(self, client, api_prefix, talking):
        again = client.post(
            f"{api_prefix}/offers/{talking['offer_id']}/conversation",
            headers=as_client(talking),
        )
        assert again.status_code == 200
        assert again.json()["id"] == talking["conversation"]["id"]

    def test_the_price_starts_at_what_he_offered(self, client, api_prefix, talking):
        assert talking["conversation"]["price_centimes"] == dirhams(400)
        assert talking["conversation"]["version"] == 1

    def test_the_tradesman_reads_the_same_thread(self, client, api_prefix, talking):
        body = thread(client, api_prefix, talking, as_pro(talking)).json()
        assert body["conversation"]["viewer_is_client"] is False
        assert body["conversation"]["other"]["full_name"]

    def test_another_client_gets_a_404_not_a_403(self, client, api_prefix, db, talking):
        """A 403 would confirm the conversation exists."""
        make_user(db, phone="+212611119999", role=Role.CLIENT)
        db.commit()
        stranger = auth(token_for(client, api_prefix, "0611119999"))

        assert thread(client, api_prefix, talking, stranger).status_code == 404


# -- the phone number -------------------------------------------------------


class TestTheClientsNumber:
    """She has no balance to charge, so blocking is the only lever there is —
    and she has no reason to want off the platform: she pays it nothing."""

    def test_no_phone_number_anywhere_in_the_thread(self, client, api_prefix, talking):
        body = thread(client, api_prefix, talking, as_client(talking)).text
        assert "+2127" not in body
        assert "phone" not in body

    def test_hers_is_struck_out(self, client, api_prefix, talking):
        sent = send(
            client, api_prefix, talking, as_client(talking), "mon num 06 12 34 56 78"
        ).json()
        assert sent["redacted_count"] == 1
        assert "0612345678" not in sent["body"].replace(" ", "")

    def test_the_message_is_still_delivered(self, client, api_prefix, talking):
        """Refusing it would teach people to write `zero six`."""
        send(client, api_prefix, talking, as_client(talking), "appelle 0612345678 stp")
        body = thread(client, api_prefix, talking, as_pro(talking)).json()
        assert any("appelle" in row["body"] for row in body["messages"])

    def test_it_is_not_stored(self, client, api_prefix, db, talking):
        send(client, api_prefix, talking, as_client(talking), "3eyet f 0612345678")

        stored = " ".join(row.body for row in db.query(Message).all())
        assert "0612345678" not in stored
        assert "3eyet f" in stored


class TestTheTradesmansNumber:
    """He may hand it over. It costs him the lead fee, once, for this client —
    the same event as accepting a job, priced the same."""

    def test_it_is_refused_until_he_agrees_to_the_price(
        self, client, api_prefix, db, talking
    ):
        response = send(
            client, api_prefix, talking, as_pro(talking), "3eyet liya f 0612345678"
        )

        assert response.status_code == 402
        body = response.json()
        assert body["code"] == "contact_costs_credit"
        assert body["details"]["fee_centimes"] == dirhams(10)
        # Nothing was sent and nothing was taken.
        assert db.query(CreditTransaction).count() == 0

    def test_agreeing_sends_it_whole_and_charges_the_fee(
        self, client, api_prefix, db, talking
    ):
        sent = send(
            client,
            api_prefix,
            talking,
            as_pro(talking),
            "3eyet liya f 0612345678",
            accept_charge=True,
        ).json()

        assert sent["redacted_count"] == 0
        assert "0612345678" in sent["body"]

        row = db.query(CreditTransaction).one()
        assert row.amount_centimes == -dirhams(10)
        assert row.reason == "contact_revealed"
        assert row.job_id is None

    def test_paying_opens_the_thread_both_ways(self, client, api_prefix, talking):
        """The platform has been paid for this lead. Striking a number out of
        her next message would be superstition."""
        send(
            client, api_prefix, talking, as_pro(talking), "0612345678", accept_charge=True
        )

        hers = send(
            client, api_prefix, talking, as_client(talking), "ok, ana f 0698765432"
        ).json()
        assert hers["redacted_count"] == 0
        assert "0698765432" in hers["body"]

    def test_he_pays_once_for_one_client(self, client, api_prefix, db, talking):
        for _ in range(3):
            send(
                client,
                api_prefix,
                talking,
                as_pro(talking),
                "0612345678",
                accept_charge=True,
            )

        assert db.query(CreditTransaction).count() == 1

    def test_the_handshake_afterwards_does_not_charge_him_twice(
        self, client, api_prefix, db, talking
    ):
        """Billing him twice for one client is the fastest way to teach him
        never to answer a question in the chat again."""
        send(
            client, api_prefix, talking, as_pro(talking), "0612345678", accept_charge=True
        )

        agree(client, api_prefix, talking, as_client(talking), 1)
        body = agree(client, api_prefix, talking, as_pro(talking), 1).json()

        assert body["job_id"] is not None
        assert db.query(CreditTransaction).count() == 1

    def test_a_free_lead_covers_it(self, client, api_prefix, db, talking):
        account = db.query(CreditAccount).one()
        account.free_leads_left = 2
        db.commit()

        send(
            client, api_prefix, talking, as_pro(talking), "0612345678", accept_charge=True
        )

        db.expire_all()
        account = db.query(CreditAccount).one()
        assert account.free_leads_left == 1
        assert account.balance_centimes == dirhams(50)

        # The type says a free lead paid for it; the reason says what it was
        # spent on. Both, because either alone loses half the story.
        row = db.query(CreditTransaction).one()
        assert row.type is TransactionType.FREE_LEAD
        assert row.reason == "contact_revealed"

    def test_a_free_lead_still_closes_the_door_on_the_handshake(
        self, client, api_prefix, db, talking
    ):
        """A free lead freezes zero onto the offer, and zero is a price. The
        guard has to ask whether it is *set*, not whether it is truthy — the
        day someone writes `if not offer.lead_fee_centimes` every tradesman on
        his free leads pays twice."""
        account = db.query(CreditAccount).one()
        account.free_leads_left = 2
        db.commit()

        send(
            client, api_prefix, talking, as_pro(talking), "0612345678", accept_charge=True
        )
        agree(client, api_prefix, talking, as_client(talking), 1)
        agree(client, api_prefix, talking, as_pro(talking), 1)

        db.expire_all()
        assert db.query(CreditTransaction).count() == 1
        assert db.query(CreditAccount).one().free_leads_left == 1

    def test_an_ordinary_message_costs_nothing_and_needs_no_agreement(
        self, client, api_prefix, db, talking
    ):
        """The rule has to be quiet on everything that is not a contact, or a
        tradesman quoting a price learns to distrust the box."""
        for text in ("450 DH et je viens à 15h", "prix 2000dh", "nji f rab3a"):
            sent = send(client, api_prefix, talking, as_pro(talking), text).json()
            assert sent["redacted_count"] == 0
            assert sent["body"] == text

        assert db.query(CreditTransaction).count() == 0

    def test_the_screen_is_told_the_price_before_he_can_be_charged(
        self, client, api_prefix, talking
    ):
        body = thread(client, api_prefix, talking, as_pro(talking)).json()
        assert body["conversation"]["contact_fee_centimes"] == dirhams(10)
        assert body["conversation"]["lead_charged_at"] is None


# -- the handshake ----------------------------------------------------------


class TestTheHandshake:
    def test_one_signature_creates_nothing(self, client, api_prefix, db, talking):
        body = agree(client, api_prefix, talking, as_client(talking), 1).json()

        assert body["client_agreed"] is True
        assert body["provider_agreed"] is False
        assert body["sealed_at"] is None
        assert db.query(Job).count() == 0

    def test_both_signatures_create_the_job_and_charge_the_fee(
        self, client, api_prefix, db, talking
    ):
        agree(client, api_prefix, talking, as_client(talking), 1)
        body = agree(client, api_prefix, talking, as_pro(talking), 1).json()

        assert body["sealed_at"] is not None
        assert body["job_id"] is not None

        job = db.get(Job, body["job_id"])
        assert job is not None
        assert job.status is JobStatus.ASSIGNED

        fee = db.query(CreditTransaction).one()
        assert fee.job_id == job.id

    def test_the_job_is_created_at_the_price_they_agreed_not_the_one_offered(
        self, client, api_prefix, db, talking
    ):
        """He quoted 400 before he had seen the photos. They settled on 550."""
        moved = propose(
            client, api_prefix, talking, as_pro(talking), dirhams(550), "Matériel inclus"
        ).json()

        agree(client, api_prefix, talking, as_client(talking), moved["version"])
        body = agree(client, api_prefix, talking, as_pro(talking), moved["version"]).json()

        job = db.get(Job, body["job_id"])
        assert job is not None
        assert job.agreed_price_centimes == dirhams(550)

    def test_a_price_moved_after_a_signature_clears_it(
        self, client, api_prefix, db, talking
    ):
        """The rule the whole design turns on: he agreed to 400, not to 500."""
        agree(client, api_prefix, talking, as_client(talking), 1)

        moved = propose(
            client, api_prefix, talking, as_pro(talking), dirhams(500)
        ).json()
        assert moved["client_agreed"] is False
        assert moved["version"] == 2

        # And the tradesman signing alone still creates nothing.
        after = agree(client, api_prefix, talking, as_pro(talking), 2).json()
        assert after["sealed_at"] is None
        assert db.query(Job).count() == 0

    def test_signing_a_version_that_has_moved_is_refused(
        self, client, api_prefix, talking
    ):
        propose(client, api_prefix, talking, as_pro(talking), dirhams(500))
        response = agree(client, api_prefix, talking, as_client(talking), 1)

        assert response.status_code == 409
        assert response.json()["details"]["reason"] == "terms_moved"

    def test_sealing_takes_the_request_off_the_market(
        self, client, api_prefix, db, talking
    ):
        agree(client, api_prefix, talking, as_client(talking), 1)
        agree(client, api_prefix, talking, as_pro(talking), 1)

        offer = db.get(Offer, talking["offer_id"])
        assert offer is not None
        assert offer.status is OfferStatus.ACCEPTED

        request = db.get(ServiceRequest, talking["mine"]["id"])
        assert request is not None
        assert request.status is RequestStatus.ASSIGNED

    def test_nothing_moves_after_it_is_sealed(self, client, api_prefix, talking):
        agree(client, api_prefix, talking, as_client(talking), 1)
        agree(client, api_prefix, talking, as_pro(talking), 1)

        assert propose(
            client, api_prefix, talking, as_pro(talking), dirhams(900)
        ).status_code == 409

    def test_the_number_is_readable_once_the_job_exists(
        self, client, api_prefix, talking
    ):
        """C4 and M7 — two people who have agreed to meet need to reach each
        other, and now the platform has been paid for it."""
        agree(client, api_prefix, talking, as_client(talking), 1)
        body = agree(client, api_prefix, talking, as_pro(talking), 1).json()

        job = client.get(
            f"{api_prefix}/jobs/{body['job_id']}", headers=as_client(talking)
        ).json()
        assert job["provider"]["phone"].startswith("+212")

    def test_the_chat_stops_striking_out_numbers_once_it_is_sealed(
        self, client, api_prefix, talking
    ):
        """There is nothing left to protect: they have each other's number."""
        agree(client, api_prefix, talking, as_client(talking), 1)
        agree(client, api_prefix, talking, as_pro(talking), 1)

        sent = send(
            client, api_prefix, talking, as_pro(talking), "je suis au 0612345678"
        ).json()
        assert sent["redacted_count"] == 0
        assert "0612345678" in sent["body"]


# -- taking it back ---------------------------------------------------------


class TestWithdrawing:
    def test_a_signature_can_be_taken_back_before_the_other_lands(
        self, client, api_prefix, talking
    ):
        agree(client, api_prefix, talking, as_client(talking), 1)
        body = client.post(
            f"{api_prefix}/conversations/{talking['conversation']['id']}/withdraw",
            headers=as_client(talking),
        ).json()

        assert body["client_agreed"] is False

    def test_it_cannot_be_taken_back_once_the_job_exists(
        self, client, api_prefix, talking
    ):
        agree(client, api_prefix, talking, as_client(talking), 1)
        agree(client, api_prefix, talking, as_pro(talking), 1)

        response = client.post(
            f"{api_prefix}/conversations/{talking['conversation']['id']}/withdraw",
            headers=as_client(talking),
        )
        assert response.status_code == 409


# -- who may be here --------------------------------------------------------


def test_staff_do_not_read_private_conversations(client, api_prefix, db, talking):
    """A moderator arbitrating a dispute reads the job and what was filed about
    it, not two people's negotiation."""
    make_user(db, phone="+212655000001", role=Role.MODERATOR)
    make_user(db, phone="+212600000001", role=Role.ADMIN)
    db.commit()

    for phone in ("0655000001", "0600000001"):
        headers = auth(token_for(client, api_prefix, phone))
        assert thread(client, api_prefix, talking, headers).status_code == 403


def test_the_tradesman_cannot_open_a_conversation_himself(
    client, api_prefix, talking
):
    """The client chooses who to talk to. An unsolicited thread from every
    tradesman who saw the request is a spam channel."""
    response = client.post(
        f"{api_prefix}/offers/{talking['offer_id']}/conversation",
        headers=as_pro(talking),
    )
    assert response.status_code == 403


# -- being told ------------------------------------------------------------


def unread(client, api_prefix, headers):
    return client.get(f"{api_prefix}/conversations/unread", headers=headers).json()["count"]


class TestUnread:
    def test_the_tradesman_is_told_a_client_opened_a_chat(
        self, client, api_prefix, talking
    ):
        """He sent an offer and went back to work. Without this he has to
        remember to check M6, which is the same as not being told."""
        assert unread(client, api_prefix, as_pro(talking)) == 1

    def test_the_client_who_opened_it_has_nothing_to_read(
        self, client, api_prefix, talking
    ):
        assert unread(client, api_prefix, as_client(talking)) == 0

    def test_reading_the_thread_clears_it(self, client, api_prefix, talking):
        client.post(
            f"{api_prefix}/conversations/{talking['conversation']['id']}/read",
            headers=as_pro(talking),
        )
        assert unread(client, api_prefix, as_pro(talking)) == 0

    def test_a_reply_puts_it_back(self, client, api_prefix, talking):
        client.post(
            f"{api_prefix}/conversations/{talking['conversation']['id']}/read",
            headers=as_pro(talking),
        )
        send(client, api_prefix, talking, as_client(talking), "wach momkin ghedda?")

        assert unread(client, api_prefix, as_pro(talking)) == 1
        # Sending is reading: she has plainly seen the thread she just wrote in.
        assert unread(client, api_prefix, as_client(talking)) == 0

    def test_the_literal_path_wins_over_the_parameter(self, client, api_prefix, talking):
        """`/conversations/unread` must not be read as a conversation called
        "unread" — that is a 422, and a badge that never appears."""
        response = client.get(
            f"{api_prefix}/conversations/unread", headers=as_pro(talking)
        )
        assert response.status_code == 200
        assert "count" in response.json()
