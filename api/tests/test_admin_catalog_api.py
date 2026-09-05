"""A6 — the two lists everything else points at.

The rule the whole screen is shaped by: **nothing here is ever deleted.** A
trade with jobs behind it cannot vanish without taking the history, so
deactivation is the only removal, and these tests exist mostly to hold that
line.
"""

from __future__ import annotations

import pytest

from app.core.enums import Role
from app.core.money import dirhams
from app.models.catalog import City, Trade
from app.models.system import AuditLog
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade


@pytest.fixture
def stage(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plombier = make_trade(db, "plombier")
    make_user(db, phone="+212600000001", role=Role.ADMIN)
    make_user(db, phone="+212655000001", role=Role.MODERATOR)
    db.commit()

    return {
        "casa": casa,
        "plombier": plombier,
        "admin": auth(token_for(client, api_prefix, "0600000001")),
        "mod": auth(token_for(client, api_prefix, "0655000001")),
    }


def read(client, api_prefix, stage):
    return client.get(f"{api_prefix}/admin/catalog", headers=stage["admin"])


def new_trade(client, api_prefix, stage, **overrides):
    body = {
        "slug": "peintre",
        "name_ar": "صباغ",
        "name_fr": "Peintre",
        "name_en": "Painter",
        "icon": "brush",
        "sort_order": 20,
    }
    body.update(overrides)
    return client.post(f"{api_prefix}/admin/catalog/trades", json=body, headers=stage["admin"])


def new_city(client, api_prefix, stage, **overrides):
    body = {
        "slug": "rabat",
        "name_ar": "الرباط",
        "name_fr": "Rabat",
        "name_en": "Rabat",
        "latitude": 34.0209,
        "longitude": -6.8416,
    }
    body.update(overrides)
    return client.post(f"{api_prefix}/admin/catalog/cities", json=body, headers=stage["admin"])


def trade_named(payload, slug):
    return next(row for row in payload["trades"] if row["slug"] == slug)


def city_named(payload, slug):
    return next(row for row in payload["cities"] if row["slug"] == slug)


class TestWhoMayEdit:
    def test_a_moderator_is_refused(self, client, api_prefix, stage):
        assert client.get(f"{api_prefix}/admin/catalog", headers=stage["mod"]).status_code == 403

    def test_a_visitor_is_refused(self, client, api_prefix):
        assert client.get(f"{api_prefix}/admin/catalog").status_code == 401


class TestReading:
    def test_it_returns_both_lists_at_once(self, client, api_prefix, stage):
        """Neither is big enough to be worth two requests, and the screen shows
        them side by side."""
        body = read(client, api_prefix, stage).json()
        assert [row["slug"] for row in body["trades"]] == ["plombier"]
        assert [row["slug"] for row in body["cities"]] == ["casablanca"]

    def test_an_inactive_trade_is_still_here(self, client, api_prefix, db, stage):
        """This is the screen that turns it back on. The public list hides it;
        this one cannot."""
        stage["plombier"].is_active = False
        db.commit()

        assert [row["slug"] for row in read(client, api_prefix, stage).json()["trades"]] == [
            "plombier"
        ]
        assert client.get(f"{api_prefix}/trades").json() == []

    def test_a_fresh_row_carries_zeroes_not_nulls(self, client, api_prefix, stage):
        usage = trade_named(read(client, api_prefix, stage).json(), "plombier")["usage"]
        assert usage == {"providers": 0, "requests": 0, "jobs": 0}


class TestCreating:
    def test_a_new_trade_arrives_active(self, client, api_prefix, stage):
        response = new_trade(client, api_prefix, stage)
        assert response.status_code == 201

        created = trade_named(response.json(), "peintre")
        assert created["name_ar"] == "صباغ"
        assert created["is_active"] is True
        assert created["lead_fee_centimes"] is None

    def test_a_duplicate_slug_is_refused(self, client, api_prefix, stage):
        response = new_trade(client, api_prefix, stage, slug="plombier")
        assert response.status_code == 409
        assert response.json()["details"]["field"] == "slug"

    def test_the_slug_is_normalised_before_it_is_stored(self, client, api_prefix, stage):
        body = new_trade(client, api_prefix, stage, slug="  LAVE-AUTO ").json()
        assert trade_named(body, "lave-auto")["slug"] == "lave-auto"

    @pytest.mark.parametrize(
        "field,value",
        [("name_ar", "   "), ("slug", "pas valide"), ("icon", " ")],
    )
    def test_a_bad_field_is_named(self, client, api_prefix, db, stage, field, value):
        response = new_trade(client, api_prefix, stage, **{field: value})
        assert response.status_code == 422
        assert db.query(Trade).count() == 1

    def test_a_fee_above_the_bound_is_refused(self, client, api_prefix, stage):
        response = new_trade(client, api_prefix, stage, lead_fee_centimes=dirhams(501))
        assert response.status_code == 422

    def test_a_new_city_arrives_active(self, client, api_prefix, stage):
        body = new_city(client, api_prefix, stage).json()
        created = city_named(body, "rabat")
        assert created["is_active"] is True
        assert created["latitude"] == pytest.approx(34.0209)

    def test_creating_is_on_the_record(self, client, api_prefix, db, stage):
        new_trade(client, api_prefix, stage)

        row = db.query(AuditLog).filter_by(action="trade.created").one()
        assert row.before is None
        assert row.after["slug"] == "peintre"


class TestEditing:
    def test_the_three_names_and_the_fee_move(self, client, api_prefix, stage):
        body = client.patch(
            f"{api_prefix}/admin/catalog/trades/{stage['plombier'].id}",
            json={
                "name_ar": "سباك ومسخن",
                "name_fr": "Plombier chauffagiste",
                "name_en": "Plumber and heating",
                "icon": "wrench",
                "lead_fee_centimes": dirhams(15),
                "sort_order": 5,
            },
            headers=stage["admin"],
        ).json()

        edited = trade_named(body, "plombier")
        assert edited["name_fr"] == "Plombier chauffagiste"
        assert edited["lead_fee_centimes"] == dirhams(15)
        assert edited["sort_order"] == 5

    def test_the_slug_never_moves(self, client, api_prefix, db, stage):
        """It is in `/services/:slug` and in every link anybody has shared.
        Editing it turns all of them into a silent 404, so the endpoint does
        not take one at all."""
        client.patch(
            f"{api_prefix}/admin/catalog/trades/{stage['plombier'].id}",
            json={
                "slug": "something-else",
                "name_ar": "سباك",
                "name_fr": "Plombier",
                "name_en": "Plumber",
                "icon": "wrench",
                "sort_order": 10,
            },
            headers=stage["admin"],
        )

        db.expire_all()
        assert db.get(Trade, stage["plombier"].id).slug == "plombier"

    def test_only_what_moved_is_logged(self, client, api_prefix, db, stage):
        """A log with an entry per save, listing eight unchanged fields, cannot
        answer "when did this fee change"."""
        trade = stage["plombier"]
        client.patch(
            f"{api_prefix}/admin/catalog/trades/{trade.id}",
            json={
                # Everything else is exactly what it already was, so the only
                # thing this save moved is the fee.
                "name_ar": trade.name_ar,
                "name_fr": trade.name_fr,
                "name_en": trade.name_en,
                "icon": trade.icon,
                "lead_fee_centimes": dirhams(15),
                "sort_order": trade.sort_order,
            },
            headers=stage["admin"],
        )

        row = db.query(AuditLog).filter_by(action="trade.updated").one()
        assert row.after == {"lead_fee_centimes": dirhams(15)}
        assert row.before == {"lead_fee_centimes": None}

    def test_saving_the_same_values_writes_nothing(self, client, api_prefix, db, stage):
        client.patch(
            f"{api_prefix}/admin/catalog/trades/{stage['plombier'].id}",
            json={
                "name_ar": stage["plombier"].name_ar,
                "name_fr": stage["plombier"].name_fr,
                "name_en": stage["plombier"].name_en,
                "icon": stage["plombier"].icon,
                "sort_order": stage["plombier"].sort_order,
            },
            headers=stage["admin"],
        )
        assert db.query(AuditLog).count() == 0

    def test_a_city_moves_on_the_map(self, client, api_prefix, stage):
        body = client.patch(
            f"{api_prefix}/admin/catalog/cities/{stage['casa'].id}",
            json={
                "name_ar": "الدار البيضاء",
                "name_fr": "Casablanca",
                "name_en": "Casablanca",
                "latitude": 33.6,
                "longitude": -7.6,
            },
            headers=stage["admin"],
        ).json()
        assert city_named(body, "casablanca")["latitude"] == pytest.approx(33.6)

    def test_editing_something_that_is_not_there_is_a_404(self, client, api_prefix, stage):
        response = client.patch(
            f"{api_prefix}/admin/catalog/trades/999999",
            json={
                "name_ar": "س",
                "name_fr": "P",
                "name_en": "P",
                "icon": "wrench",
                "sort_order": 10,
            },
            headers=stage["admin"],
        )
        assert response.status_code == 404


class TestDeactivating:
    """The only removal this product has."""

    def test_there_is_no_delete_at_all(self, client, api_prefix, stage):
        """Not a 404 on a missing route — a 405, because the path exists and
        the verb does not."""
        response = client.delete(
            f"{api_prefix}/admin/catalog/trades/{stage['plombier'].id}",
            headers=stage["admin"],
        )
        assert response.status_code in {404, 405}

    def test_it_hides_the_trade_from_everyone_else(self, client, api_prefix, stage):
        client.patch(
            f"{api_prefix}/admin/catalog/trades/{stage['plombier'].id}/active",
            json={"is_active": False},
            headers=stage["admin"],
        )

        assert client.get(f"{api_prefix}/trades").json() == []
        assert trade_named(read(client, api_prefix, stage).json(), "plombier")[
            "is_active"
        ] is False

    def test_the_row_and_its_history_stay(self, client, api_prefix, db, stage):
        client.patch(
            f"{api_prefix}/admin/catalog/cities/{stage['casa'].id}/active",
            json={"is_active": False},
            headers=stage["admin"],
        )

        db.expire_all()
        assert db.get(City, stage["casa"].id) is not None
        assert db.get(City, stage["casa"].id).slug == "casablanca"

    def test_it_can_be_turned_back_on(self, client, api_prefix, stage):
        for active in (False, True):
            body = client.patch(
                f"{api_prefix}/admin/catalog/trades/{stage['plombier'].id}/active",
                json={"is_active": active},
                headers=stage["admin"],
            ).json()
        assert trade_named(body, "plombier")["is_active"] is True

    def test_it_is_on_the_record(self, client, api_prefix, db, stage):
        client.patch(
            f"{api_prefix}/admin/catalog/trades/{stage['plombier'].id}/active",
            json={"is_active": False},
            headers=stage["admin"],
        )

        row = db.query(AuditLog).filter_by(action="trade.updated").one()
        assert row.before == {"is_active": True}
        assert row.after == {"is_active": False}

    def test_a_moderator_cannot(self, client, api_prefix, db, stage):
        response = client.patch(
            f"{api_prefix}/admin/catalog/trades/{stage['plombier'].id}/active",
            json={"is_active": False},
            headers=stage["mod"],
        )
        assert response.status_code == 403
        assert db.query(AuditLog).count() == 0
