"""The trade grid, and the counts a visitor decides on.

A count that ignores the city is worse than no count: it tells somebody in
Meknès that forty plumbers are available when every one of them is in
Casablanca.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import ProviderStatus, Role
from app.core.security import hash_password
from app.models.catalog import City, Trade
from app.models.provider import ProviderProfile
from app.models.user import User


def make_city(db: Session, slug: str) -> City:
    city = City(
        slug=slug, name_ar=slug, name_fr=slug, name_en=slug, latitude=33.5, longitude=-7.5
    )
    db.add(city)
    db.flush()
    return city


def make_trade(db: Session, slug: str) -> Trade:
    trade = Trade(slug=slug, name_ar=slug, name_fr=slug, name_en=slug, icon="tool")
    db.add(trade)
    db.flush()
    return trade


def make_provider(
    db: Session,
    *,
    phone: str,
    city: City,
    trades: list[Trade],
    status: ProviderStatus = ProviderStatus.APPROVED,
) -> ProviderProfile:
    user = User(
        phone=phone,
        password_hash=hash_password("khedma2026"),
        full_name="Tradesman",
        role=Role.PROVIDER,
    )
    db.add(user)
    db.flush()

    profile = ProviderProfile(user_id=user.id, city_id=city.id, status=status)
    profile.trades = trades
    db.add(profile)
    db.flush()
    return profile


def trades_by_slug(payload: list[dict[str, object]]) -> dict[str, int]:
    return {str(row["slug"]): int(row["providers_count"]) for row in payload}  # type: ignore[call-overload]


def test_a_trade_with_nobody_behind_it_still_appears_with_zero(client, api_prefix, db):
    make_trade(db, "plombier")
    db.commit()

    response = client.get(f"{api_prefix}/trades")
    assert response.status_code == 200
    assert trades_by_slug(response.json()) == {"plombier": 0}


def test_counts_only_approved_tradesmen(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")

    make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    make_provider(
        db,
        phone="+212700000002",
        city=casa,
        trades=[plumber],
        status=ProviderStatus.PENDING,
    )
    make_provider(
        db,
        phone="+212700000003",
        city=casa,
        trades=[plumber],
        status=ProviderStatus.SUSPENDED,
    )
    db.commit()

    assert trades_by_slug(client.get(f"{api_prefix}/trades").json()) == {"plombier": 1}


def test_the_city_filter_is_what_makes_the_count_honest(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    meknes = make_city(db, "meknes")
    plumber = make_trade(db, "plombier")

    make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    make_provider(db, phone="+212700000002", city=casa, trades=[plumber])
    make_provider(db, phone="+212700000003", city=meknes, trades=[plumber])
    db.commit()

    everywhere = trades_by_slug(client.get(f"{api_prefix}/trades").json())
    assert everywhere == {"plombier": 3}

    in_meknes = trades_by_slug(
        client.get(f"{api_prefix}/trades", params={"city_id": meknes.id}).json()
    )
    assert in_meknes == {"plombier": 1}

    in_casa = trades_by_slug(
        client.get(f"{api_prefix}/trades", params={"city_id": casa.id}).json()
    )
    assert in_casa == {"plombier": 2}


def test_one_tradesman_working_two_trades_counts_in_both_but_once_each(
    client, api_prefix, db
):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    painter = make_trade(db, "peintre")

    make_provider(db, phone="+212700000001", city=casa, trades=[plumber, painter])
    db.commit()

    assert trades_by_slug(client.get(f"{api_prefix}/trades").json()) == {
        "plombier": 1,
        "peintre": 1,
    }


def test_an_inactive_trade_leaves_the_grid(client, api_prefix, db):
    trade = make_trade(db, "plombier")
    trade.is_active = False
    db.commit()

    assert client.get(f"{api_prefix}/trades").json() == []


def test_a_city_nobody_works_in_reports_zero_rather_than_hiding_the_trade(
    client, api_prefix, db
):
    casa = make_city(db, "casablanca")
    empty = make_city(db, "ouarzazate")
    plumber = make_trade(db, "plombier")
    make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    db.commit()

    payload = client.get(f"{api_prefix}/trades", params={"city_id": empty.id}).json()
    assert trades_by_slug(payload) == {"plombier": 0}
