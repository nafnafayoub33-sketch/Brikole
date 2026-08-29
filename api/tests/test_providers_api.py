"""The grid a client browses.

What matters here is who is *not* in it: an unapproved application and a
suspended account are not people you can hire, and both have to leave the grid
the moment their status changes rather than at the next deploy.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import ProviderStatus, Role, UserStatus
from app.core.money import dirhams
from app.core.security import hash_password
from app.models.catalog import City, Trade
from app.models.provider import ProviderProfile
from app.models.user import User
from tests.test_catalog_api import make_city, make_trade


def make_provider(
    db: Session,
    *,
    phone: str,
    city: City,
    trades: list[Trade],
    name: str = "Tradesman",
    status: ProviderStatus = ProviderStatus.APPROVED,
    user_status: UserStatus = UserStatus.ACTIVE,
    rating: float = 0.0,
    rating_count: int = 0,
    jobs_done: int = 0,
    price_dh: int | None = None,
    headline: str | None = None,
) -> ProviderProfile:
    user = User(
        phone=phone,
        password_hash=hash_password("khedma2026"),
        full_name=name,
        role=Role.PROVIDER,
        status=user_status,
    )
    db.add(user)
    db.flush()

    profile = ProviderProfile(
        user_id=user.id,
        city_id=city.id,
        status=status,
        rating_avg=rating,
        rating_count=rating_count,
        jobs_done=jobs_done,
        headline=headline,
        starting_price_centimes=None if price_dh is None else dirhams(price_dh),
    )
    profile.trades = trades
    db.add(profile)
    db.flush()
    return profile


def names(payload: dict[str, object]) -> list[str]:
    items = payload["items"]
    assert isinstance(items, list)
    return [str(item["full_name"]) for item in items]


def test_the_grid_carries_what_a_client_decides_with(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    make_provider(
        db,
        phone="+212700000001",
        city=casa,
        trades=[plumber],
        name="Rachid Alami",
        rating=4.8,
        rating_count=12,
        jobs_done=30,
        price_dh=150,
        headline="Plomberie et dépannage",
    )
    db.commit()

    payload = client.get(f"{api_prefix}/providers").json()
    assert payload["total"] == 1

    card = payload["items"][0]
    assert card["full_name"] == "Rachid Alami"
    assert card["headline"] == "Plomberie et dépannage"
    assert card["city"]["slug"] == "casablanca"
    assert [t["slug"] for t in card["trades"]] == ["plombier"]
    assert card["rating_avg"] == 4.8
    assert card["rating_count"] == 12
    assert card["jobs_done"] == 30
    assert card["starting_price_centimes"] == 15_000


def test_only_approved_tradesmen_on_live_accounts_are_listed(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")

    make_provider(db, phone="+212700000001", city=casa, trades=[plumber], name="Approved")
    make_provider(
        db,
        phone="+212700000002",
        city=casa,
        trades=[plumber],
        name="Pending",
        status=ProviderStatus.PENDING,
    )
    make_provider(
        db,
        phone="+212700000003",
        city=casa,
        trades=[plumber],
        name="Rejected",
        status=ProviderStatus.REJECTED,
    )
    make_provider(
        db,
        phone="+212700000004",
        city=casa,
        trades=[plumber],
        name="Suspended account",
        user_status=UserStatus.SUSPENDED,
    )
    db.commit()

    assert names(client.get(f"{api_prefix}/providers").json()) == ["Approved"]


def test_filtering_by_city_and_by_trade(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    meknes = make_city(db, "meknes")
    plumber = make_trade(db, "plombier")
    painter = make_trade(db, "peintre")

    make_provider(db, phone="+212700000001", city=casa, trades=[plumber], name="Casa plumber")
    make_provider(db, phone="+212700000002", city=meknes, trades=[plumber], name="Meknes plumber")
    make_provider(db, phone="+212700000003", city=casa, trades=[painter], name="Casa painter")
    db.commit()

    by_city = client.get(f"{api_prefix}/providers", params={"city_id": meknes.id}).json()
    assert names(by_city) == ["Meknes plumber"]

    by_trade = client.get(f"{api_prefix}/providers", params={"trade_id": painter.id}).json()
    assert names(by_trade) == ["Casa painter"]

    both = client.get(
        f"{api_prefix}/providers", params={"city_id": casa.id, "trade_id": plumber.id}
    ).json()
    assert names(both) == ["Casa plumber"]


def test_best_rated_first_by_default(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")

    make_provider(
        db, phone="+212700000001", city=casa, trades=[plumber], name="Good", rating=4.2,
        rating_count=40,
    )
    make_provider(
        db, phone="+212700000002", city=casa, trades=[plumber], name="Best", rating=4.9,
        rating_count=10,
    )
    make_provider(db, phone="+212700000003", city=casa, trades=[plumber], name="Unrated")
    db.commit()

    assert names(client.get(f"{api_prefix}/providers").json()) == ["Best", "Good", "Unrated"]


def test_sorting_by_price_puts_no_price_last_not_first(client, api_prefix, db):
    """"I would rather quote" must never sort as "free"."""
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")

    make_provider(
        db, phone="+212700000001", city=casa, trades=[plumber], name="Quote", price_dh=None
    )
    make_provider(db, phone="+212700000002", city=casa, trades=[plumber], name="Cheap", price_dh=90)
    make_provider(db, phone="+212700000003", city=casa, trades=[plumber], name="Dear", price_dh=400)
    db.commit()

    payload = client.get(f"{api_prefix}/providers", params={"sort": "price"}).json()
    assert names(payload) == ["Cheap", "Dear", "Quote"]


def test_pagination_never_repeats_a_row(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    # All identical on the sort key, so only the id tiebreak keeps pages apart.
    for index in range(5):
        make_provider(
            db,
            phone=f"+21270000000{index}",
            city=casa,
            trades=[plumber],
            name=f"Tradesman {index}",
            rating=5.0,
            rating_count=3,
        )
    db.commit()

    first = client.get(f"{api_prefix}/providers", params={"page": 1, "per_page": 2}).json()
    second = client.get(f"{api_prefix}/providers", params={"page": 2, "per_page": 2}).json()

    assert first["total"] == 5
    assert len(names(first)) == 2
    assert set(names(first)).isdisjoint(names(second))


def test_one_provider_can_be_read_on_its_own(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    profile = make_provider(
        db, phone="+212700000001", city=casa, trades=[plumber], name="Rachid Alami"
    )
    db.commit()

    response = client.get(f"{api_prefix}/providers/{profile.id}")
    assert response.status_code == 200
    assert response.json()["full_name"] == "Rachid Alami"


def test_a_pending_profile_is_not_found_rather_than_forbidden(client, api_prefix, db):
    """Confirming it exists would tell a stranger something about someone else."""
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    profile = make_provider(
        db,
        phone="+212700000001",
        city=casa,
        trades=[plumber],
        status=ProviderStatus.PENDING,
    )
    db.commit()

    response = client.get(f"{api_prefix}/providers/{profile.id}")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_browsing_needs_no_account(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    make_provider(db, phone="+212700000001", city=casa, trades=[make_trade(db, "plombier")])
    db.commit()

    # No Authorization header anywhere in this test.
    assert client.get(f"{api_prefix}/providers").status_code == 200
