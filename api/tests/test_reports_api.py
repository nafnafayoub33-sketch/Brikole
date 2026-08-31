"""Filing a report, and D3 — the moderator clearing them."""

from __future__ import annotations

import pytest

from app.core.enums import JobStatus, OfferStatus, RequestStatus, Role, UserStatus
from app.core.money import dirhams
from app.models.job import Job, Review
from app.models.offer import Offer
from app.models.request import ServiceRequest
from app.models.system import AuditLog
from app.models.user import User
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    """A tradesman with one review on him, a client, and a moderator."""
    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")
    provider = make_provider(
        db, phone="+212700000001", city=city, trades=[trade], name="Karim Zeroual"
    )
    author = make_user(db, phone="+212611111111", role=Role.CLIENT)
    make_user(db, phone="+212611111112", role=Role.CLIENT)
    make_user(db, phone="+212655000001", role=Role.MODERATOR)
    make_user(db, phone="+212600000001", role=Role.ADMIN)
    db.flush()

    # A real request and offer behind the job: the foreign keys are real, and a
    # fixture that invents ids only proves the test can lie.
    request = ServiceRequest(
        client_id=author.id,
        trade_id=trade.id,
        city_id=city.id,
        title="Fuite sous l'évier",
        description="L'eau coule dès que j'ouvre le robinet.",
        address="12 rue Al Massira",
        status=RequestStatus.DONE,
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
        client_id=author.id,
        provider_id=provider.id,
        agreed_price_centimes=dirhams(300),
        status=JobStatus.CONFIRMED,
    )
    db.add(job)
    db.flush()

    review = Review(
        job_id=job.id,
        author_id=author.id,
        provider_id=provider.id,
        rating=1,
        comment="Voleur, ne l'appelez jamais.",
    )
    db.add(review)
    db.commit()

    return {
        "provider": provider,
        "review": review,
        "author": author,
        "client": token_for(client, api_prefix, "0611111111"),
        "other": token_for(client, api_prefix, "0611111112"),
        "pro": token_for(client, api_prefix, "0700000001"),
        "mod": token_for(client, api_prefix, "0655000001"),
        "admin": token_for(client, api_prefix, "0600000001"),
    }


def file(client, api_prefix, stage, token=None, **body):
    payload = {
        "target_type": "review",
        "target_id": stage["review"].id,
        "reason": "offensive",
        "description": "Insultes dans le commentaire.",
    }
    payload.update(body)
    return client.post(
        f"{api_prefix}/reports", json=payload, headers=auth(token or stage["pro"])
    )


# -- filing --------------------------------------------------------------


def test_a_tradesman_can_report_a_review_about_him(client, api_prefix, stage):
    response = file(client, api_prefix, stage)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["status"] == "open"
    assert body["content"]["body"] == "Voleur, ne l'appelez jamais."
    assert body["content"]["rating"] == 1


def test_a_client_can_report_a_profile(client, api_prefix, stage):
    response = file(
        client,
        api_prefix,
        stage,
        token=stage["client"],
        target_type="provider_profile",
        target_id=stage["provider"].id,
        reason="fake",
    )
    assert response.status_code == 201
    assert response.json()["content"]["title"] == "Karim Zeroual"


def test_reporting_your_own_review_is_refused(client, api_prefix, stage):
    """Not moderation — a way to make a moderator read your complaint."""
    response = file(client, api_prefix, stage, token=stage["client"])
    assert response.status_code == 422


def test_reporting_your_own_profile_is_refused(client, api_prefix, stage):
    response = file(
        client,
        api_prefix,
        stage,
        target_type="provider_profile",
        target_id=stage["provider"].id,
    )
    assert response.status_code == 422


def test_the_same_person_cannot_file_it_twice(client, api_prefix, stage):
    assert file(client, api_prefix, stage).status_code == 201
    again = file(client, api_prefix, stage)
    assert again.status_code == 409
    assert again.json()["details"]["reason"] == "already_reported"


def test_a_report_on_something_that_is_not_there_is_refused(client, api_prefix, stage):
    """An empty row in the queue is a moderator's wasted minute."""
    assert file(client, api_prefix, stage, target_id=999_999).status_code == 404


def test_other_needs_a_description(client, api_prefix, stage):
    assert file(client, api_prefix, stage, reason="other", description=" ").status_code == 422


def test_staff_do_not_file_reports_they_act(client, api_prefix, stage):
    """An admin looking at bad content does not queue a complaint for himself."""
    for token in (stage["mod"], stage["admin"]):
        assert file(client, api_prefix, stage, token=token).status_code == 403


def test_filing_needs_an_account(client, api_prefix, stage):
    assert client.post(f"{api_prefix}/reports", json={}).status_code == 401


# -- D3 ------------------------------------------------------------------


def queue(client, api_prefix, stage, tab="open"):
    return client.get(
        f"{api_prefix}/mod/reports", params={"tab": tab}, headers=auth(stage["mod"])
    )


def handle(client, api_prefix, stage, report_id, outcome, note="Vérifié.", token=None):
    return client.post(
        f"{api_prefix}/mod/reports/{report_id}/handle",
        json={"outcome": outcome, "note": note},
        headers=auth(token or stage["mod"]),
    )


def test_the_queue_quotes_the_content_complained_about(client, api_prefix, stage):
    file(client, api_prefix, stage)
    body = queue(client, api_prefix, stage).json()

    assert body["total"] == 1
    row = body["items"][0]
    assert row["reason"] == "offensive"
    assert row["content"]["body"] == "Voleur, ne l'appelez jamais."
    assert row["also_reported"] == 0


def test_a_second_reporter_shows_as_also_reported(client, api_prefix, stage):
    """Three complaints about one review is a different decision from one."""
    file(client, api_prefix, stage)
    file(client, api_prefix, stage, token=stage["other"])

    rows = queue(client, api_prefix, stage).json()["items"]
    assert all(row["also_reported"] == 1 for row in rows)


def test_dismissing_changes_nothing_but_clears_the_row(client, api_prefix, db, stage):
    report_id = file(client, api_prefix, stage).json()["id"]
    response = handle(client, api_prefix, stage, report_id, "dismissed")
    assert response.status_code == 200
    assert response.json()["outcome"] == "dismissed"

    db.expire_all()
    assert db.get(Review, stage["review"].id).is_hidden is False
    assert queue(client, api_prefix, stage).json()["total"] == 0
    assert queue(client, api_prefix, stage, "handled").json()["total"] == 1


def test_hiding_takes_the_review_off_the_profile(client, api_prefix, db, stage):
    report_id = file(client, api_prefix, stage).json()["id"]
    handle(client, api_prefix, stage, report_id, "content_hidden")

    db.expire_all()
    assert db.get(Review, stage["review"].id).is_hidden is True

    # And it is gone from the public profile, which is the point.
    reviews = client.get(
        f"{api_prefix}/providers/{stage['provider'].id}/reviews"
    ).json()
    assert reviews["total"] == 0


def test_a_profile_cannot_be_hidden(client, api_prefix, stage):
    """Taking a tradesman off the market is a suspension, and calling it
    "hidden" would leave nothing saying why he went."""
    report_id = file(
        client,
        api_prefix,
        stage,
        token=stage["client"],
        target_type="provider_profile",
        target_id=stage["provider"].id,
        reason="fake",
    ).json()["id"]

    response = handle(client, api_prefix, stage, report_id, "content_hidden")
    assert response.status_code == 422
    assert response.json()["details"]["field"] == "outcome"


def test_suspending_lands_on_the_author_of_the_content(client, api_prefix, db, stage):
    report_id = file(client, api_prefix, stage).json()["id"]
    handle(client, api_prefix, stage, report_id, "suspended", note="Insultes répétées.")

    db.expire_all()
    author = db.query(User).filter_by(phone="+212611111111").one()
    assert author.status is UserStatus.SUSPENDED
    assert author.suspended_until is not None  # temporary, always
    assert author.suspension_reason == "Insultes répétées."


def test_suspending_on_a_profile_report_lands_on_the_tradesman(
    client, api_prefix, db, stage
):
    report_id = file(
        client,
        api_prefix,
        stage,
        token=stage["client"],
        target_type="provider_profile",
        target_id=stage["provider"].id,
        reason="fake",
    ).json()["id"]

    handle(client, api_prefix, stage, report_id, "suspended", note="Profil mensonger.")

    db.expire_all()
    assert db.query(User).filter_by(phone="+212700000001").one().status is UserStatus.SUSPENDED


def test_a_warning_moves_nothing(client, api_prefix, db, stage):
    report_id = file(client, api_prefix, stage).json()["id"]
    handle(client, api_prefix, stage, report_id, "warned", note="Premier avertissement.")

    db.expire_all()
    assert db.get(Review, stage["review"].id).is_hidden is False
    assert db.query(User).filter_by(phone="+212611111111").one().status is UserStatus.ACTIVE


def test_a_note_is_required(client, api_prefix, stage):
    """The next moderator to see this person reads it."""
    report_id = file(client, api_prefix, stage).json()["id"]
    assert handle(client, api_prefix, stage, report_id, "dismissed", note="  ").status_code == 422


def test_a_handled_report_cannot_be_handled_twice(client, api_prefix, stage):
    """Two moderators on one queue: 409 beats two suspensions on one person."""
    report_id = file(client, api_prefix, stage).json()["id"]
    assert handle(client, api_prefix, stage, report_id, "dismissed").status_code == 200
    assert handle(client, api_prefix, stage, report_id, "suspended").status_code == 409


def test_handling_writes_an_audit_row(client, api_prefix, db, stage):
    report_id = file(client, api_prefix, stage).json()["id"]
    handle(client, api_prefix, stage, report_id, "content_hidden", note="Insultes.")

    entry = db.query(AuditLog).filter_by(action="report.handled").one()
    assert entry.after["outcome"] == "content_hidden"
    assert entry.note == "Insultes."


def test_an_admin_may_also_clear_the_queue(client, api_prefix, stage):
    """He can do everything a moderator can — the permission table says so."""
    report_id = file(client, api_prefix, stage).json()["id"]
    assert handle(
        client, api_prefix, stage, report_id, "dismissed", token=stage["admin"]
    ).status_code == 200


def test_neither_party_can_reach_the_queue(client, api_prefix, stage):
    for token in (stage["client"], stage["pro"]):
        assert client.get(f"{api_prefix}/mod/reports", headers=auth(token)).status_code == 403
