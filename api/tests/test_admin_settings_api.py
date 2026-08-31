"""A7 and A8 — changing the platform's dials, and reading who turned them."""

from __future__ import annotations

import pytest

from app.core.enums import Role
from app.core.money import dirhams
from app.core.policy import DEFAULT_LEAD_FEE_CENTIMES, SettingKey
from app.models.system import AuditLog
from tests.test_auth_api import auth, make_user, token_for


@pytest.fixture
def stage(client, api_prefix, db):
    make_user(db, phone="+212600000001", role=Role.ADMIN)
    make_user(db, phone="+212655000001", role=Role.MODERATOR)
    make_user(db, phone="+212611111111", role=Role.CLIENT)
    db.commit()
    return {
        "admin": token_for(client, api_prefix, "0600000001"),
        "mod": token_for(client, api_prefix, "0655000001"),
        "client": token_for(client, api_prefix, "0611111111"),
    }


def settings(client, api_prefix, stage):
    return client.get(f"{api_prefix}/admin/settings", headers=auth(stage["admin"]))


def patch(client, api_prefix, stage, values, token=None):
    return client.patch(
        f"{api_prefix}/admin/settings",
        json={"values": values},
        headers=auth(token or stage["admin"]),
    )


def value_of(body, key):
    return next(item["value"] for item in body["items"] if item["key"] == key)


# -- A7 ------------------------------------------------------------------


def test_untouched_keys_come_back_on_their_shipped_default(client, api_prefix, stage):
    """And with no author, so A7 does not imply somebody chose them."""
    body = settings(client, api_prefix, stage).json()
    assert value_of(body, SettingKey.DEFAULT_LEAD_FEE) == DEFAULT_LEAD_FEE_CENTIMES

    entry = next(
        item for item in body["items"] if item["key"] == SettingKey.DEFAULT_LEAD_FEE
    )
    assert entry["updated_by_name"] is None
    assert entry["updated_at"] is None


def test_changing_a_setting_takes_effect_and_names_who_did_it(client, api_prefix, stage):
    response = patch(client, api_prefix, stage, {SettingKey.DEFAULT_LEAD_FEE: dirhams(15)})
    assert response.status_code == 200, response.text

    body = settings(client, api_prefix, stage).json()
    assert value_of(body, SettingKey.DEFAULT_LEAD_FEE) == dirhams(15)

    entry = next(
        item for item in body["items"] if item["key"] == SettingKey.DEFAULT_LEAD_FEE
    )
    assert entry["updated_by_name"] is not None
    assert entry["updated_at"] is not None


def test_the_new_lead_fee_is_what_the_tradesman_is_quoted(client, api_prefix, db, stage):
    """A7 is not a display: it changes what the rest of the product charges."""
    from app.models.credit import CreditAccount
    from tests.test_catalog_api import make_city, make_trade
    from tests.test_providers_api import make_provider

    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")
    provider = make_provider(db, phone="+212700000001", city=city, trades=[trade])
    db.add(CreditAccount(provider_id=provider.id, balance_centimes=dirhams(50), free_leads_left=0))
    db.commit()

    patch(client, api_prefix, stage, {SettingKey.DEFAULT_LEAD_FEE: dirhams(25)})

    body = client.get(
        f"{api_prefix}/pro/credit", headers=auth(token_for(client, api_prefix, "0700000001"))
    ).json()
    assert body["default_lead_fee_centimes"] == dirhams(25)


def test_the_bank_details_reach_m9(client, api_prefix, db, stage):
    """The whole reason A7 had to exist: M9 had no way to be filled in."""
    from app.models.credit import CreditAccount
    from tests.test_catalog_api import make_city, make_trade
    from tests.test_providers_api import make_provider

    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")
    provider = make_provider(db, phone="+212700000002", city=city, trades=[trade])
    db.add(CreditAccount(provider_id=provider.id, balance_centimes=0, free_leads_left=0))
    db.commit()

    patch(
        client,
        api_prefix,
        stage,
        {
            SettingKey.BANK_TRANSFER: {
                "bank_name": "Attijariwafa Bank",
                "account_holder": "Brikole SARL",
                "rib": "007 780 0001234567890123 45",
                "instructions": "Mettez votre téléphone en référence.",
            }
        },
    )

    page = client.get(
        f"{api_prefix}/pro/credit/page",
        headers=auth(token_for(client, api_prefix, "0700000002")),
    ).json()
    assert page["bank"]["rib"].startswith("007")
    assert page["bank"]["account_holder"] == "Brikole SARL"


def test_a_partial_write_leaves_the_other_keys_alone(client, api_prefix, stage):
    """Two admins editing different halves of the screen must not clobber."""
    patch(client, api_prefix, stage, {SettingKey.DEFAULT_LEAD_FEE: dirhams(15)})
    patch(client, api_prefix, stage, {SettingKey.DISPUTE_WINDOW_DAYS: 14})

    body = settings(client, api_prefix, stage).json()
    assert value_of(body, SettingKey.DEFAULT_LEAD_FEE) == dirhams(15)
    assert value_of(body, SettingKey.DISPUTE_WINDOW_DAYS) == 14


def test_a_bad_value_rejects_the_whole_batch(client, api_prefix, stage):
    """Saving three fields and rejecting the fourth leaves him guessing which
    of them landed."""
    response = patch(
        client,
        api_prefix,
        stage,
        {SettingKey.DISPUTE_WINDOW_DAYS: 14, SettingKey.DEFAULT_LEAD_FEE: 0},
    )
    assert response.status_code == 422
    assert response.json()["details"]["field"] == SettingKey.DEFAULT_LEAD_FEE

    body = settings(client, api_prefix, stage).json()
    assert value_of(body, SettingKey.DISPUTE_WINDOW_DAYS) != 14


def test_a_key_a7_does_not_own_is_refused(client, api_prefix, stage):
    assert patch(client, api_prefix, stage, {"secret_key": "x"}).status_code == 422


def test_only_an_admin_may_change_them(client, api_prefix, stage):
    for token in (stage["mod"], stage["client"]):
        response = patch(
            client, api_prefix, stage, {SettingKey.DEFAULT_LEAD_FEE: dirhams(15)}, token
        )
        assert response.status_code == 403
    assert client.get(f"{api_prefix}/admin/settings").status_code == 401


# -- A8 ------------------------------------------------------------------


def test_every_change_lands_in_the_log_with_both_values(client, api_prefix, db, stage):
    patch(client, api_prefix, stage, {SettingKey.DEFAULT_LEAD_FEE: dirhams(15)})

    entry = db.query(AuditLog).filter_by(target_type="platform_setting").one()
    assert entry.action == "setting.changed"
    assert entry.before[SettingKey.DEFAULT_LEAD_FEE] == DEFAULT_LEAD_FEE_CENTIMES
    assert entry.after[SettingKey.DEFAULT_LEAD_FEE] == dirhams(15)


def test_writing_the_same_value_is_not_a_line_in_the_log(client, api_prefix, db, stage):
    """A log padded with no-ops is one nobody reads."""
    patch(client, api_prefix, stage, {SettingKey.DEFAULT_LEAD_FEE: dirhams(15)})
    patch(client, api_prefix, stage, {SettingKey.DEFAULT_LEAD_FEE: dirhams(15)})

    assert db.query(AuditLog).filter_by(target_type="platform_setting").count() == 1


def test_the_log_reads_newest_first_with_the_actor_named(client, api_prefix, stage):
    patch(client, api_prefix, stage, {SettingKey.DEFAULT_LEAD_FEE: dirhams(15)})
    patch(client, api_prefix, stage, {SettingKey.DISPUTE_WINDOW_DAYS: 14})

    body = client.get(f"{api_prefix}/admin/audit", headers=auth(stage["admin"])).json()
    assert body["total"] == 2
    assert body["items"][0]["note"] == SettingKey.DISPUTE_WINDOW_DAYS
    assert body["items"][0]["actor_name"] is not None


def test_the_log_filters_by_action_and_target(client, api_prefix, stage):
    patch(client, api_prefix, stage, {SettingKey.DEFAULT_LEAD_FEE: dirhams(15)})

    hit = client.get(
        f"{api_prefix}/admin/audit",
        params={"action": "setting.changed"},
        headers=auth(stage["admin"]),
    ).json()
    assert hit["total"] == 1

    miss = client.get(
        f"{api_prefix}/admin/audit",
        params={"action": "provider.approved"},
        headers=auth(stage["admin"]),
    ).json()
    assert miss["total"] == 0


def test_the_filters_offer_only_what_the_log_contains(client, api_prefix, stage):
    patch(client, api_prefix, stage, {SettingKey.DEFAULT_LEAD_FEE: dirhams(15)})

    body = client.get(
        f"{api_prefix}/admin/audit/filters", headers=auth(stage["admin"])
    ).json()
    assert body["actions"] == ["setting.changed"]
    assert body["target_types"] == ["platform_setting"]


def test_the_log_has_no_write_and_no_delete(client, api_prefix, stage):
    """Read-only, and never deletable from the UI."""
    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)(
            f"{api_prefix}/admin/audit", headers=auth(stage["admin"])
        )
        assert response.status_code == 405


def test_only_an_admin_reads_the_log(client, api_prefix, stage):
    for token in (stage["mod"], stage["client"]):
        response = client.get(f"{api_prefix}/admin/audit", headers=auth(token))
        assert response.status_code == 403
