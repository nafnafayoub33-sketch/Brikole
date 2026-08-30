"""What a request must say before somebody can price it, checked without a database."""

import pytest

from app.core.enums import Urgency
from app.core.errors import DomainError, ErrorCode
from app.core.money import dirhams
from app.core.service_request import (
    MAX_TITLE,
    MIN_DESCRIPTION,
    validate_request,
)

VALID = {
    "trade_id": 1,
    "city_id": 2,
    "title": "  Fuite   sous l'évier  ",
    "description": "L'eau coule dès que j'ouvre le robinet, depuis hier soir.",
    "address": "  12 rue Al Massira, Maârif  ",
    "latitude": 33.57,
    "longitude": -7.59,
    "urgency": Urgency.TODAY,
    "budget_min_centimes": dirhams(100),
    "budget_max_centimes": dirhams(400),
    "photo_paths": ["public/requests/1/a.jpg"],
}


def request(**overrides):
    return validate_request(**{**VALID, **overrides})


def field_of(error: DomainError) -> str:
    return str(error.details["field"])


def test_a_complete_request_is_normalised():
    result = request()
    assert result.title == "Fuite sous l'évier"
    assert result.address == "12 rue Al Massira, Maârif"
    assert result.urgency is Urgency.TODAY


@pytest.mark.parametrize("title", ["", "   ", "abc", "x" * (MAX_TITLE + 1)])
def test_the_title_is_required_and_bounded(title):
    with pytest.raises(DomainError) as exc:
        request(title=title)
    assert exc.value.code is ErrorCode.VALIDATION_FAILED
    assert field_of(exc.value) == "title"


def test_a_description_too_short_to_quote_on_is_refused():
    """"Fuite" is not a request. What, where, since when — that is."""
    with pytest.raises(DomainError) as exc:
        request(description="x" * (MIN_DESCRIPTION - 1))
    assert field_of(exc.value) == "description"


def test_the_address_is_required():
    with pytest.raises(DomainError) as exc:
        request(address="  ")
    assert field_of(exc.value) == "address"


@pytest.mark.parametrize(("lat", "lng"), [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_coordinates_off_the_planet_are_refused(lat, lng):
    with pytest.raises(DomainError):
        request(latitude=lat, longitude=lng)


def test_a_pin_is_optional():
    assert request(latitude=None, longitude=None).latitude is None


def test_a_budget_is_optional():
    result = request(budget_min_centimes=None, budget_max_centimes=None)
    assert result.budget_min_centimes is None


def test_a_budget_that_reads_high_to_low_is_a_typo():
    with pytest.raises(DomainError) as exc:
        request(budget_min_centimes=dirhams(400), budget_max_centimes=dirhams(100))
    assert field_of(exc.value) == "budget_max_centimes"


def test_the_two_ends_may_be_equal():
    assert request(
        budget_min_centimes=dirhams(200), budget_max_centimes=dirhams(200)
    ).budget_max_centimes == dirhams(200)


def test_a_free_budget_is_not_a_budget():
    with pytest.raises(DomainError) as exc:
        request(budget_min_centimes=0)
    assert field_of(exc.value) == "budget_min_centimes"


def test_the_same_photo_twice_counts_once():
    assert request(photo_paths=["a.jpg", "a.jpg", "b.jpg"]).photo_paths == ("a.jpg", "b.jpg")


def test_more_than_six_photos_is_refused():
    with pytest.raises(DomainError) as exc:
        request(photo_paths=[f"{index}.jpg" for index in range(7)])
    assert field_of(exc.value) == "photo_paths"
