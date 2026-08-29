"""P3: the profile, and the reviews behind its stars.

The rating shown on a card is a cache. What makes it trustworthy is that the
reviews it was computed from can be opened and read, so these tests care most
about the two staying in step.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.enums import JobStatus, OfferStatus, RequestStatus, Role, Urgency
from app.core.money import dirhams
from app.core.security import hash_password
from app.models.base import utcnow
from app.models.catalog import City, Trade
from app.models.job import Job, Review
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User
from tests.test_catalog_api import make_city, make_trade
from tests.test_providers_api import make_provider


def make_client(db: Session, *, phone: str, name: str = "Fatima Zahra Alami") -> User:
    user = User(
        phone=phone,
        password_hash=hash_password("khedma2026"),
        full_name=name,
        role=Role.CLIENT,
    )
    db.add(user)
    db.flush()
    return user


def leave_review(
    db: Session,
    *,
    provider: ProviderProfile,
    client: User,
    city: City,
    trade: Trade,
    rating: int,
    comment: str = "Travail propre.",
    days_ago: int = 1,
    hidden: bool = False,
    reply: str | None = None,
) -> Review:
    when = utcnow() - timedelta(days=days_ago)

    request = ServiceRequest(
        client_id=client.id,
        trade_id=trade.id,
        city_id=city.id,
        title="Une fuite",
        description="",
        address="—",
        urgency=Urgency.FLEXIBLE,
        status=RequestStatus.DONE,
    )
    db.add(request)
    db.flush()

    offer = Offer(
        request_id=request.id,
        provider_id=provider.id,
        price_centimes=dirhams(300),
        status=OfferStatus.ACCEPTED,
    )
    db.add(offer)
    db.flush()

    job = Job(
        request_id=request.id,
        offer_id=offer.id,
        client_id=client.id,
        provider_id=provider.id,
        agreed_price_centimes=dirhams(300),
        status=JobStatus.CONFIRMED,
    )
    db.add(job)
    db.flush()

    review = Review(
        job_id=job.id,
        author_id=client.id,
        provider_id=provider.id,
        rating=rating,
        comment=comment,
        created_at=when,
        is_hidden=hidden,
        reply=reply,
    )
    db.add(review)
    db.flush()
    return review


def test_the_profile_carries_what_the_grid_has_no_room_for(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    provider = make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    provider.bio = "15 ans d'expérience."
    provider.radius_km = 25
    db.commit()

    payload = client.get(f"{api_prefix}/providers/{provider.id}").json()
    assert payload["bio"] == "15 ans d'expérience."
    assert payload["radius_km"] == 25
    assert payload["member_since"]
    assert payload["photos"] == []


def test_the_breakdown_always_has_all_five_bars(client, api_prefix, db):
    """A chart missing its empty bars reads as a chart of different categories."""
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    provider = make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    author = make_client(db, phone="+212760000001")

    leave_review(db, provider=provider, client=author, city=casa, trade=plumber, rating=5)
    leave_review(db, provider=provider, client=author, city=casa, trade=plumber, rating=5)
    leave_review(db, provider=provider, client=author, city=casa, trade=plumber, rating=3)
    db.commit()

    payload = client.get(f"{api_prefix}/providers/{provider.id}").json()
    assert payload["rating_breakdown"] == {"1": 0, "2": 0, "3": 1, "4": 0, "5": 2}


def test_reviews_come_back_newest_first(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    provider = make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    author = make_client(db, phone="+212760000001")

    leave_review(
        db, provider=provider, client=author, city=casa, trade=plumber, rating=5,
        comment="Le plus ancien", days_ago=30,
    )
    leave_review(
        db, provider=provider, client=author, city=casa, trade=plumber, rating=4,
        comment="Le plus récent", days_ago=1,
    )
    db.commit()

    items = client.get(f"{api_prefix}/providers/{provider.id}/reviews").json()["items"]
    assert [item["comment"] for item in items] == ["Le plus récent", "Le plus ancien"]


def test_a_hidden_review_is_in_no_list_and_no_bar(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    provider = make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    author = make_client(db, phone="+212760000001")

    leave_review(db, provider=provider, client=author, city=casa, trade=plumber, rating=5)
    leave_review(
        db, provider=provider, client=author, city=casa, trade=plumber, rating=1, hidden=True
    )
    db.commit()

    reviews = client.get(f"{api_prefix}/providers/{provider.id}/reviews").json()
    assert reviews["total"] == 1

    profile = client.get(f"{api_prefix}/providers/{provider.id}").json()
    assert profile["rating_breakdown"]["1"] == 0


def test_a_reviewer_is_a_first_name_and_an_initial(client, api_prefix, db):
    """The review is public. The reviewer's full name does not have to be."""
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    provider = make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    author = make_client(db, phone="+212760000001", name="Fatima Zahra Alami")

    leave_review(db, provider=provider, client=author, city=casa, trade=plumber, rating=5)
    db.commit()

    item = client.get(f"{api_prefix}/providers/{provider.id}/reviews").json()["items"][0]
    assert item["author"]["display_name"] == "Fatima A."
    assert item["author"]["city"]["slug"] == "casablanca"
    assert item["trade"]["slug"] == "plombier"


def test_a_single_word_name_is_left_alone(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    provider = make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    author = make_client(db, phone="+212760000001", name="Hamid")

    leave_review(db, provider=provider, client=author, city=casa, trade=plumber, rating=5)
    db.commit()

    item = client.get(f"{api_prefix}/providers/{provider.id}/reviews").json()["items"][0]
    assert item["author"]["display_name"] == "Hamid"


def test_the_tradesmans_reply_travels_with_the_review(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    provider = make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    author = make_client(db, phone="+212760000001")

    leave_review(
        db, provider=provider, client=author, city=casa, trade=plumber, rating=5,
        reply="Merci pour votre confiance !",
    )
    db.commit()

    item = client.get(f"{api_prefix}/providers/{provider.id}/reviews").json()["items"][0]
    assert item["reply"] == "Merci pour votre confiance !"


def test_reviews_paginate_without_overlap(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    provider = make_provider(db, phone="+212700000001", city=casa, trades=[plumber])
    author = make_client(db, phone="+212760000001")

    # Same instant on every one, so only the id tiebreak separates the pages.
    for index in range(5):
        leave_review(
            db, provider=provider, client=author, city=casa, trade=plumber, rating=5,
            comment=f"Avis {index}", days_ago=1,
        )
    db.commit()

    first = client.get(
        f"{api_prefix}/providers/{provider.id}/reviews", params={"page": 1, "per_page": 2}
    ).json()
    second = client.get(
        f"{api_prefix}/providers/{provider.id}/reviews", params={"page": 2, "per_page": 2}
    ).json()

    assert first["total"] == 5
    ids = {item["id"] for item in first["items"]}
    assert ids.isdisjoint({item["id"] for item in second["items"]})


def test_reviews_of_a_provider_that_is_not_visible_are_not_found(client, api_prefix, db):
    from app.core.enums import ProviderStatus

    casa = make_city(db, "casablanca")
    plumber = make_trade(db, "plombier")
    provider = make_provider(
        db,
        phone="+212700000001",
        city=casa,
        trades=[plumber],
        status=ProviderStatus.PENDING,
    )
    db.commit()

    response = client.get(f"{api_prefix}/providers/{provider.id}/reviews")
    assert response.status_code == 404


def test_a_provider_with_no_reviews_is_an_empty_page_not_an_error(client, api_prefix, db):
    casa = make_city(db, "casablanca")
    provider = make_provider(
        db, phone="+212700000001", city=casa, trades=[make_trade(db, "plombier")]
    )
    db.commit()

    payload = client.get(f"{api_prefix}/providers/{provider.id}/reviews").json()
    assert payload == {"items": [], "total": 0, "page": 1, "per_page": 10}
