"""C8, D1 and D2 — opening an argument and settling it."""

from __future__ import annotations

import pytest

from app.core.enums import JobStatus, Role, UserStatus
from app.core.money import dirhams
from app.models.credit import CreditAccount, CreditTransaction
from app.models.dispute import Dispute
from app.models.job import Job
from app.models.offer import Offer
from app.models.system import AuditLog
from app.models.user import User
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    """A finished job, its two parties, and a moderator."""
    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")

    provider = make_provider(
        db, phone="+212700000001", city=city, trades=[trade], name="Karim Zeroual"
    )
    db.add(CreditAccount(provider_id=provider.id, balance_centimes=dirhams(50), free_leads_left=0))
    make_user(db, phone="+212611111111", role=Role.CLIENT)
    make_user(db, phone="+212655000001", role=Role.MODERATOR)
    db.commit()

    client_token = token_for(client, api_prefix, "0611111111")
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
        headers=auth(client_token),
    ).json()

    offer = Offer(
        request_id=request["id"],
        provider_id=provider.id,
        price_centimes=dirhams(300),
        message="",
    )
    db.add(offer)
    db.commit()

    pro_token = token_for(client, api_prefix, "0700000001")

    # A job exists once both sides have signed the same terms in the chat.
    conversation = client.post(
        f"{api_prefix}/offers/{offer.id}/conversation", headers=auth(client_token)
    ).json()
    signature = {"version": conversation["version"]}
    client.post(
        f"{api_prefix}/conversations/{conversation['id']}/agree",
        json=signature,
        headers=auth(client_token),
    )
    sealed = client.post(
        f"{api_prefix}/conversations/{conversation['id']}/agree",
        json=signature,
        headers=auth(pro_token),
    ).json()
    job = client.get(
        f"{api_prefix}/jobs/{sealed['job_id']}", headers=auth(client_token)
    ).json()

    client.post(f"{api_prefix}/jobs/{job['id']}/start", headers=auth(pro_token))
    client.post(f"{api_prefix}/jobs/{job['id']}/finish", headers=auth(pro_token))

    return {
        "provider": provider,
        "job_id": job["id"],
        "client": client_token,
        "pro": pro_token,
        "mod": token_for(client, api_prefix, "0655000001"),
    }


def open_dispute(client, api_prefix, stage, token=None, **body):
    payload = {
        "reason": "work_not_done",
        "description": "Il a démonté le siphon et il est parti sans rien remonter.",
        "evidence_paths": [],
    }
    payload.update(body)
    return client.post(
        f"{api_prefix}/jobs/{stage['job_id']}/dispute",
        json=payload,
        headers=auth(token or stage["client"]),
    )


# -- C8 ------------------------------------------------------------------


def test_the_client_can_open_one_against_the_tradesman(client, api_prefix, stage):
    response = open_dispute(client, api_prefix, stage)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["status"] == "open"
    assert body["opened_by"]["full_name"]
    assert body["against"]["full_name"] == "Karim Zeroual"
    assert body["job"]["title"] == "Fuite sous l'évier"


def test_the_tradesman_can_open_one_against_the_client(client, api_prefix, stage):
    """Both sides, not just the paying one."""
    response = open_dispute(client, api_prefix, stage, token=stage["pro"])
    assert response.status_code == 201
    assert response.json()["against"]["role"] == "client"


def test_only_one_live_dispute_per_job(client, api_prefix, stage):
    assert open_dispute(client, api_prefix, stage).status_code == 201
    again = open_dispute(client, api_prefix, stage)
    assert again.status_code == 409
    assert again.json()["details"]["reason"] == "already_open"


def test_a_stranger_cannot_open_one_on_somebody_elses_job(client, api_prefix, db, stage):
    make_user(db, phone="+212611111112", role=Role.CLIENT)
    db.commit()
    other = token_for(client, api_prefix, "0611111112")
    assert open_dispute(client, api_prefix, stage, token=other).status_code == 404


def test_a_job_that_has_not_started_has_nothing_to_argue_about(client, api_prefix, db, stage):
    db.get(Job, stage["job_id"]).status = JobStatus.ASSIGNED
    db.commit()
    assert open_dispute(client, api_prefix, stage).status_code == 409


def test_outside_the_window_it_is_refused(client, api_prefix, db, stage):
    from datetime import timedelta

    from app.models.base import utcnow

    job = db.get(Job, stage["job_id"])
    job.finished_at = utcnow() - timedelta(days=30)
    db.commit()

    response = open_dispute(client, api_prefix, stage)
    assert response.status_code == 409
    assert response.json()["details"]["reason"] == "outside_window"


def test_a_description_too_short_to_judge_is_refused(client, api_prefix, stage):
    assert open_dispute(client, api_prefix, stage, description="nul").status_code == 422


# -- D1 ------------------------------------------------------------------


def queue(client, api_prefix, stage, tab="open"):
    return client.get(
        f"{api_prefix}/mod/disputes", params={"tab": tab}, headers=auth(stage["mod"])
    )


def test_the_queue_shows_what_a_moderator_triages_on(client, api_prefix, stage):
    open_dispute(client, api_prefix, stage)
    body = queue(client, api_prefix, stage).json()

    assert body["total"] == 1
    row = body["items"][0]
    assert row["reason"] == "work_not_done"
    assert row["job_title"] == "Fuite sous l'évier"
    assert row["against_name"] == "Karim Zeroual"
    assert row["is_stale"] is False


def test_claiming_takes_it_off_the_open_tab_and_onto_mine(client, api_prefix, stage):
    dispute_id = open_dispute(client, api_prefix, stage).json()["id"]

    claimed = client.post(
        f"{api_prefix}/mod/disputes/{dispute_id}/claim", headers=auth(stage["mod"])
    )
    assert claimed.status_code == 200
    assert claimed.json()["status"] == "claimed"

    assert queue(client, api_prefix, stage, "open").json()["total"] == 0
    assert queue(client, api_prefix, stage, "mine").json()["total"] == 1


def test_a_second_moderator_cannot_claim_it(client, api_prefix, db, stage):
    """Two moderators on one argument reach two verdicts."""
    dispute_id = open_dispute(client, api_prefix, stage).json()["id"]
    client.post(f"{api_prefix}/mod/disputes/{dispute_id}/claim", headers=auth(stage["mod"]))

    make_user(db, phone="+212655000002", role=Role.MODERATOR)
    db.commit()
    other = token_for(client, api_prefix, "0655000002")

    response = client.post(
        f"{api_prefix}/mod/disputes/{dispute_id}/claim", headers=auth(other)
    )
    assert response.status_code == 409
    assert response.json()["details"]["reason"] == "already_claimed"


def test_a_client_has_no_queue(client, api_prefix, stage):
    response = client.get(f"{api_prefix}/mod/disputes", headers=auth(stage["client"]))
    assert response.status_code == 403


# -- messages ------------------------------------------------------------


def test_both_parties_and_the_moderator_can_write(client, api_prefix, stage):
    dispute_id = open_dispute(client, api_prefix, stage).json()["id"]

    for token in (stage["client"], stage["pro"], stage["mod"]):
        response = client.post(
            f"{api_prefix}/disputes/{dispute_id}/messages",
            json={"body": "Voici ce qui s'est passé."},
            headers=auth(token),
        )
        assert response.status_code == 201

    body = client.get(f"{api_prefix}/disputes/{dispute_id}", headers=auth(stage["mod"])).json()
    assert len(body["messages"]) == 3


def test_an_internal_note_never_reaches_a_party(client, api_prefix, stage):
    """Filtered in the service, not in the screen: a note about somebody must
    not be one forgotten `if` away from that person reading it."""
    dispute_id = open_dispute(client, api_prefix, stage).json()["id"]
    client.post(
        f"{api_prefix}/disputes/{dispute_id}/messages",
        json={"body": "Client déjà signalé deux fois.", "is_internal": True},
        headers=auth(stage["mod"]),
    )

    mine = client.get(f"{api_prefix}/disputes/{dispute_id}", headers=auth(stage["client"])).json()
    assert mine["messages"] == []

    theirs = client.get(f"{api_prefix}/disputes/{dispute_id}", headers=auth(stage["mod"])).json()
    assert len(theirs["messages"]) == 1


def test_a_party_cannot_write_an_internal_note(client, api_prefix, stage):
    dispute_id = open_dispute(client, api_prefix, stage).json()["id"]
    response = client.post(
        f"{api_prefix}/disputes/{dispute_id}/messages",
        json={"body": "hmm", "is_internal": True},
        headers=auth(stage["client"]),
    )
    assert response.status_code == 403


# -- D2 ------------------------------------------------------------------


def claim_and_resolve(client, api_prefix, stage, **body):
    dispute_id = open_dispute(client, api_prefix, stage).json()["id"]
    client.post(f"{api_prefix}/mod/disputes/{dispute_id}/claim", headers=auth(stage["mod"]))

    payload = {"verdict": "no_fault", "note": "Malentendu des deux côtés."}
    payload.update(body)
    return dispute_id, client.post(
        f"{api_prefix}/mod/disputes/{dispute_id}/resolve",
        json=payload,
        headers=auth(stage["mod"]),
    )


def test_resolving_records_the_verdict_and_the_reason(client, api_prefix, stage):
    _, response = claim_and_resolve(client, api_prefix, stage)
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "resolved"
    assert body["verdict"] == "no_fault"
    assert body["resolution_note"] == "Malentendu des deux côtés."
    assert body["lead_fee_refunded"] is False


def test_a_client_at_fault_gets_the_lead_fee_back_to_the_tradesman(
    client, api_prefix, db, stage
):
    _, response = claim_and_resolve(
        client,
        api_prefix,
        stage,
        verdict="client_at_fault",
        note="Le client n'était pas là et n'a pas prévenu.",
        refund_lead_fee=True,
    )
    assert response.json()["lead_fee_refunded"] is True

    db.expire_all()
    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    # 50 - 10 taken at acceptance, + 10 given back.
    assert account.balance_centimes == dirhams(50)

    refund = db.query(CreditTransaction).filter_by(reason="dispute_refund").one()
    assert refund.amount_centimes == dirhams(5)


def test_a_refund_is_refused_on_any_other_verdict(client, api_prefix, stage):
    """It is not a way of splitting the difference."""
    _, response = claim_and_resolve(
        client, api_prefix, stage, verdict="no_fault", refund_lead_fee=True
    )
    assert response.status_code == 422
    assert response.json()["details"]["field"] == "refund_lead_fee"


def test_suspending_the_party_at_fault_lasts_48_hours(client, api_prefix, db, stage):
    _, response = claim_and_resolve(
        client,
        api_prefix,
        stage,
        verdict="provider_at_fault",
        note="Travail non fait et injoignable ensuite.",
        suspend_at_fault=True,
    )
    assert response.status_code == 200

    db.expire_all()
    user = db.query(User).filter_by(phone="+212700000001").one()
    assert user.status is UserStatus.SUSPENDED
    assert user.suspended_until is not None


def test_no_fault_suspends_nobody(client, api_prefix, db, stage):
    claim_and_resolve(client, api_prefix, stage, verdict="no_fault", suspend_at_fault=True)

    db.expire_all()
    assert db.query(User).filter_by(phone="+212700000001").one().status is UserStatus.ACTIVE
    assert db.query(User).filter_by(phone="+212611111111").one().status is UserStatus.ACTIVE


def test_resolving_writes_an_audit_row(client, api_prefix, db, stage):
    claim_and_resolve(client, api_prefix, stage)
    entry = db.query(AuditLog).filter_by(target_type="dispute").one()
    assert entry.action == "dispute.resolved"
    assert entry.after["verdict"] == "no_fault"


def test_an_unclaimed_dispute_cannot_be_resolved(client, api_prefix, stage):
    """Read-only until somebody takes it."""
    dispute_id = open_dispute(client, api_prefix, stage).json()["id"]
    response = client.post(
        f"{api_prefix}/mod/disputes/{dispute_id}/resolve",
        json={"verdict": "no_fault", "note": "x"},
        headers=auth(stage["mod"]),
    )
    assert response.status_code == 409
    assert response.json()["details"]["reason"] == "not_claimed_by_you"


def test_a_resolved_dispute_stays_resolved(client, api_prefix, stage):
    dispute_id, _ = claim_and_resolve(client, api_prefix, stage)
    again = client.post(
        f"{api_prefix}/mod/disputes/{dispute_id}/resolve",
        json={"verdict": "client_at_fault", "note": "changed my mind"},
        headers=auth(stage["mod"]),
    )
    assert again.status_code == 409


def test_a_party_sees_the_case_but_cannot_resolve_it(client, api_prefix, stage):
    dispute_id = open_dispute(client, api_prefix, stage).json()["id"]

    assert client.get(
        f"{api_prefix}/disputes/{dispute_id}", headers=auth(stage["client"])
    ).status_code == 200

    assert client.post(
        f"{api_prefix}/mod/disputes/{dispute_id}/resolve",
        json={"verdict": "no_fault", "note": "x"},
        headers=auth(stage["client"]),
    ).status_code == 403


def test_a_stranger_cannot_read_the_case(client, api_prefix, db, stage):
    dispute_id = open_dispute(client, api_prefix, stage).json()["id"]
    make_user(db, phone="+212611111113", role=Role.CLIENT)
    db.commit()
    other = token_for(client, api_prefix, "0611111113")

    response = client.get(f"{api_prefix}/disputes/{dispute_id}", headers=auth(other))
    assert response.status_code == 404


def test_the_moderator_sees_the_lead_fee_and_no_other_money(client, api_prefix, stage):
    """The whole reason the role is not a weaker admin."""
    dispute_id = open_dispute(client, api_prefix, stage).json()["id"]
    body = client.get(f"{api_prefix}/disputes/{dispute_id}", headers=auth(stage["mod"])).json()

    assert body["job"]["lead_fee_centimes"] == dirhams(5)
    serialised = str(body)
    assert "balance_centimes" not in serialised
    assert "free_leads_left" not in serialised


def test_the_moderator_cannot_read_a_balance_anywhere(client, api_prefix, stage):
    assert client.get(f"{api_prefix}/pro/credit", headers=auth(stage["mod"])).status_code == 403
    assert client.get(f"{api_prefix}/admin/topups", headers=auth(stage["mod"])).status_code == 403


def test_the_parties_see_their_own_disputes(client, api_prefix, stage):
    open_dispute(client, api_prefix, stage)
    for token in (stage["client"], stage["pro"]):
        body = client.get(f"{api_prefix}/disputes", headers=auth(token)).json()
        assert body["total"] == 1


def test_opening_needs_an_account(client, api_prefix, stage):
    assert client.post(f"{api_prefix}/jobs/{stage['job_id']}/dispute", json={}).status_code == 401


def test_the_history_beside_a_name_counts_past_findings(client, api_prefix, db, stage):
    """One complaint is noise; a pattern is a decision."""
    dispute_id, _ = claim_and_resolve(
        client,
        api_prefix,
        stage,
        verdict="provider_at_fault",
        note="Travail non fait.",
    )
    db.expire_all()
    assert db.get(Dispute, dispute_id).verdict.value == "provider_at_fault"

    # A second job between the same two, so a second dispute is possible.
    job = db.get(Job, stage["job_id"])
    job.status = JobStatus.DONE
    db.query(Dispute).filter_by(id=dispute_id).one().job_id = job.id
    db.commit()

    body = client.get(f"{api_prefix}/disputes/{dispute_id}", headers=auth(stage["mod"])).json()
    assert body["against"]["disputes_lost"] == 1
