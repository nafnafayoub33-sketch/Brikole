"""A9 — the roster, and what each person on it has handled.

The counts come out of the audit log rather than a column somebody remembers
to increment, so these tests do real staff work and then read it back.
"""

from __future__ import annotations

import pytest

from app.core.enums import ProviderStatus, Role
from app.core.money import dirhams
from app.models.credit import CreditAccount, TopupRequest
from app.models.provider import ProviderProfile
from app.models.user import User
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plombier = make_trade(db, "plombier")

    make_user(db, phone="+212600000001", role=Role.ADMIN)
    make_user(db, phone="+212600000002", role=Role.ADMIN)
    make_user(db, phone="+212655000001", role=Role.MODERATOR)
    make_user(db, phone="+212611111111", role=Role.CLIENT)

    applicant = make_provider(
        db,
        phone="+212700000001",
        city=casa,
        trades=[plombier],
        status=ProviderStatus.PENDING,
    )
    db.commit()

    return {
        "casa": casa,
        "applicant": applicant,
        "admin": auth(token_for(client, api_prefix, "0600000001")),
        "other_admin": auth(token_for(client, api_prefix, "0600000002")),
        "mod": auth(token_for(client, api_prefix, "0655000001")),
        "client": auth(token_for(client, api_prefix, "0611111111")),
    }


def roster(client, api_prefix, stage, headers=None):
    return client.get(
        f"{api_prefix}/admin/users/staff", headers=headers or stage["admin"]
    )


def member(payload, phone):
    return next(row for row in payload["members"] if row["phone"] == phone)


class TestWhoMayLook:
    def test_a_moderator_is_refused(self, client, api_prefix, stage):
        """He is on this list; he does not get to read it."""
        assert roster(client, api_prefix, stage, stage["mod"]).status_code == 403

    def test_a_client_is_refused(self, client, api_prefix, stage):
        assert roster(client, api_prefix, stage, stage["client"]).status_code == 403


class TestTheRoster:
    def test_it_is_the_staff_and_nobody_else(self, client, api_prefix, stage):
        phones = {row["phone"] for row in roster(client, api_prefix, stage).json()["members"]}

        assert phones == {"+212600000001", "+212600000002", "+212655000001"}

    def test_the_route_is_not_read_as_a_user_id(self, client, api_prefix, stage):
        """`/staff` sits beside `/{user_id}`, and FastAPI matches in order."""
        assert roster(client, api_prefix, stage).status_code == 200

    def test_a_suspended_member_is_still_listed(self, client, api_prefix, db, stage):
        """This is the screen that undoes a suspension, so it is the one list
        that cannot filter them out."""
        target = db.query(User).filter_by(phone="+212655000001").one()
        client.post(
            f"{api_prefix}/admin/users/{target.id}/suspend",
            json={"days": 7, "reason": "Ne répond plus"},
            headers=stage["admin"],
        )

        row = member(roster(client, api_prefix, stage).json(), "+212655000001")
        assert row["status"] == "suspended"
        assert row["suspension_reason"] == "Ne répond plus"
        assert row["suspended_until"] is not None

    def test_the_reader_knows_which_row_is_his(self, client, api_prefix, stage):
        """Refused before it is pressed rather than after: suspending yourself
        locks you out of the screen that would undo it."""
        payload = roster(client, api_prefix, stage).json()

        assert member(payload, "+212600000001")["is_me"] is True
        assert member(payload, "+212600000002")["is_me"] is False


class TestWhatTheyHaveHandled:
    def test_somebody_who_has_done_nothing_reads_as_zero(self, client, api_prefix, stage):
        work = member(roster(client, api_prefix, stage).json(), "+212655000001")["work"]

        assert work["total"] == 0
        assert work["disputes"] == 0
        assert work["approvals"] == 0

    def test_approving_a_tradesman_counts_as_an_approval(
        self, client, api_prefix, stage
    ):
        client.post(
            f"{api_prefix}/admin/approvals/{stage['applicant'].id}/approve",
            json={},
            headers=stage["admin"],
        )

        work = member(roster(client, api_prefix, stage).json(), "+212600000001")["work"]
        assert work["approvals"] == 1
        assert work["total"] == 1

    def test_money_and_accounts_are_told_apart(self, client, api_prefix, db, stage):
        account = CreditAccount(
            provider_id=stage["applicant"].id, balance_centimes=0, free_leads_left=0
        )
        db.add(account)
        topup = TopupRequest(
            provider_id=stage["applicant"].id,
            amount_centimes=dirhams(100),
            reference="VIR-1",
        )
        db.add(topup)
        db.commit()

        client.post(
            f"{api_prefix}/admin/topups/{topup.id}/approve", headers=stage["admin"]
        )
        target = db.query(User).filter_by(phone="+212655000001").one()
        client.post(
            f"{api_prefix}/admin/users/{target.id}/suspend",
            json={"days": 7, "reason": "Ne répond plus"},
            headers=stage["admin"],
        )

        work = member(roster(client, api_prefix, stage).json(), "+212600000001")["work"]
        assert work["money"] == 1
        assert work["accounts"] == 1
        assert work["total"] == 2

    def test_the_work_is_attributed_to_whoever_did_it(
        self, client, api_prefix, db, stage
    ):
        """Two admins, one action. The other one's row must stay at zero."""
        client.post(
            f"{api_prefix}/admin/approvals/{stage['applicant'].id}/approve",
            json={},
            headers=stage["other_admin"],
        )

        payload = roster(client, api_prefix, stage).json()
        assert member(payload, "+212600000002")["work"]["approvals"] == 1
        assert member(payload, "+212600000001")["work"]["total"] == 0

    def test_it_says_when_he_last_did_something(self, client, api_prefix, stage):
        """`last_login_at` does not answer this: signing in and doing nothing
        is the case worth telling apart."""
        before = member(roster(client, api_prefix, stage).json(), "+212600000001")
        assert before["last_action_at"] is None

        client.post(
            f"{api_prefix}/admin/approvals/{stage['applicant'].id}/approve",
            json={},
            headers=stage["admin"],
        )

        after = member(roster(client, api_prefix, stage).json(), "+212600000001")
        assert after["last_action_at"] is not None


class TestDeactivation:
    def test_an_admin_cannot_suspend_himself(self, client, api_prefix, db, stage):
        me = db.query(User).filter_by(phone="+212600000001").one()
        response = client.post(
            f"{api_prefix}/admin/users/{me.id}/suspend",
            json={"days": 7, "reason": "test"},
            headers=stage["admin"],
        )
        assert response.status_code == 409
        assert response.json()["code"] == "self_action_refused"

    def test_a_suspension_can_be_undone_from_here(self, client, api_prefix, db, stage):
        target = db.query(User).filter_by(phone="+212655000001").one()
        client.post(
            f"{api_prefix}/admin/users/{target.id}/suspend",
            json={"days": 7, "reason": "Ne répond plus"},
            headers=stage["admin"],
        )
        client.post(
            f"{api_prefix}/admin/users/{target.id}/reactivate", headers=stage["admin"]
        )

        assert member(roster(client, api_prefix, stage).json(), "+212655000001")[
            "status"
        ] == "active"

    def test_creating_a_moderator_puts_him_on_the_roster(
        self, client, api_prefix, stage
    ):
        client.post(
            f"{api_prefix}/admin/users",
            json={
                "phone": "0655000002",
                "full_name": "Nadia Moderator",
                "password": "khedma2026",
                "role": "moderator",
            },
            headers=stage["admin"],
        )

        row = member(roster(client, api_prefix, stage).json(), "+212655000002")
        assert row["role"] == "moderator"
        assert row["work"]["total"] == 0

    def test_a_tradesman_cannot_be_made_staff(self, client, api_prefix, stage):
        """A m3allem is an application with a CIN and a trade behind it (M1,
        A2). A role handed out here would be a provider with no profile,
        invisible to every screen that expects one.

        409 rather than 422: the request is well-formed and the admin is
        allowed to make staff — it is the world that says no."""
        response = client.post(
            f"{api_prefix}/admin/users",
            json={
                "phone": "0700000009",
                "full_name": "Karim",
                "password": "khedma2026",
                "role": "provider",
            },
            headers=stage["admin"],
        )
        assert response.status_code == 409
        assert response.json()["code"] == "role_not_assignable"


def test_a_provider_profile_is_not_on_the_staff_list(client, api_prefix, db, stage):
    assert db.query(ProviderProfile).count() == 1
    phones = {row["phone"] for row in roster(client, api_prefix, stage).json()["members"]}
    assert "+212700000001" not in phones
