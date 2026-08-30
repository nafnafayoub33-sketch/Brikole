"""A2 — an admin judging an application, and the trail it leaves.

Two things matter here beyond the happy path: nobody but an admin gets near it,
and two admins with the same queue open cannot both decide the same case.
"""

from __future__ import annotations

import pytest

from app.core.enums import ProviderStatus, Role
from app.models.system import AuditLog
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def pending(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    profile = make_provider(
        db,
        phone="+212700000001",
        city=casa,
        trades=[plumber],
        name="Youssef Berrada",
        status=ProviderStatus.PENDING,
    )
    profile.id_card_url = "private/id-cards/1/cin.jpg"
    profile.headline = "Plomberie et dépannage"
    profile.bio = "Douze ans d'expérience à Casablanca."

    make_user(db, phone="+212600000001", role=Role.ADMIN, )
    db.commit()

    return {"profile": profile, "token": token_for(client, api_prefix, "0600000001")}


def test_the_queue_shows_what_an_admin_needs_to_judge(client, api_prefix, pending):
    payload = client.get(
        f"{api_prefix}/admin/approvals", headers=auth(pending["token"])
    ).json()

    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["full_name"] == "Youssef Berrada"
    assert item["headline"] == "Plomberie et dépannage"
    assert item["city"]["slug"] == "casablanca"
    # The applicant's phone: an admin checking an identity has to reach them.
    assert item["phone"] == "+212700000001"
    assert item["id_card_path"] == "private/id-cards/1/cin.jpg"
    assert item["submitted_at"]


def test_the_queue_is_oldest_first_because_it_is_a_queue(client, api_prefix, db, pending):
    casa = make_city(db, "casablanca2")
    later = make_provider(
        db,
        phone="+212700000002",
        city=casa,
        trades=[make_trade(db, "peintre")],
        name="Later Applicant",
        status=ProviderStatus.PENDING,
    )
    later.id_card_url = "private/id-cards/2/cin.jpg"
    db.commit()

    items = client.get(
        f"{api_prefix}/admin/approvals", headers=auth(pending["token"])
    ).json()["items"]
    assert [item["full_name"] for item in items] == ["Youssef Berrada", "Later Applicant"]


def test_only_pending_applications_are_in_it(client, api_prefix, db, pending):
    pending["profile"].status = ProviderStatus.APPROVED
    db.commit()

    payload = client.get(
        f"{api_prefix}/admin/approvals", headers=auth(pending["token"])
    ).json()
    assert payload == {"items": [], "total": 0, "page": 1, "per_page": 20}


def test_approving_puts_him_in_the_public_grid(client, api_prefix, pending):
    assert client.get(f"{api_prefix}/providers").json()["total"] == 0

    response = client.post(
        f"{api_prefix}/admin/approvals/{pending['profile'].id}/approve",
        headers=auth(pending["token"]),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    assert client.get(f"{api_prefix}/providers").json()["total"] == 1


def test_approving_is_written_down(client, api_prefix, db, pending):
    client.post(
        f"{api_prefix}/admin/approvals/{pending['profile'].id}/approve",
        headers=auth(pending["token"]),
    )

    entry = db.query(AuditLog).one()
    assert entry.action == "provider.approved"
    assert entry.target_type == "provider_profile"
    assert entry.target_id == pending["profile"].id
    assert entry.before == {"status": "pending"}
    assert entry.after == {"status": "approved"}


def test_rejecting_keeps_him_out_and_tells_him_why(client, api_prefix, db, pending):
    response = client.post(
        f"{api_prefix}/admin/approvals/{pending['profile'].id}/reject",
        json={"reason": "  La photo de la CIN   est illisible  "},
        headers=auth(pending["token"]),
    )
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "rejected"
    # Normalised, because it is shown to somebody.
    assert body["rejection_reason"] == "La photo de la CIN est illisible"

    assert client.get(f"{api_prefix}/providers").json()["total"] == 0

    entry = db.query(AuditLog).one()
    assert entry.action == "provider.rejected"
    assert entry.note == "La photo de la CIN est illisible"


@pytest.mark.parametrize("reason", ["", "   "])
def test_a_rejection_with_no_reason_is_refused(client, api_prefix, pending, reason):
    """The reason is the only thing M2 can tell him to fix."""
    response = client.post(
        f"{api_prefix}/admin/approvals/{pending['profile'].id}/reject",
        json={"reason": reason},
        headers=auth(pending["token"]),
    )
    assert response.status_code == 422


def test_the_second_admin_is_told_rather_than_allowed_to_overwrite(
    client, api_prefix, pending
):
    """Two admins, one queue, one case. The first decision stands."""
    first = client.post(
        f"{api_prefix}/admin/approvals/{pending['profile'].id}/approve",
        headers=auth(pending["token"]),
    )
    assert first.status_code == 200

    second = client.post(
        f"{api_prefix}/admin/approvals/{pending['profile'].id}/reject",
        json={"reason": "Trop tard"},
        headers=auth(pending["token"]),
    )
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"
    assert second.json()["details"]["status"] == "approved"


def test_a_rejected_application_that_is_resubmitted_returns_to_the_queue(
    client, api_prefix, db, pending
):
    client.post(
        f"{api_prefix}/admin/approvals/{pending['profile'].id}/reject",
        json={"reason": "CIN illisible"},
        headers=auth(pending["token"]),
    )
    assert client.get(
        f"{api_prefix}/admin/approvals", headers=auth(pending["token"])
    ).json()["total"] == 0

    # M1 resubmission, as the service performs it.
    pending["profile"].status = ProviderStatus.PENDING
    pending["profile"].rejection_reason = None
    db.commit()

    assert client.get(
        f"{api_prefix}/admin/approvals", headers=auth(pending["token"])
    ).json()["total"] == 1


@pytest.mark.parametrize(
    ("role", "phone"),
    [
        (Role.CLIENT, "+212611111111"),
        (Role.PROVIDER, "+212722222222"),
        (Role.MODERATOR, "+212633333333"),
    ],
)
def test_nobody_but_an_admin_gets_near_the_queue(client, api_prefix, db, pending, role, phone):
    """A moderator included: approving a tradesman is not arbitration."""
    make_user(db, phone=phone, role=role)
    db.commit()
    token = token_for(client, api_prefix, phone)

    assert client.get(f"{api_prefix}/admin/approvals", headers=auth(token)).status_code == 403
    assert (
        client.post(
            f"{api_prefix}/admin/approvals/{pending['profile'].id}/approve",
            headers=auth(token),
        ).status_code
        == 403
    )


def test_signed_out_is_not_authenticated_rather_than_forbidden(client, api_prefix, pending):
    assert client.get(f"{api_prefix}/admin/approvals").status_code == 401


def test_an_application_that_does_not_exist_is_a_404(client, api_prefix, pending):
    response = client.get(
        f"{api_prefix}/admin/approvals/999999", headers=auth(pending["token"])
    )
    assert response.status_code == 404
