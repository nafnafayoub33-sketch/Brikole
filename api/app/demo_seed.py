"""Fill a development database with plausible tradesmen.

    python -m app.demo_seed

Every count on the landing page is a real query, so an empty database makes the
design impossible to judge and the product impossible to demonstrate. This
creates approved tradesmen spread unevenly across trades and cities — because
that is how a marketplace actually looks, and a design that only works when
every number is healthy is a design that has not been tested.

Development only: it refuses to run when ENV=production, and every account it
makes shares one obvious password.
"""

from __future__ import annotations

import random
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.enums import ProviderStatus, Role
from app.core.money import dirhams
from app.core.policy import FREE_LEADS_NEW_PROVIDER
from app.core.security import hash_password
from app.db import session_scope
from app.models.catalog import City, Trade
from app.models.credit import CreditAccount
from app.models.provider import ProviderProfile
from app.models.user import User

DEMO_PASSWORD = "demo1234"
DEMO_PHONE_PREFIX = "+21277"  # a block real numbers never fall in

FIRST_NAMES = [
    "Youssef", "Rachid", "Hamid", "Abdelilah", "Mustapha", "Karim", "Said",
    "Brahim", "Hicham", "Anas", "Yassine", "Omar", "Khalid", "Noureddine",
    "Mehdi", "Tarik", "Jamal", "Aziz", "Reda", "Soufiane", "Fatima", "Khadija",
    "Nadia", "Samira", "Latifa",
]
LAST_NAMES = [
    "Alami", "Bennani", "Chraibi", "Idrissi", "Tazi", "Benjelloun", "Fassi",
    "Amrani", "Berrada", "Sqalli", "Kabbaj", "Lahlou", "Naciri", "Ouazzani",
    "Sekkat", "Bouhali", "Zeroual", "Mansouri", "Cherkaoui", "Belkadi",
]

#: Roughly how busy each city is. Casablanca carries a marketplace; Ouarzazate
#: does not, and the design has to survive both.
CITY_WEIGHT = {
    "casablanca": 26, "rabat": 15, "marrakech": 14, "tanger": 11, "fes": 10,
    "agadir": 9, "sale": 8, "meknes": 7, "kenitra": 6, "oujda": 5,
    "tetouan": 4, "mohammedia": 4, "el-jadida": 3, "safi": 3, "nador": 3,
    "beni-mellal": 3, "khouribga": 2, "essaouira": 2, "laayoune": 1,
    "ouarzazate": 1,
}

#: What a tradesman in each trade typically starts at, in dirhams: a call-out
#: or a floor price, not the job. The job itself is still quoted per request.
BASE_PRICE_DH = {
    "plombier": 150, "electricien": 150, "peintre": 300, "menuisier": 250,
    "lavage-auto": 80, "climatisation": 250, "macon": 280, "serrurier": 120,
    "carreleur": 220, "jardinier": 150, "menage": 120, "demenagement": 400,
    "vitrier": 200, "electromenager": 150, "soudeur": 200, "antenne": 150,
}

#: The one line that turns a row into a card worth clicking. Real tradesmen
#: write these themselves, in whichever language they think in — so the demo
#: mixes French and Arabic, which is also what the layout has to survive.
HEADLINES = {
    "plombier": [
        "Plomberie et dépannage, 7j/7",
        "Fuites, chauffe-eau, sanitaires",
        "سباكة وإصلاح التسربات بسرعة",
    ],
    "electricien": [
        "Installation et dépannage électrique",
        "Tableaux, prises, éclairage",
        "كهرباء المنازل والمحلات",
    ],
    "peintre": [
        "Peinture intérieure et façades",
        "Finitions soignées, devis gratuit",
        "صباغة وديكور بجودة عالية",
    ],
    "menuisier": [
        "Menuiserie bois sur mesure",
        "Portes, placards, cuisines",
        "نجارة الخشب حسب الطلب",
    ],
    "lavage-auto": [
        "Lavage auto à domicile",
        "Nettoyage intérieur et extérieur",
        "غسيل السيارات عندك فالدار",
    ],
    "climatisation": [
        "Installation et entretien de clim",
        "Pose, recharge de gaz, entretien",
        "تركيب وصيانة المكيفات",
    ],
    "macon": ["Maçonnerie et gros œuvre", "Murs, dalles, rénovation", "بناء وترميم"],
    "serrurier": [
        "Ouverture de porte 24h/24",
        "Serrures et blindage",
        "فتح الأبواب وإصلاح الأقفال",
    ],
    "carreleur": ["Pose de carrelage et faïence", "Sols, murs, salles de bain", "تبليط وزليج"],
    "jardinier": ["Entretien de jardins", "Taille, tonte, arrosage", "العناية بالحدائق"],
    "menage": [
        "Ménage et grand nettoyage",
        "Maisons, bureaux, après travaux",
        "تنظيف المنازل والمكاتب",
    ],
    "demenagement": ["Déménagement avec camion", "Emballage et transport", "نقل الأثاث بشاحنة"],
    "vitrier": ["Vitrerie et miroiterie", "Remplacement de vitres", "تركيب الزجاج والمرايا"],
    "electromenager": [
        "Réparation électroménager",
        "Lave-linge, frigo, four",
        "إصلاح الأجهزة المنزلية",
    ],
    "soudeur": ["Soudure fer et inox", "Portails, grilles, structures", "لحام الحديد والستانلس"],
    "antenne": ["Antennes et paraboles", "Installation et réglage", "تركيب وضبط الهوائيات"],
}

#: And how common each trade is. A welder is rarer than a plumber.
TRADE_WEIGHT = {
    "plombier": 10, "electricien": 9, "peintre": 8, "menuisier": 7,
    "menage": 7, "climatisation": 6, "lavage-auto": 6, "macon": 5,
    "carreleur": 5, "serrurier": 4, "electromenager": 4, "demenagement": 4,
    "jardinier": 3, "vitrier": 3, "antenne": 2, "soudeur": 2,
}


def seed_demo(db: Session, *, total: int, rng: random.Random) -> tuple[int, int]:
    cities = {c.slug: c for c in db.execute(select(City)).scalars()}
    trades = {t.slug: t for t in db.execute(select(Trade)).scalars()}

    if not cities or not trades:
        raise SystemExit("run `python -m app.seed` first — no trades or cities yet")

    city_pool = [cities[slug] for slug, weight in CITY_WEIGHT.items() if slug in cities
                 for _ in range(weight)]
    trade_pool = [trades[slug] for slug, weight in TRADE_WEIGHT.items() if slug in trades
                  for _ in range(weight)]

    existing = {
        phone
        for phone in db.execute(
            select(User.phone).where(User.phone.like(f"{DEMO_PHONE_PREFIX}%"))
        ).scalars()
    }

    password_hash = hash_password(DEMO_PASSWORD)
    created = 0

    for index in range(total):
        phone = f"{DEMO_PHONE_PREFIX}{index:07d}"
        if phone in existing:
            continue

        city = rng.choice(city_pool)
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"

        user = User(
            phone=phone,
            password_hash=password_hash,
            full_name=name,
            role=Role.PROVIDER,
            city_id=city.id,
            language="ar",
        )
        db.add(user)
        db.flush()

        jobs_done = rng.choice([0, 0, 2, 5, 9, 14, 23, 38, 57])
        rating_count = 0 if jobs_done == 0 else rng.randint(1, jobs_done)

        profile = ProviderProfile(
            user_id=user.id,
            city_id=city.id,
            radius_km=rng.choice([5, 10, 10, 15, 25, 40]),
            bio="",
            years_experience=rng.randint(1, 22),
            status=ProviderStatus.APPROVED,
            rating_avg=0.0 if rating_count == 0 else round(rng.uniform(3.6, 5.0), 1),
            rating_count=rating_count,
            jobs_done=jobs_done,
        )

        # Most work one trade; a few work two, which is why the counts across
        # the grid add up to more than the number of people.
        picked = {rng.choice(trade_pool)}
        if rng.random() < 0.22:
            picked.add(rng.choice(trade_pool))
        profile.trades = list(picked)

        main_trade = next(iter(picked))
        profile.headline = rng.choice(HEADLINES.get(main_trade.slug, ["Services à domicile"]))

        # Four in five say a starting price; the rest would rather quote, and
        # the card has to look right without one.
        if rng.random() < 0.8:
            base = BASE_PRICE_DH.get(main_trade.slug, 150)
            profile.starting_price_centimes = dirhams(
                int(base * rng.choice([0.7, 0.85, 1.0, 1.0, 1.2, 1.5]))
            )

        db.add(profile)
        db.flush()

        db.add(
            CreditAccount(
                provider_id=profile.id,
                balance_centimes=rng.choice([0, 0, 2000, 5000, 12000, 30000]),
                free_leads_left=rng.randint(0, FREE_LEADS_NEW_PROVIDER),
            )
        )
        created += 1

    backfilled = backfill(db, rng=rng)
    return created, backfilled


def backfill(db: Session, *, rng: random.Random) -> int:
    """Give demo tradesmen created before this column existed a headline."""
    stale = (
        db.execute(
            select(ProviderProfile)
            .join(User, User.id == ProviderProfile.user_id)
            .where(User.phone.like(f"{DEMO_PHONE_PREFIX}%"), ProviderProfile.headline.is_(None))
        )
        .scalars()
        .unique()
    )

    touched = 0
    for profile in stale:
        slug = profile.trades[0].slug if profile.trades else ""
        profile.headline = rng.choice(HEADLINES.get(slug, ["Services à domicile"]))
        if rng.random() < 0.8:
            base = BASE_PRICE_DH.get(slug, 150)
            profile.starting_price_centimes = dirhams(
                int(base * rng.choice([0.7, 0.85, 1.0, 1.0, 1.2, 1.5]))
            )
        touched += 1
    return touched


def main() -> int:
    settings = get_settings()
    if settings.is_production:
        print("refusing to run against a production database", file=sys.stderr)
        return 1

    rng = random.Random(20260829)  # deterministic: the same demo every time
    with session_scope() as db:
        created, backfilled = seed_demo(db, total=240, rng=rng)

    print(f"demo tradesmen created: {created}, headlines backfilled: {backfilled}")
    print(f"they all sign in with the password {DEMO_PASSWORD!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
