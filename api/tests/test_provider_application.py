"""The rules a tradesman's application has to satisfy, checked without a database."""

import pytest

from app.core.errors import DomainError, ErrorCode
from app.core.provider_application import (
    MAX_BIO,
    MAX_TRADES,
    MIN_BIO,
    validate_application,
)

VALID = {
    "trade_ids": [1],
    "city_id": 2,
    "radius_km": 15,
    "headline": "  Plomberie   et dépannage  ",
    "bio": "Quinze ans d'expérience, je travaille à Casablanca.",
    "years_experience": 15,
    "starting_price_centimes": 15_000,
    "avatar_path": "public/avatars/1/a.jpg",
    "id_card_path": "private/id-cards/1/b.jpg",
    "photo_paths": ["public/portfolio/1/c.jpg"],
}


def application(**overrides):
    return validate_application(**{**VALID, **overrides})


def field_of(error: DomainError) -> str:
    return str(error.details["field"])


def test_a_complete_application_is_normalised():
    result = application()
    assert result.headline == "Plomberie et dépannage"  # collapsed whitespace
    assert result.trade_ids == (1,)
    assert result.photo_paths == ("public/portfolio/1/c.jpg",)


def test_the_identity_document_is_what_makes_it_judgeable():
    """Everything else can be corrected later; without this there is nothing
    for an admin to decide on."""
    with pytest.raises(DomainError) as exc:
        application(id_card_path=None)
    assert exc.value.code is ErrorCode.VALIDATION_FAILED
    assert field_of(exc.value) == "id_card_path"


def test_at_least_one_trade_and_no_more_than_five():
    with pytest.raises(DomainError) as exc:
        application(trade_ids=[])
    assert field_of(exc.value) == "trade_ids"

    with pytest.raises(DomainError):
        application(trade_ids=list(range(1, MAX_TRADES + 2)))


def test_a_trade_listed_twice_counts_once():
    assert application(trade_ids=[3, 3, 4]).trade_ids == (3, 4)


def test_a_photo_listed_twice_counts_once():
    assert application(photo_paths=["a.jpg", "a.jpg"]).photo_paths == ("a.jpg",)


@pytest.mark.parametrize("radius", [0, -5, 101])
def test_the_radius_has_to_be_a_distance_somebody_could_travel(radius):
    with pytest.raises(DomainError) as exc:
        application(radius_km=radius)
    assert field_of(exc.value) == "radius_km"


@pytest.mark.parametrize("headline", ["", "   ", "x" * 200])
def test_the_headline_is_required_and_bounded(headline):
    with pytest.raises(DomainError) as exc:
        application(headline=headline)
    assert field_of(exc.value) == "headline"


def test_the_bio_has_a_floor_and_a_ceiling():
    with pytest.raises(DomainError) as exc:
        application(bio="x" * (MIN_BIO - 1))
    assert field_of(exc.value) == "bio"

    with pytest.raises(DomainError):
        application(bio="x" * (MAX_BIO + 1))


def test_experience_cannot_exceed_a_working_life():
    with pytest.raises(DomainError) as exc:
        application(years_experience=99)
    assert field_of(exc.value) == "years_experience"


def test_no_starting_price_is_allowed_but_a_free_one_is_not():
    assert application(starting_price_centimes=None).starting_price_centimes is None

    with pytest.raises(DomainError) as exc:
        application(starting_price_centimes=0)
    assert field_of(exc.value) == "starting_price_centimes"


def test_an_avatar_is_optional():
    assert application(avatar_path=None).avatar_path is None
    assert application(avatar_path="").avatar_path is None
