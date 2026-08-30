"""M9 and A5 — submitting a transfer, and an admin confirming it landed."""

from __future__ import annotations

import pytest

from app.core.enums import Role
from app.core.money import dirhams
from app.core.policy import SettingKey
from app.models.credit import CreditAccount, CreditTransaction
from app.models.system import AuditLog
from app.repositories.catalog import SettingsRepository
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
    db.add(CreditAccount(provider_id=provider.id, balance_centimes=0, free_leads_left=0))
    make_user(db, phone="+212600000001", role=Role.ADMIN)

    SettingsRepository(db).set(
        SettingKey.BANK_TRANSFER,
        {
            "bank_name": "Attijariwafa Bank",
            "account_holder": "Brikole SARL",
            "rib": "007 780 0001234567890123 45",
            "instructions": "Mettez votre numéro de téléphone en référence.",
        },
    )
    db.commit()

    return {
        "provider": provider,
        "token": token_for(client, api_prefix, "0700000001"),
        "admin": token_for(client, api_prefix, "0600000001"),
    }


def submit(client, api_prefix, stage, **body):
    payload = {"amount_centimes": dirhams(500), "reference": "TRF-9912"}
    payload.update(body)
    return client.post(f"{api_prefix}/pro/topups", json=payload, headers=auth(stage["token"]))


def page(client, api_prefix, stage):
    return client.get(f"{api_prefix}/pro/credit/page", headers=auth(stage["token"])).json()


# -- M9 ------------------------------------------------------------------


def test_the_page_carries_the_bank_details_he_transfers_into(client, api_prefix, stage):
    body = page(client, api_prefix, stage)
    assert body["bank"]["rib"].startswith("007")
    assert body["bank"]["account_holder"] == "Brikole SARL"
    assert body["preset_amounts"][0] == dirhams(100)


def test_submitting_a_transfer_moves_no_money(client, api_prefix, db, stage):
    """The whole point of the screen: only an admin confirming it does."""
    response = submit(client, api_prefix, stage)
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"

    db.expire_all()
    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    assert account.balance_centimes == 0
    assert db.query(CreditTransaction).count() == 0


def test_a_pending_claim_is_on_his_page(client, api_prefix, stage):
    submit(client, api_prefix, stage)
    body = page(client, api_prefix, stage)
    assert body["topups"][0]["status"] == "pending"
    assert body["topups"][0]["reference"] == "TRF-9912"


def test_only_one_claim_at_a_time(client, api_prefix, stage):
    """A second is almost always him thinking the first did not go through, and
    it is two rows an admin must reconcile against one statement."""
    submit(client, api_prefix, stage)
    again = submit(client, api_prefix, stage)
    assert again.status_code == 409
    assert again.json()["details"]["reason"] == "topup_already_pending"


def test_a_reference_is_required(client, api_prefix, stage):
    response = submit(client, api_prefix, stage, reference="   ")
    assert response.status_code == 422


def test_an_amount_below_the_floor_is_refused(client, api_prefix, stage):
    response = submit(client, api_prefix, stage, amount_centimes=dirhams(10))
    assert response.status_code == 422
    assert response.json()["details"]["field"] == "amount_centimes"


def test_a_client_cannot_top_up_a_balance_he_does_not_have(client, api_prefix, db, stage):
    make_user(db, phone="+212611111111", role=Role.CLIENT)
    db.commit()
    token = token_for(client, api_prefix, "0611111111")

    response = client.post(
        f"{api_prefix}/pro/topups",
        json={"amount_centimes": dirhams(500), "reference": "X"},
        headers=auth(token),
    )
    assert response.status_code == 403


# -- A5 ------------------------------------------------------------------


def queue(client, api_prefix, stage):
    return client.get(f"{api_prefix}/admin/topups", headers=auth(stage["admin"]))


def test_the_queue_shows_the_claim_and_who_made_it(client, api_prefix, stage):
    submit(client, api_prefix, stage)
    body = queue(client, api_prefix, stage).json()

    assert body["total"] == 1
    row = body["items"][0]
    assert row["reference"] == "TRF-9912"
    assert row["provider"]["full_name"] == "Karim Zeroual"
    assert row["provider"]["balance_centimes"] == 0


def test_approving_credits_the_balance_with_its_ledger_row(client, api_prefix, db, stage):
    topup_id = submit(client, api_prefix, stage).json()["id"]

    response = client.post(
        f"{api_prefix}/admin/topups/{topup_id}/approve", headers=auth(stage["admin"])
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    db.expire_all()
    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    assert account.balance_centimes == dirhams(500)

    row = db.query(CreditTransaction).one()
    assert row.type.value == "topup"
    assert row.amount_centimes == dirhams(500)
    assert row.balance_after_centimes == dirhams(500)
    assert row.topup_id == topup_id


def test_approving_writes_an_audit_row(client, api_prefix, db, stage):
    topup_id = submit(client, api_prefix, stage).json()["id"]
    client.post(f"{api_prefix}/admin/topups/{topup_id}/approve", headers=auth(stage["admin"]))

    entry = db.query(AuditLog).filter_by(target_type="topup_request").one()
    assert entry.action == "topup.approved"
    assert entry.before["balance_centimes"] == 0
    assert entry.after["balance_centimes"] == dirhams(500)


def test_rejecting_moves_nothing_and_says_why(client, api_prefix, db, stage):
    topup_id = submit(client, api_prefix, stage).json()["id"]

    response = client.post(
        f"{api_prefix}/admin/topups/{topup_id}/reject",
        json={"reason": "Aucun virement à cette référence."},
        headers=auth(stage["admin"]),
    )
    assert response.status_code == 200
    assert response.json()["rejection_reason"] == "Aucun virement à cette référence."

    db.expire_all()
    assert db.query(CreditTransaction).count() == 0
    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    assert account.balance_centimes == 0


def test_a_rejection_with_no_reason_is_refused(client, api_prefix, stage):
    topup_id = submit(client, api_prefix, stage).json()["id"]
    response = client.post(
        f"{api_prefix}/admin/topups/{topup_id}/reject",
        json={"reason": "   "},
        headers=auth(stage["admin"]),
    )
    assert response.status_code == 422


def test_a_second_admin_gets_a_conflict_rather_than_crediting_twice(
    client, api_prefix, db, stage
):
    topup_id = submit(client, api_prefix, stage).json()["id"]
    first = client.post(
        f"{api_prefix}/admin/topups/{topup_id}/approve", headers=auth(stage["admin"])
    )
    assert first.status_code == 200

    second = client.post(
        f"{api_prefix}/admin/topups/{topup_id}/approve", headers=auth(stage["admin"])
    )
    assert second.status_code == 409

    db.expire_all()
    account = db.query(CreditAccount).filter_by(provider_id=stage["provider"].id).one()
    assert account.balance_centimes == dirhams(500)  # once, not twice


def test_a_rejected_claim_lets_him_submit_another(client, api_prefix, stage):
    topup_id = submit(client, api_prefix, stage).json()["id"]
    client.post(
        f"{api_prefix}/admin/topups/{topup_id}/reject",
        json={"reason": "Référence introuvable"},
        headers=auth(stage["admin"]),
    )
    assert submit(client, api_prefix, stage, reference="TRF-9913").status_code == 201


def test_approving_reopens_the_feed(client, api_prefix, db, stage):
    """The whole reason he is on this screen."""
    assert page(client, api_prefix, stage)["can_take_work"] is False

    topup_id = submit(client, api_prefix, stage).json()["id"]
    client.post(f"{api_prefix}/admin/topups/{topup_id}/approve", headers=auth(stage["admin"]))

    body = page(client, api_prefix, stage)
    assert body["can_take_work"] is True
    assert body["ledger"][0]["reason"] == "topup_approved"


def test_a_tradesman_cannot_approve_his_own_transfer(client, api_prefix, stage):
    topup_id = submit(client, api_prefix, stage).json()["id"]
    response = client.post(
        f"{api_prefix}/admin/topups/{topup_id}/approve", headers=auth(stage["token"])
    )
    assert response.status_code == 403


def test_the_queue_needs_an_admin(client, api_prefix, stage):
    assert queue(client, api_prefix, {"admin": stage["token"]}).status_code == 403
    assert client.get(f"{api_prefix}/admin/topups").status_code == 401
