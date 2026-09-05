"""What an admin may put in the trades and the cities.

Framework-free, so the shape of a slug can be argued about without a database.
"""

from __future__ import annotations

import pytest

from app.core.catalog_rules import validate_city, validate_slug, validate_trade
from app.core.money import dirhams


def trade(**overrides):
    fields = {
        "slug": "plombier",
        "name_ar": "سباك",
        "name_fr": "Plombier",
        "name_en": "Plumber",
        "icon": "wrench",
        "lead_fee_centimes": None,
        "sort_order": 10,
    }
    fields.update(overrides)
    return validate_trade(**fields)


def city(**overrides):
    fields = {
        "slug": "casablanca",
        "name_ar": "الدار البيضاء",
        "name_fr": "Casablanca",
        "name_en": "Casablanca",
        "latitude": 33.5731,
        "longitude": -7.5898,
    }
    fields.update(overrides)
    return validate_city(**fields)


class TestTheSlug:
    @pytest.mark.parametrize(
        "raw,expected",
        [("plombier", "plombier"), ("PLOMBIER", "plombier"), ("  peintre  ", "peintre")],
    )
    def test_it_is_lowercased_and_trimmed(self, raw, expected):
        assert validate_slug(raw) == expected

    @pytest.mark.parametrize("slug", ["lave-auto", "a1", "mobile-car-wash"])
    def test_hyphens_and_digits_are_fine(self, slug):
        assert validate_slug(slug) == slug

    def test_trailing_space_is_trimmed_rather_than_refused(self):
        """Somebody pasted it. Refusing over whitespace teaches nothing."""
        assert validate_slug("plombier ") == "plombier"

    @pytest.mark.parametrize(
        "slug",
        [
            "",
            "   ",
            "plombier 2",  # a space inside; a trailing one is trimmed and fine
            "plombier_2",
            "-plombier",
            "plombier-",
            "plombier--2",
            "plombier/2",
            "سباك",
            "a" * 65,
        ],
    )
    def test_anything_that_would_look_wrong_in_a_url_is_refused(self, slug):
        """It goes in `/services/:slug`, so it stays boring on purpose."""
        with pytest.raises(ValueError):
            validate_slug(slug)


class TestATrade:
    def test_a_good_one_comes_back_cleaned(self):
        result = trade(name_fr="  Plombier   chauffagiste ")
        assert result.name_fr == "Plombier chauffagiste"
        assert result.slug == "plombier"

    @pytest.mark.parametrize("field", ["name_ar", "name_fr", "name_en"])
    def test_every_language_is_mandatory(self, field):
        """A trade with no Arabic name renders as a blank row to this
        product's default audience."""
        with pytest.raises(ValueError, match=field):
            trade(**{field: "   "})

    def test_a_null_fee_means_the_platform_default(self):
        """Not "free" — the difference is the whole business model."""
        assert trade(lead_fee_centimes=None).lead_fee_centimes is None

    @pytest.mark.parametrize("fee", [0, -1, dirhams(501)])
    def test_a_fee_outside_the_bounds_is_refused(self, fee):
        with pytest.raises(ValueError, match="lead_fee_centimes"):
            trade(lead_fee_centimes=fee)

    def test_true_is_not_a_fee(self):
        """`bool` is an `int` in Python, and `True` would store as 1 centime."""
        with pytest.raises(ValueError, match="lead_fee_centimes"):
            trade(lead_fee_centimes=True)

    @pytest.mark.parametrize("order", [-1, 10_000])
    def test_the_sort_order_is_bounded(self, order):
        with pytest.raises(ValueError, match="sort_order"):
            trade(sort_order=order)

    def test_an_icon_is_mandatory(self):
        with pytest.raises(ValueError, match="icon"):
            trade(icon="  ")


class TestACity:
    def test_a_good_one_comes_back_cleaned(self):
        assert city().name_ar == "الدار البيضاء"

    @pytest.mark.parametrize("latitude", [-90.1, 90.1])
    def test_an_impossible_latitude_is_refused(self, latitude):
        with pytest.raises(ValueError, match="latitude"):
            city(latitude=latitude)

    @pytest.mark.parametrize("longitude", [-180.1, 180.1])
    def test_an_impossible_longitude_is_refused(self, longitude):
        with pytest.raises(ValueError, match="longitude"):
            city(longitude=longitude)

    def test_a_city_outside_morocco_is_allowed(self):
        """Bounding this to Morocco is a rule somebody has to find and remove
        the day the product crosses a border."""
        assert city(slug="paris", latitude=48.8566, longitude=2.3522).latitude == 48.8566

    @pytest.mark.parametrize("field", ["name_ar", "name_fr", "name_en"])
    def test_every_language_is_mandatory_here_too(self, field):
        with pytest.raises(ValueError, match=field):
            city(**{field: ""})
