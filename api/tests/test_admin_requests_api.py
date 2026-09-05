"""A4 — the support browser, and the one thing it can change.

Every test here is written from the same situation: somebody is on the phone
about a request, and an admin has to find it and say what happened to it.
"""

from __future__ import annotations

import pytest

from app.core.enums import RequestStatus, Role
from app.core.money import dirhams
from app.models.request import ServiceRequest
from app.models.system import AuditLog
from tests.test_auth_api import auth, make_user, token_for
from tests.test_offers_api import stage  # noqa: F401 — the fixture is the point


@pytest.fixture
def support(client, api_prefix, db, stage):  # noqa: F811
    """An admin, and a moderator who must not get in."""
    make_user(db, phone="+212600000001", role=Role.ADMIN)
    make_user(db, phone="+212655000001", role=Role.MODERATOR)
    db.commit()

    return {
        **stage,
        "admin": auth(token_for(client, api_prefix, "0600000001")),
        "mod": auth(token_for(client, api_prefix, "0655000001")),
    }


def browse(client, api_prefix, support, **params):
    return client.get(
        f"{api_prefix}/admin/requests", params=params, headers=support["admin"]
    )


def detail(client, api_prefix, support, request_id, headers=None):
    return client.get(
        f"{api_prefix}/admin/requests/{request_id}",
        headers=headers or support["admin"],
    )


def cancel(client, api_prefix, support, request_id, reason="Doublon signalé par le client"):
    return client.post(
        f"{api_prefix}/admin/requests/{request_id}/cancel",
        json={"reason": reason},
        headers=support["admin"],
    )


def ids(payload):
    return [item["id"] for item in payload["items"]]


def hire(client, api_prefix, support):
    """Put a tradesman on the request the way the product actually does it:
    an offer, a conversation opened on it, and both signatures."""
    offer = client.post(
        f"{api_prefix}/pro/requests/{support['mine']['id']}/offer",
        json={"price_centimes": dirhams(400), "message": "Je passe demain."},
        headers=auth(support["token"]),
    ).json()

    conversation = client.post(
        f"{api_prefix}/offers/{offer['id']}/conversation",
        headers=auth(support["client_token"]),
    ).json()

    for headers in (auth(support["client_token"]), auth(support["token"])):
        client.post(
            f"{api_prefix}/conversations/{conversation['id']}/agree",
            json={"version": conversation["version"]},
            headers=headers,
        )
    return offer


class TestWhoMayLook:
    def test_a_moderator_is_refused(self, client, api_prefix, support):
        """He resolves disputes and sees nothing about money. Every offer on
        this screen carries a price."""
        response = client.get(f"{api_prefix}/admin/requests", headers=support["mod"])
        assert response.status_code == 403

    def test_a_client_is_refused(self, client, api_prefix, support):
        response = client.get(
            f"{api_prefix}/admin/requests", headers=auth(support["client_token"])
        )
        assert response.status_code == 403

    def test_a_visitor_is_refused(self, client, api_prefix):
        assert client.get(f"{api_prefix}/admin/requests").status_code == 401


class TestFindingIt:
    def test_every_request_is_here_newest_first(self, client, api_prefix, support):
        """Not one client's requests — all of them. That is the difference
        between this screen and C2."""
        payload = browse(client, api_prefix, support).json()
        assert payload["total"] == 3
        assert ids(payload)[0] == support["other_city"]["id"]

    def test_the_client_rides_on_the_row(self, client, api_prefix, support):
        """Support is reading this while somebody talks. A name that needs a
        second request is a name he reads out late."""
        row = browse(client, api_prefix, support).json()["items"][0]
        assert row["client"]["full_name"]
        assert row["client"]["phone"].startswith("+212")

    def test_a_bare_number_finds_the_request_by_id(self, client, api_prefix, support):
        wanted = support["mine"]["id"]
        assert ids(browse(client, api_prefix, support, q=str(wanted)).json()) == [wanted]

    def test_a_national_phone_finds_the_client_who_typed_it(
        self, client, api_prefix, support
    ):
        """He is stored `+212611111111` and says "zero six one one…"."""
        payload = browse(client, api_prefix, support, q="0611111111").json()
        assert payload["total"] == 3

    def test_a_title_finds_it_too(self, client, api_prefix, support):
        payload = browse(client, api_prefix, support, q="Chauffe-eau").json()
        assert ids(payload) == [support["other_city"]["id"]]

    def test_an_underscore_is_not_a_wildcard(self, client, api_prefix, support):
        assert browse(client, api_prefix, support, q="_").json()["total"] == 0

    def test_a_number_too_long_to_be_an_id_finds_nothing_rather_than_failing(
        self, client, api_prefix, support
    ):
        """MySQL raises on a BIGINT it cannot hold; the box takes whatever
        somebody pastes into it."""
        response = browse(client, api_prefix, support, q="9" * 40)
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.parametrize("filters,expected", [
        ({"status": "open"}, 3),
        ({"status": "cancelled"}, 0),
    ])
    def test_it_filters_by_status(self, client, api_prefix, support, filters, expected):
        assert browse(client, api_prefix, support, **filters).json()["total"] == expected

    def test_it_filters_by_city_and_trade(self, client, api_prefix, support):
        casa = browse(client, api_prefix, support, city_id=support["casa"].id).json()
        assert casa["total"] == 2

        plumbing = browse(
            client, api_prefix, support, trade_id=support["plombier"].id
        ).json()
        assert plumbing["total"] == 2

    def test_an_empty_filter_is_an_empty_page_not_an_error(
        self, client, api_prefix, support
    ):
        response = browse(client, api_prefix, support, q="rien du tout")
        assert response.status_code == 200
        assert response.json()["items"] == []


class TestTheWholeStory:
    def test_it_carries_the_request_and_who_posted_it(self, client, api_prefix, support):
        body = detail(client, api_prefix, support, support["mine"]["id"]).json()

        assert body["title"] == "Fuite sous l'évier"
        assert body["address"] == "12 rue Al Massira"
        assert body["client"]["phone"] == "+212611111111"
        assert body["trade"]["slug"] == "plombier"
        assert body["city"]["slug"] == "casablanca"

    def test_a_request_nobody_answered_says_so_rather_than_omitting_it(
        self, client, api_prefix, support
    ):
        """Empty lists and nulls, not missing keys: the screen renders "no
        offers yet", which is an answer support can read out."""
        body = detail(client, api_prefix, support, support["mine"]["id"]).json()

        assert body["offers"] == []
        assert body["job"] is None
        assert body["dispute"] is None

    def test_the_offers_and_the_job_come_with_it(self, client, api_prefix, db, support):
        hire(client, api_prefix, support)

        body = detail(client, api_prefix, support, support["mine"]["id"]).json()

        assert len(body["offers"]) == 1
        assert body["offers"][0]["price_centimes"] == dirhams(400)
        assert body["offers"][0]["provider"]["full_name"] == "Karim Zeroual"
        # Frozen when it was accepted, so a later price change never rewrites
        # what this lead actually cost.
        assert body["offers"][0]["lead_fee_centimes"] == dirhams(5)

        assert body["job"] is not None
        assert body["job"]["agreed_price_centimes"] == dirhams(400)
        assert body["job"]["provider"]["phone"] == "+212700000001"

    def test_a_request_that_does_not_exist_is_a_404(self, client, api_prefix, support):
        assert detail(client, api_prefix, support, 999_999).status_code == 404


class TestCancelling:
    def test_it_closes_the_request_and_keeps_the_reason(
        self, client, api_prefix, db, support
    ):
        body = cancel(client, api_prefix, support, support["mine"]["id"]).json()

        assert body["status"] == "cancelled"
        assert body["cancel_reason"] == "Doublon signalé par le client"
        assert body["cancelled_at"] is not None
        assert body["can_cancel"] is False

    def test_it_is_on_the_record(self, client, api_prefix, db, support):
        cancel(client, api_prefix, support, support["mine"]["id"])

        row = db.query(AuditLog).filter_by(action="request.cancelled").one()
        assert row.target_id == support["mine"]["id"]
        assert row.before == {"status": "open"}
        assert row.after["reason"] == "Doublon signalé par le client"

    def test_a_reason_is_mandatory(self, client, api_prefix, db, support):
        """Somebody reads this in three months and needs to know why a client's
        request vanished. "Cancelled by an admin" is not a why."""
        response = cancel(client, api_prefix, support, support["mine"]["id"], reason="   ")

        assert response.status_code == 422
        assert db.get(ServiceRequest, support["mine"]["id"]).status is RequestStatus.OPEN

    def test_an_assigned_request_is_refused(self, client, api_prefix, support):
        """There is a tradesman who may be on his way, a fee already charged,
        and possibly a refund owed. That is a dispute, not a cancel button."""
        hire(client, api_prefix, support)

        assert detail(client, api_prefix, support, support["mine"]["id"]).json()[
            "can_cancel"
        ] is False
        response = cancel(client, api_prefix, support, support["mine"]["id"])
        assert response.status_code == 409

    def test_cancelling_twice_is_refused(self, client, api_prefix, support):
        cancel(client, api_prefix, support, support["mine"]["id"])
        assert cancel(client, api_prefix, support, support["mine"]["id"]).status_code == 409

    def test_a_moderator_cannot(self, client, api_prefix, db, support):
        response = client.post(
            f"{api_prefix}/admin/requests/{support['mine']['id']}/cancel",
            json={"reason": "parce que"},
            headers=support["mod"],
        )
        assert response.status_code == 403
        assert db.query(AuditLog).filter_by(action="request.cancelled").count() == 0

    def test_the_client_still_sees_it_as_cancelled(self, client, api_prefix, support):
        """The screen is not a private ledger: what an admin does here is what
        the client reads on C2."""
        cancel(client, api_prefix, support, support["mine"]["id"])

        body = client.get(
            f"{api_prefix}/client/requests/{support['mine']['id']}",
            headers=auth(support["client_token"]),
        ).json()
        assert body["status"] == "cancelled"


def test_a_role_the_route_never_heard_of_is_still_refused(client, api_prefix, support):
    """Belt and braces: the guard is a role list, not an absence of one."""
    assert Role.PROVIDER not in {Role.ADMIN}
    response = client.get(f"{api_prefix}/admin/requests", headers=auth(support["token"]))
    assert response.status_code == 403
