"""M10 — the tradesman reading his reviews, and answering once.

The "once" is the line these tests exist to hold. Everything else about the
screen is a read.
"""

from __future__ import annotations

import pytest

from app.core.enums import JobStatus, ProviderStatus, Role
from app.core.review_reply import MAX_REPLY
from app.models.job import Review
from tests.test_account_api import make_job
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")

    karim = make_provider(
        db, phone="+212700000001", city=city, trades=[trade], name="Karim Zeroual"
    )
    rival = make_provider(db, phone="+212700000002", city=city, trades=[trade])
    pending = make_provider(
        db,
        phone="+212700000003",
        city=city,
        trades=[trade],
        status=ProviderStatus.PENDING,
    )
    author = make_user(db, phone="+212611111111", role=Role.CLIENT)
    db.commit()

    def review(provider, rating: int, comment: str, *, hidden: bool = False) -> Review:
        job = make_job(
            db, client_user=author, provider=provider, status=JobStatus.CONFIRMED
        )
        row = Review(
            job_id=job.id,
            author_id=author.id,
            provider_id=provider.id,
            rating=rating,
            comment=comment,
            is_hidden=hidden,
        )
        db.add(row)
        db.flush()
        return row

    mine = [
        review(karim, 5, "Rapide et propre."),
        review(karim, 4, "Bon travail."),
        review(karim, 2, "En retard."),
    ]
    hidden = review(karim, 1, "Insultes.", hidden=True)
    theirs = review(rival, 5, "Parfait.")
    db.commit()

    return {
        "karim": karim,
        "mine": mine,
        "hidden": hidden,
        "theirs": theirs,
        "token": auth(token_for(client, api_prefix, "0700000001")),
        "rival_token": auth(token_for(client, api_prefix, "0700000002")),
        "pending_token": auth(token_for(client, api_prefix, "0700000003")),
        "client": auth(token_for(client, api_prefix, "0611111111")),
        "pending": pending,
    }


def reply(client, api_prefix, stage, review_id: int, text: str = "Désolé pour le retard."):
    return client.post(
        f"{api_prefix}/pro/reviews/{review_id}/reply",
        json={"reply": text},
        headers=stage["token"],
    )


class TestReading:
    def test_he_sees_his_own_reviews(self, client, api_prefix, stage):
        body = client.get(f"{api_prefix}/pro/reviews", headers=stage["token"]).json()
        assert body["total"] == 3
        assert sorted(item["rating"] for item in body["items"]) == [2, 4, 5]

    def test_newest_first(self, client, api_prefix, stage):
        body = client.get(f"{api_prefix}/pro/reviews", headers=stage["token"]).json()
        assert body["items"][0]["comment"] == "En retard."

    def test_a_hidden_review_is_not_on_his_page_either(self, client, api_prefix, stage):
        """He sees exactly what the public sees. A review D3 took down is not
        his to read: a reply under a review nobody can see is an argument with
        a client about something invisible."""
        body = client.get(f"{api_prefix}/pro/reviews", headers=stage["token"]).json()
        assert all(item["comment"] != "Insultes." for item in body["items"])

    def test_he_never_sees_somebody_elses(self, client, api_prefix, stage):
        body = client.get(f"{api_prefix}/pro/reviews", headers=stage["token"]).json()
        assert all(item["comment"] != "Parfait." for item in body["items"])

    def test_the_author_is_a_first_name_and_an_initial(self, client, api_prefix, stage):
        """The same shape P3 shows the public, because it is the same set."""
        body = client.get(f"{api_prefix}/pro/reviews", headers=stage["token"]).json()
        assert all("." in item["author"]["display_name"] for item in body["items"])

    def test_a_client_has_no_business_here(self, client, api_prefix, stage):
        response = client.get(f"{api_prefix}/pro/reviews", headers=stage["client"])
        assert response.status_code == 403

    def test_a_pending_applicant_is_sent_back_to_m2(self, client, api_prefix, stage):
        """He has no reviews yet, and the screen he needs is his application."""
        response = client.get(f"{api_prefix}/pro/reviews", headers=stage["pending_token"])
        assert response.status_code == 409


class TestTheSummary:
    def test_it_counts_every_score(self, client, api_prefix, stage):
        body = client.get(
            f"{api_prefix}/pro/reviews/summary", headers=stage["token"]
        ).json()

        assert body["breakdown"] == {"1": 0, "2": 1, "3": 0, "4": 1, "5": 1}

    def test_a_hidden_review_counts_nowhere(self, client, api_prefix, stage):
        """It is out of the average, so it has to be out of the bars too, or
        the two halves of the same header disagree."""
        body = client.get(
            f"{api_prefix}/pro/reviews/summary", headers=stage["token"]
        ).json()
        assert body["breakdown"]["1"] == 0

    def test_it_says_how_many_are_waiting_on_him(self, client, api_prefix, stage):
        """The number that turns the screen into a queue."""
        body = client.get(
            f"{api_prefix}/pro/reviews/summary", headers=stage["token"]
        ).json()
        assert body["unanswered"] == 3

    def test_answering_one_lowers_it(self, client, api_prefix, stage):
        reply(client, api_prefix, stage, stage["mine"][0].id)

        body = client.get(
            f"{api_prefix}/pro/reviews/summary", headers=stage["token"]
        ).json()
        assert body["unanswered"] == 2

    def test_summary_is_not_read_as_a_review_id(self, client, api_prefix, stage):
        """The route is declared before `/reviews/{id}` would swallow it."""
        response = client.get(f"{api_prefix}/pro/reviews/summary", headers=stage["token"])
        assert response.status_code == 200


class TestReplyingOnce:
    def test_his_answer_lands_under_the_review(self, client, api_prefix, stage):
        response = reply(client, api_prefix, stage, stage["mine"][2].id)

        assert response.status_code == 200
        body = response.json()
        assert body["reply"] == "Désolé pour le retard."
        assert body["replied_at"] is not None

    def test_the_client_sees_it_on_the_public_page(self, client, api_prefix, stage):
        """A reply nobody reads is not a reply."""
        reply(client, api_prefix, stage, stage["mine"][2].id)

        body = client.get(f"{api_prefix}/providers/{stage['karim'].id}/reviews").json()
        answered = [item for item in body["items"] if item["reply"]]
        assert answered[0]["reply"] == "Désolé pour le retard."

    def test_a_second_answer_is_refused(self, client, api_prefix, stage):
        """"Once" is the rule. A reply that can be rewritten after the client
        has read it is a moving target, not an answer."""
        reply(client, api_prefix, stage, stage["mine"][0].id, "D'accord.")

        response = reply(client, api_prefix, stage, stage["mine"][0].id, "En fait, non.")
        assert response.status_code == 409
        assert response.json()["details"]["reason"] == "already_replied"

    def test_and_the_first_one_stands(self, client, api_prefix, db, stage):
        reply(client, api_prefix, stage, stage["mine"][0].id, "D'accord.")
        reply(client, api_prefix, stage, stage["mine"][0].id, "En fait, non.")

        db.expire_all()
        row = db.get(Review, stage["mine"][0].id)
        assert row is not None
        assert row.reply == "D'accord."

    def test_the_whitespace_is_collapsed(self, client, api_prefix, stage):
        body = reply(
            client, api_prefix, stage, stage["mine"][0].id, "  Merci   beaucoup.  "
        ).json()
        assert body["reply"] == "Merci beaucoup."

    def test_an_empty_answer_is_refused(self, client, api_prefix, stage):
        response = reply(client, api_prefix, stage, stage["mine"][0].id, "     ")
        assert response.status_code == 422

    def test_an_essay_is_refused(self, client, api_prefix, stage):
        response = reply(client, api_prefix, stage, stage["mine"][0].id, "a" * (MAX_REPLY + 1))
        assert response.status_code == 422

    def test_somebody_elses_review_is_a_404(self, client, api_prefix, stage):
        """The id space is guessable, and a 403 would confirm it exists."""
        response = reply(client, api_prefix, stage, stage["theirs"].id)
        assert response.status_code == 404

    def test_a_hidden_review_is_a_404_too(self, client, api_prefix, stage):
        response = reply(client, api_prefix, stage, stage["hidden"].id)
        assert response.status_code == 404

    def test_a_review_that_does_not_exist_is_a_404(self, client, api_prefix, stage):
        assert reply(client, api_prefix, stage, 999999).status_code == 404

    def test_a_client_cannot_reply_to_his_own_review(self, client, api_prefix, stage):
        response = client.post(
            f"{api_prefix}/pro/reviews/{stage['mine'][0].id}/reply",
            json={"reply": "Merci."},
            headers=stage["client"],
        )
        assert response.status_code == 403
