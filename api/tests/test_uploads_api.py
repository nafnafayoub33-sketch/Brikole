"""Uploading a photo, and who may read one back.

The identity document is the part that matters: everything else on a profile is
meant to be seen, and that one is not.
"""

from __future__ import annotations

import pytest

from app.core.enums import Role
from app.services.storage import MAX_BYTES
from tests.test_auth_api import auth, make_user, token_for

# Real first bytes. A file is what it starts with, not what it is called.
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
WEBP = b"RIFF" + b"0000" + b"WEBP" + b"0" * 64
NOT_AN_IMAGE = b"<?php system($_GET['c']); ?>"


def upload(client, api_prefix, token, *, purpose: str, data: bytes, name="photo.jpg"):
    return client.post(
        f"{api_prefix}/uploads",
        headers=auth(token),
        data={"purpose": purpose},
        files={"file": (name, data, "image/jpeg")},
    )


@pytest.fixture
def provider_token(client, api_prefix, db):
    make_user(db, phone="+212700000001", role=Role.PROVIDER)
    return token_for(client, api_prefix, "0700000001")


@pytest.mark.parametrize("data", [JPEG, PNG, WEBP])
def test_a_real_image_is_accepted_and_readable(client, api_prefix, provider_token, data):
    response = upload(client, api_prefix, provider_token, purpose="portfolio", data=data)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["path"].startswith("public/portfolio/")
    assert body["url"] == f"{api_prefix}/uploads/{body['path']}"

    # Public means public: no token needed to read it back.
    assert client.get(body["url"]).status_code == 200


def test_a_script_renamed_to_jpg_is_still_a_script(client, api_prefix, provider_token):
    """The declared name and content type come from the client. The bytes do not."""
    response = upload(
        client, api_prefix, provider_token, purpose="portfolio", data=NOT_AN_IMAGE
    )
    assert response.status_code == 422
    assert response.json()["details"]["reason"] == "unsupported_image"


def test_an_empty_file_is_refused(client, api_prefix, provider_token):
    response = upload(client, api_prefix, provider_token, purpose="portfolio", data=b"")
    assert response.status_code == 422


def test_a_file_over_the_cap_is_refused(client, api_prefix, provider_token):
    oversized = JPEG + b"0" * MAX_BYTES
    response = upload(client, api_prefix, provider_token, purpose="portfolio", data=oversized)
    assert response.status_code == 422
    assert response.json()["details"]["reason"] == "file_too_large"


def test_uploading_needs_an_account(client, api_prefix):
    response = client.post(
        f"{api_prefix}/uploads",
        data={"purpose": "avatar"},
        files={"file": ("a.jpg", JPEG, "image/jpeg")},
    )
    assert response.status_code == 401


def test_anybody_may_upload_an_avatar_but_only_a_tradesman_an_id_card(
    client, api_prefix, db
):
    make_user(db, phone="+212611111111", role=Role.CLIENT)
    client_token = token_for(client, api_prefix, "0611111111")

    assert (
        upload(client, api_prefix, client_token, purpose="avatar", data=JPEG).status_code
        == 201
    )

    refused = upload(client, api_prefix, client_token, purpose="id_card", data=JPEG)
    assert refused.status_code == 403


# --- the private bucket -------------------------------------------------------


def test_an_id_card_gets_no_public_url(client, api_prefix, provider_token):
    body = upload(client, api_prefix, provider_token, purpose="id_card", data=JPEG).json()
    assert body["path"].startswith("private/id-cards/")
    assert body["url"] is None


def test_its_owner_can_read_it_back(client, api_prefix, provider_token):
    body = upload(client, api_prefix, provider_token, purpose="id_card", data=JPEG).json()
    response = client.get(f"{api_prefix}/uploads/{body['path']}", headers=auth(provider_token))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"


def test_another_tradesman_cannot(client, api_prefix, db, provider_token):
    body = upload(client, api_prefix, provider_token, purpose="id_card", data=JPEG).json()

    make_user(db, phone="+212700000002", role=Role.PROVIDER)
    other = token_for(client, api_prefix, "0700000002")

    response = client.get(f"{api_prefix}/uploads/{body['path']}", headers=auth(other))
    # Not 403: whether somebody's identity document exists is itself private.
    assert response.status_code == 404


def test_a_stranger_with_no_token_cannot(client, api_prefix, provider_token):
    body = upload(client, api_prefix, provider_token, purpose="id_card", data=JPEG).json()
    assert client.get(f"{api_prefix}/uploads/{body['path']}").status_code == 401


def test_an_admin_can_because_that_is_the_point_of_the_review(
    client, api_prefix, db, provider_token
):
    body = upload(client, api_prefix, provider_token, purpose="id_card", data=JPEG).json()

    make_user(db, phone="+212600000001", role=Role.ADMIN)
    admin = token_for(client, api_prefix, "0600000001")

    assert (
        client.get(f"{api_prefix}/uploads/{body['path']}", headers=auth(admin)).status_code
        == 200
    )


def test_a_traversal_in_the_path_does_not_escape_the_bucket(client, api_prefix, db):
    make_user(db, phone="+212600000001", role=Role.ADMIN)
    admin = token_for(client, api_prefix, "0600000001")

    response = client.get(
        f"{api_prefix}/uploads/private/../../../etc/passwd", headers=auth(admin)
    )
    assert response.status_code in (404, 422)
