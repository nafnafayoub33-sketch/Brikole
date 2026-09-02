"""A3 — the accounts screen, end to end.

The screen with the most power on the platform, so most of what is checked
here is what it refuses to do.
"""

from __future__ import annotations

import pytest

from app.core.enums import ProviderStatus, Role, UserStatus
from app.models.system import AuditLog
from app.models.user import User
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    """One admin, one moderator, one client, one tradesman."""
    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")

    admin = make_user(db, phone="+212600000001", role=Role.ADMIN)
    moderator = make_user(db, phone="+212655000001", role=Role.MODERATOR)
    ordinary = make_user(db, phone="+212611111111", role=Role.CLIENT)
    provider = make_provider(
        db, phone="+212700000001", city=city, trades=[trade], name="Karim Zeroual"
    )
    db.commit()

    return {
        "token": token_for(client, api_prefix, "0600000001"),
        "admin": admin,
        "moderator": moderator,
        "client": ordinary,
        "provider": provider,
    }


def users(client, api_prefix, stage, **params):
    return client.get(
        f"{api_prefix}/admin/users", params=params, headers=auth(stage["token"])
    )


def detail(client, api_prefix, stage, user_id: int):
    return client.get(f"{api_prefix}/admin/users/{user_id}", headers=auth(stage["token"]))


def audited(db, action: str) -> AuditLog | None:
    return db.query(AuditLog).filter(AuditLog.action == action).one_or_none()


# -- finding somebody -------------------------------------------------------


class TestTheList:
    def test_it_lists_everyone(self, client, api_prefix, stage):
        body = users(client, api_prefix, stage).json()
        assert body["total"] == 4

    def test_it_finds_a_person_by_name(self, client, api_prefix, stage):
        body = users(client, api_prefix, stage, q="Karim").json()
        assert [row["full_name"] for row in body["items"]] == ["Karim Zeroual"]

    def test_a_national_phone_number_finds_its_e164_row(self, client, api_prefix, stage):
        """Phones are stored +212… and typed 06…. One box, both forms."""
        body = users(client, api_prefix, stage, q="0611111111").json()
        assert [row["phone"] for row in body["items"]] == ["+212611111111"]

    def test_an_underscore_is_not_a_wildcard(self, client, api_prefix, stage):
        assert users(client, api_prefix, stage, q="_").json()["total"] == 0

    def test_it_filters_by_role(self, client, api_prefix, stage):
        body = users(client, api_prefix, stage, role="moderator").json()
        assert [row["role"] for row in body["items"]] == ["moderator"]

    def test_a_row_says_whether_the_person_is_also_a_tradesman(
        self, client, api_prefix, stage
    ):
        body = users(client, api_prefix, stage, q="Karim").json()
        assert body["items"][0]["provider_status"] == ProviderStatus.APPROVED.value

    def test_a_deleted_account_stays_out_unless_it_is_asked_for(
        self, client, api_prefix, db, stage
    ):
        stage["client"].status = UserStatus.DELETED
        db.commit()

        assert users(client, api_prefix, stage).json()["total"] == 3
        assert users(client, api_prefix, stage, status="deleted").json()["total"] == 1


# -- one account ------------------------------------------------------------


class TestTheDetail:
    def test_it_carries_the_activity_of_both_sides(self, client, api_prefix, stage):
        """A client and a tradesman are the same row, so both are counted and
        the ones that do not apply come back zero."""
        body = detail(client, api_prefix, stage, stage["client"].id).json()
        assert body["activity"]["requests_posted"] == 0
        assert body["activity"]["offers_sent"] == 0
        assert body["provider"] is None

    def test_a_tradesman_carries_his_profile_and_his_wallet(
        self, client, api_prefix, stage
    ):
        body = detail(client, api_prefix, stage, stage["provider"].user_id).json()
        assert body["provider"]["status"] == ProviderStatus.APPROVED.value
        assert body["provider"]["balance_centimes"] == 0

    def test_somebody_who_is_not_there_is_a_404(self, client, api_prefix, stage):
        assert detail(client, api_prefix, stage, 999_999).status_code == 404


# -- suspending -------------------------------------------------------------


class TestSuspending:
    def test_it_suspends_with_a_date_and_a_reason(self, client, api_prefix, db, stage):
        response = client.post(
            f"{api_prefix}/admin/users/{stage['client'].id}/suspend",
            json={"days": 7, "reason": "Faux devis"},
            headers=auth(stage["token"]),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == UserStatus.SUSPENDED.value
        assert body["suspended_until"] is not None
        assert body["suspension_reason"] == "Faux devis"
        assert audited(db, "user.suspended") is not None

    def test_permanent_leaves_no_end_date(self, client, api_prefix, stage):
        body = client.post(
            f"{api_prefix}/admin/users/{stage['client'].id}/suspend",
            json={"reason": "Compte frauduleux"},
            headers=auth(stage["token"]),
        ).json()

        assert body["status"] == UserStatus.SUSPENDED.value
        assert body["suspended_until"] is None

    def test_a_suspended_person_cannot_sign_in(self, client, api_prefix, stage):
        client.post(
            f"{api_prefix}/admin/users/{stage['client'].id}/suspend",
            json={"reason": "Compte frauduleux"},
            headers=auth(stage["token"]),
        )

        response = client.post(
            f"{api_prefix}/auth/login",
            json={"phone": "0611111111", "password": "khedma2026"},
        )
        assert response.status_code == 403
        assert response.json()["code"] == "account_suspended"

    def test_an_admin_cannot_suspend_himself(self, client, api_prefix, stage):
        response = client.post(
            f"{api_prefix}/admin/users/{stage['admin'].id}/suspend",
            json={"reason": "Test"},
            headers=auth(stage["token"]),
        )
        assert response.status_code == 409
        assert response.json()["code"] == "self_action_refused"

    def test_the_platform_always_keeps_an_admin_who_can_sign_in(
        self, client, api_prefix, db, stage
    ):
        """The property, not the branch.

        `LAST_ADMIN` cannot fire through this router today and that is the
        point: the caller must be an active admin, so if he is not the target
        then he is himself the admin who remains, and if he is the target the
        self-refusal catches him first. Two admins taking turns at each other
        therefore always leaves one standing — which is what this checks, by
        playing the attack out rather than asserting an error code.
        """
        second = make_user(db, phone="+212600000002", role=Role.ADMIN)
        db.commit()
        theirs = auth(token_for(client, api_prefix, "0600000002"))

        # He cannot start with himself.
        assert (
            client.post(
                f"{api_prefix}/admin/users/{second.id}/suspend",
                json={"reason": "Test"},
                headers=theirs,
            ).json()["code"]
            == "self_action_refused"
        )

        # He can take the other one, and then he is alone…
        assert (
            client.post(
                f"{api_prefix}/admin/users/{stage['admin'].id}/suspend",
                json={"reason": "Test"},
                headers=theirs,
            ).status_code
            == 200
        )

        # …and the admin he suspended can no longer reach the screen to
        # suspend him back.
        assert (
            client.post(
                f"{api_prefix}/admin/users/{second.id}/suspend",
                json={"reason": "Test"},
                headers=auth(stage["token"]),
            ).status_code
            == 403
        )

        remaining = (
            db.query(User)
            .filter(User.role == Role.ADMIN, User.status == UserStatus.ACTIVE)
            .count()
        )
        assert remaining == 1

    def test_a_suspension_without_a_reason_is_refused(self, client, api_prefix, stage):
        response = client.post(
            f"{api_prefix}/admin/users/{stage['client'].id}/suspend",
            json={"reason": "   "},
            headers=auth(stage["token"]),
        )
        assert response.status_code == 422


class TestReactivating:
    def test_it_clears_the_suspension_and_the_lockout(self, client, api_prefix, db, stage):
        target = stage["client"]
        target.failed_login_attempts = 4
        db.commit()

        client.post(
            f"{api_prefix}/admin/users/{target.id}/suspend",
            json={"reason": "Faux devis"},
            headers=auth(stage["token"]),
        )
        body = client.post(
            f"{api_prefix}/admin/users/{target.id}/reactivate",
            headers=auth(stage["token"]),
        ).json()

        assert body["status"] == UserStatus.ACTIVE.value
        assert body["suspended_until"] is None
        assert body["suspension_reason"] is None
        assert audited(db, "user.reactivated") is not None

        db.refresh(target)
        assert target.failed_login_attempts == 0

    def test_reactivating_somebody_nobody_suspended_is_a_conflict(
        self, client, api_prefix, stage
    ):
        response = client.post(
            f"{api_prefix}/admin/users/{stage['client'].id}/reactivate",
            headers=auth(stage["token"]),
        )
        assert response.status_code == 409


# -- roles ------------------------------------------------------------------


class TestChangingARole:
    def test_a_client_becomes_a_moderator(self, client, api_prefix, db, stage):
        response = client.patch(
            f"{api_prefix}/admin/users/{stage['client'].id}/role",
            json={"role": "moderator"},
            headers=auth(stage["token"]),
        )

        assert response.status_code == 200
        assert response.json()["role"] == "moderator"

        entry = audited(db, "user.role_changed")
        assert entry is not None
        assert entry.before["role"] == "client"
        assert entry.after["role"] == "moderator"

    def test_the_new_role_applies_to_the_token_already_issued(
        self, client, api_prefix, stage
    ):
        """The role is re-read on every request, so nobody waits for a token
        to expire before losing what he no longer has."""
        theirs = auth(token_for(client, api_prefix, "0611111111"))
        assert client.get(f"{api_prefix}/mod/disputes", headers=theirs).status_code == 403

        client.patch(
            f"{api_prefix}/admin/users/{stage['client'].id}/role",
            json={"role": "moderator"},
            headers=auth(stage["token"]),
        )
        assert client.get(f"{api_prefix}/mod/disputes", headers=theirs).status_code == 200

    def test_nobody_is_made_a_tradesman_from_a_dropdown(self, client, api_prefix, stage):
        response = client.patch(
            f"{api_prefix}/admin/users/{stage['client'].id}/role",
            json={"role": "provider"},
            headers=auth(stage["token"]),
        )
        assert response.status_code == 409
        assert response.json()["code"] == "role_not_assignable"

    def test_a_tradesmans_role_is_locked_by_his_profile(self, client, api_prefix, stage):
        response = client.patch(
            f"{api_prefix}/admin/users/{stage['provider'].user_id}/role",
            json={"role": "client"},
            headers=auth(stage["token"]),
        )
        assert response.status_code == 409
        assert response.json()["code"] == "provider_role_locked"

    def test_an_admin_cannot_demote_himself(self, client, api_prefix, stage):
        response = client.patch(
            f"{api_prefix}/admin/users/{stage['admin'].id}/role",
            json={"role": "client"},
            headers=auth(stage["token"]),
        )
        assert response.status_code == 409
        assert response.json()["code"] == "self_action_refused"

    def test_the_last_admin_cannot_be_demoted(self, client, api_prefix, db, stage):
        """Demoting him locks the platform exactly as suspending him would."""
        second = make_user(db, phone="+212600000002", role=Role.ADMIN)
        db.commit()

        response = client.patch(
            f"{api_prefix}/admin/users/{stage['admin'].id}/role",
            json={"role": "moderator"},
            headers=auth(token_for(client, api_prefix, "0600000002")),
        )
        assert response.status_code == 200

        response = client.patch(
            f"{api_prefix}/admin/users/{second.id}/role",
            json={"role": "moderator"},
            headers=auth(token_for(client, api_prefix, "0600000002")),
        )
        assert response.json()["code"] == "self_action_refused"


# -- creating staff ---------------------------------------------------------


class TestCreatingStaff:
    def test_an_admin_creates_a_moderator_who_can_sign_in(
        self, client, api_prefix, db, stage
    ):
        response = client.post(
            f"{api_prefix}/admin/users",
            json={
                "phone": "0655000009",
                "full_name": "Salma Bennani",
                "password": "khedma2026",
                "role": "moderator",
            },
            headers=auth(stage["token"]),
        )

        assert response.status_code == 201
        assert response.json()["role"] == "moderator"
        assert audited(db, "staff.created") is not None

        token = token_for(client, api_prefix, "0655000009")
        assert client.get(f"{api_prefix}/mod/disputes", headers=auth(token)).status_code == 200

    def test_a_client_account_is_not_created_from_here(self, client, api_prefix, stage):
        """People arrive at a client account themselves."""
        response = client.post(
            f"{api_prefix}/admin/users",
            json={
                "phone": "0655000009",
                "full_name": "Salma Bennani",
                "password": "khedma2026",
                "role": "client",
            },
            headers=auth(stage["token"]),
        )
        assert response.status_code == 409
        assert response.json()["code"] == "role_not_assignable"

    def test_a_phone_already_in_use_is_refused(self, client, api_prefix, stage):
        response = client.post(
            f"{api_prefix}/admin/users",
            json={
                "phone": "0611111111",
                "full_name": "Salma Bennani",
                "password": "khedma2026",
                "role": "admin",
            },
            headers=auth(stage["token"]),
        )
        assert response.status_code == 409
        assert response.json()["code"] == "phone_taken"


# -- who may be here at all -------------------------------------------------


def test_the_screen_is_the_admins_alone(client, api_prefix, stage):
    """A moderator handles disputes and never touches an account's role."""
    for phone in ("0655000001", "0611111111"):
        token = auth(token_for(client, api_prefix, phone))
        assert client.get(f"{api_prefix}/admin/users", headers=token).status_code == 403

    assert client.get(f"{api_prefix}/admin/users").status_code == 401
