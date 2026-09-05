"""S4 — A7's maintenance switch, and what it actually closes.

The switch existed from the day A7 was built: validated, stored, audited, and
read by nothing. These tests are the difference between a row in a table and a
platform that is closed.
"""

from __future__ import annotations

import pytest

from app.core.enums import Role
from app.core.maintenance import OPEN_PATHS, is_closed
from app.core.policy import SettingKey
from app.models.system import PlatformSetting
from tests.test_auth_api import auth, make_user, token_for
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


@pytest.fixture
def stage(client, api_prefix, db):
    city = make_city(db, "casablanca")
    trade = make_trade(db, "plombier")
    make_provider(db, phone="+212700000001", city=city, trades=[trade])
    make_user(db, phone="+212611111111", role=Role.CLIENT)
    make_user(db, phone="+212655000001", role=Role.MODERATOR)
    make_user(db, phone="+212600000001", role=Role.ADMIN)
    db.commit()

    return {
        "client": auth(token_for(client, api_prefix, "0611111111")),
        "moderator": auth(token_for(client, api_prefix, "0655000001")),
        "admin": auth(token_for(client, api_prefix, "0600000001")),
    }


def close_the_platform(db, *, on: bool = True) -> None:
    row = db.get(PlatformSetting, SettingKey.MAINTENANCE_MODE)
    if row is None:
        db.add(PlatformSetting(key=SettingKey.MAINTENANCE_MODE, value=on))
    else:
        row.value = on
    db.commit()


# -- the rule, without a database -------------------------------------------


class TestTheRule:
    def test_the_switch_off_closes_nothing(self) -> None:
        assert not is_closed(maintenance_on=False, role=None, path="/providers")

    def test_a_visitor_is_turned_away(self) -> None:
        """"We are down" beats a list of tradesmen who cannot be contacted."""
        assert is_closed(maintenance_on=True, role=None, path="/providers")

    @pytest.mark.parametrize("role", [Role.CLIENT, Role.PROVIDER, Role.MODERATOR])
    def test_everybody_else_is_too(self, role: Role) -> None:
        assert is_closed(maintenance_on=True, role=role, path="/providers")

    def test_an_admin_is_not(self) -> None:
        assert not is_closed(maintenance_on=True, role=Role.ADMIN, path="/providers")

    @pytest.mark.parametrize("path", OPEN_PATHS)
    def test_the_open_paths_stay_open(self, path: str) -> None:
        assert not is_closed(maintenance_on=True, role=None, path=path)

    def test_a_path_that_merely_starts_the_same_is_still_closed(self) -> None:
        """`/authorise` is not `/auth/login`."""
        assert is_closed(maintenance_on=True, role=None, path="/account")


# -- and through the app ----------------------------------------------------


class TestWithTheSwitchOn:
    def test_a_visitor_reads_503_and_a_code(self, client, api_prefix, db, stage):
        close_the_platform(db)

        response = client.get(f"{api_prefix}/providers")
        assert response.status_code == 503
        assert response.json()["code"] == "maintenance"

    def test_a_client_is_closed_out_too(self, client, api_prefix, db, stage):
        close_the_platform(db)

        response = client.get(f"{api_prefix}/auth/me", headers=stage["client"])
        assert response.status_code == 503

    def test_a_moderator_is_not_special(self, client, api_prefix, db, stage):
        """The spec says admins. A moderator handles disputes; he does not
        decide whether the platform is open."""
        close_the_platform(db)

        response = client.get(f"{api_prefix}/mod/disputes", headers=stage["moderator"])
        assert response.status_code == 503

    def test_an_admin_still_gets_in(self, client, api_prefix, db, stage):
        close_the_platform(db)

        assert (
            client.get(f"{api_prefix}/auth/me", headers=stage["admin"]).status_code == 200
        )
        assert (
            client.get(f"{api_prefix}/admin/settings", headers=stage["admin"]).status_code
            == 200
        )

    def test_an_admin_can_sign_in_while_it_is_on(self, client, api_prefix, db, stage):
        """Otherwise the platform locks its own keys inside: the switch is on,
        and the only person who can turn it off cannot get a token."""
        close_the_platform(db)

        response = client.post(
            f"{api_prefix}/auth/login",
            json={"phone": "0600000001", "password": "khedma2026"},
        )
        assert response.status_code == 200

    def test_and_so_can_anybody_else(self, client, api_prefix, db, stage):
        """He gets a session and then meets S4 on the next call, which is a
        truer answer than "wrong password"."""
        close_the_platform(db)

        assert (
            client.post(
                f"{api_prefix}/auth/login",
                json={"phone": "0611111111", "password": "khedma2026"},
            ).status_code
            == 200
        )

    def test_health_still_answers(self, client, api_prefix, db, stage):
        """A monitor must not go red because somebody flipped a switch."""
        close_the_platform(db)

        assert client.get(f"{api_prefix}/health").status_code == 200

    def test_turning_it_back_off_reopens_immediately(self, client, api_prefix, db, stage):
        """No cache, so no window where the switch has moved and the platform
        has not noticed."""
        close_the_platform(db)
        assert client.get(f"{api_prefix}/providers").status_code == 503

        close_the_platform(db, on=False)
        assert client.get(f"{api_prefix}/providers").status_code == 200

    def test_an_admin_can_flip_it_through_a7(self, client, api_prefix, db, stage):
        """The whole round trip: the switch A7 writes is the switch the gate
        reads. It was not, until now."""
        response = client.patch(
            f"{api_prefix}/admin/settings",
            json={"values": {SettingKey.MAINTENANCE_MODE: True}},
            headers=stage["admin"],
        )
        assert response.status_code == 200

        assert client.get(f"{api_prefix}/providers").status_code == 503

    def test_the_platform_is_open_by_default(self, client, api_prefix, stage):
        assert client.get(f"{api_prefix}/providers").status_code == 200
