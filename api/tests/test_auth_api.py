"""Registration, sign-in, and proof that the role gate is real.

These run against MySQL through the app, so a unique constraint or an enum
CHECK failing counts as a test failure rather than passing quietly.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.core.enums import Role, UserStatus
from app.core.security import MAX_FAILED_ATTEMPTS, hash_password
from app.models.user import User


def register(client, api_prefix, **overrides):
    body = {
        "phone": "0612345678",
        "full_name": "Youssef Alami",
        "password": "khedma2026",
        "role": "client",
    }
    body.update(overrides)
    return client.post(f"{api_prefix}/auth/register", json=body)


def make_user(db: Session, *, phone: str, role: Role, password: str = "khedma2026") -> User:
    user = User(
        phone=phone,
        password_hash=hash_password(password),
        full_name=f"{role.value} user",
        role=role,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def token_for(client, api_prefix, phone: str, password: str = "khedma2026") -> str:
    response = client.post(
        f"{api_prefix}/auth/login", json={"phone": phone, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- registration ------------------------------------------------------------


def test_a_client_can_register_and_is_signed_in(client, api_prefix):
    response = register(client, api_prefix)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["token"]["access_token"]
    assert body["user"]["phone"] == "+212612345678"  # normalised on the way in
    assert body["user"]["role"] == "client"
    assert body["user"]["home_path"] == "/client/requests"
    assert "request.post" in body["user"]["permissions"]
    assert body["user"]["provider"] is None


def test_a_tradesman_registers_without_a_profile_so_he_lands_on_onboarding(client, api_prefix):
    response = register(client, api_prefix, role="provider", phone="0700000001")
    assert response.status_code == 201
    user = response.json()["user"]
    assert user["role"] == "provider"
    assert user["home_path"] == "/pro"
    assert user["provider"] is None


@pytest.mark.parametrize("role", ["admin", "moderator"])
def test_staff_roles_cannot_be_self_registered(client, api_prefix, role):
    response = register(client, api_prefix, role=role, phone="0611111111")
    assert response.status_code == 403
    assert response.json()["code"] == "role_not_self_registerable"


def test_the_same_number_typed_differently_is_still_taken(client, api_prefix):
    assert register(client, api_prefix, phone="0612345678").status_code == 201
    response = register(client, api_prefix, phone="+212 612-345-678")
    assert response.status_code == 409
    assert response.json()["code"] == "phone_taken"


def test_a_weak_password_is_refused_before_anything_is_written(client, api_prefix, db):
    response = register(client, api_prefix, password="short")
    assert response.status_code == 422
    assert db.query(User).count() == 0


def test_a_number_that_is_not_moroccan_is_refused(client, api_prefix):
    response = register(client, api_prefix, phone="+33612345678")
    assert response.status_code == 422
    assert response.json()["code"] in {"phone_invalid", "validation_failed"}


def test_an_unknown_role_does_not_reach_the_service(client, api_prefix):
    response = register(client, api_prefix, role="superuser")
    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


# --- sign-in -----------------------------------------------------------------


def test_login_and_me(client, api_prefix, db):
    make_user(db, phone="+212612345678", role=Role.CLIENT)
    token = token_for(client, api_prefix, "0612345678")

    response = client.get(f"{api_prefix}/auth/me", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["phone"] == "+212612345678"


def test_a_wrong_password_says_nothing_useful(client, api_prefix, db):
    make_user(db, phone="+212612345678", role=Role.CLIENT)
    response = client.post(
        f"{api_prefix}/auth/login", json={"phone": "0612345678", "password": "wrong-one1"}
    )
    assert response.status_code == 401
    assert response.json() == {"code": "invalid_credentials"}


def test_an_unknown_number_looks_exactly_like_a_wrong_password(client, api_prefix):
    response = client.post(
        f"{api_prefix}/auth/login", json={"phone": "0612345678", "password": "khedma2026"}
    )
    assert response.status_code == 401
    assert response.json() == {"code": "invalid_credentials"}


def test_repeated_failures_lock_the_account(client, api_prefix, db):
    make_user(db, phone="+212612345678", role=Role.CLIENT)

    for _ in range(MAX_FAILED_ATTEMPTS):
        failed = client.post(
            f"{api_prefix}/auth/login", json={"phone": "0612345678", "password": "wrong-one1"}
        )
        assert failed.status_code == 401

    # Even the right password is refused now, and the client is told for how long.
    locked = client.post(
        f"{api_prefix}/auth/login", json={"phone": "0612345678", "password": "khedma2026"}
    )
    assert locked.status_code == 423
    body = locked.json()
    assert body["code"] == "account_locked"
    assert 0 < body["details"]["retry_after_seconds"] <= 15 * 60


def test_a_suspended_account_is_told_why(client, api_prefix, db):
    user = make_user(db, phone="+212612345678", role=Role.CLIENT)
    user.status = UserStatus.SUSPENDED
    user.suspension_reason = "dispute:no_show"
    db.commit()

    response = client.post(
        f"{api_prefix}/auth/login", json={"phone": "0612345678", "password": "khedma2026"}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "account_suspended"
    assert response.json()["details"]["reason"] == "dispute:no_show"


# --- tokens ------------------------------------------------------------------


def test_me_needs_a_token(client, api_prefix):
    assert client.get(f"{api_prefix}/auth/me").status_code == 401


def test_a_rubbish_token_is_rejected(client, api_prefix):
    response = client.get(f"{api_prefix}/auth/me", headers=auth("not-a-token"))
    assert response.status_code == 401
    assert response.json()["code"] == "token_invalid"


def test_the_refresh_cookie_mints_a_new_access_token(client, api_prefix, db):
    make_user(db, phone="+212612345678", role=Role.CLIENT)
    token_for(client, api_prefix, "0612345678")  # sets the cookie on the client

    response = client.post(f"{api_prefix}/auth/refresh")
    assert response.status_code == 200
    new_token = response.json()["access_token"]

    assert client.get(f"{api_prefix}/auth/me", headers=auth(new_token)).status_code == 200


def test_logout_clears_the_cookie(client, api_prefix, db):
    make_user(db, phone="+212612345678", role=Role.CLIENT)
    token_for(client, api_prefix, "0612345678")

    assert client.post(f"{api_prefix}/auth/logout").status_code == 204
    assert client.post(f"{api_prefix}/auth/refresh").status_code == 401


def test_an_access_token_is_not_accepted_as_a_refresh_token(client, api_prefix, db):
    make_user(db, phone="+212612345678", role=Role.CLIENT)
    access = token_for(client, api_prefix, "0612345678")

    client.cookies.set("brikole_refresh", access)
    response = client.post(f"{api_prefix}/auth/refresh")
    assert response.status_code == 401
    assert response.json()["code"] == "token_wrong_type"


# --- the role gate -----------------------------------------------------------


def test_an_admin_sees_the_overview(client, api_prefix, db):
    make_user(db, phone="+212600000001", role=Role.ADMIN)
    token = token_for(client, api_prefix, "0600000001")

    response = client.get(f"{api_prefix}/admin/overview", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["admins"] == 1


@pytest.mark.parametrize(
    ("role", "phone"),
    [(Role.CLIENT, "+212611111111"), (Role.PROVIDER, "+212622222222")],
)
def test_ordinary_users_are_refused_the_overview(client, api_prefix, db, role, phone):
    make_user(db, phone=phone, role=role)
    token = token_for(client, api_prefix, phone)

    response = client.get(f"{api_prefix}/admin/overview", headers=auth(token))
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_a_moderator_holding_a_valid_token_is_still_refused_the_money_screen(
    client, api_prefix, db
):
    """The separation that justifies the role existing at all."""
    make_user(db, phone="+212633333333", role=Role.MODERATOR)
    token = token_for(client, api_prefix, "0633333333")

    response = client.get(f"{api_prefix}/admin/overview", headers=auth(token))
    assert response.status_code == 403
    assert response.json()["details"]["permission"] == "stats.read"


def test_the_role_is_re_read_from_the_database_not_trusted_from_the_token(
    client, api_prefix, db
):
    """An admin who demotes someone must not have to wait for a token to expire."""
    user = make_user(db, phone="+212600000001", role=Role.ADMIN)
    token = token_for(client, api_prefix, "0600000001")
    assert client.get(f"{api_prefix}/admin/overview", headers=auth(token)).status_code == 200

    user.role = Role.CLIENT
    db.commit()

    assert client.get(f"{api_prefix}/admin/overview", headers=auth(token)).status_code == 403


# --- public endpoints --------------------------------------------------------


def test_health_needs_no_account(client, api_prefix):
    assert client.get(f"{api_prefix}/health").json()["status"] == "ok"


def test_trades_and_cities_are_public(client, api_prefix):
    assert client.get(f"{api_prefix}/trades").status_code == 200
    assert client.get(f"{api_prefix}/cities").status_code == 200
