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
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.enums import (
    JobStatus,
    OfferStatus,
    ProviderStatus,
    RequestStatus,
    Role,
    Urgency,
)
from app.core.money import dirhams
from app.core.policy import FREE_LEADS_NEW_PROVIDER, REQUEST_EXPIRY_DAYS
from app.core.security import hash_password
from app.db import session_scope
from app.models.base import utcnow
from app.models.catalog import City, Trade
from app.models.credit import CreditAccount
from app.models.job import Job, Review
from app.models.offer import Offer
from app.models.provider import ProviderProfile, provider_trades
from app.models.request import RequestPhoto, ServiceRequest
from app.models.user import User

DEMO_PASSWORD = "demo1234"
DEMO_PHONE_PREFIX = "+21277"  # a block real numbers never fall in
DEMO_CLIENT_PREFIX = "+21276"
DEMO_PENDING_PREFIX = "+212755"

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


JOB_TITLES = {
    "plombier": ["Fuite sous l'évier", "Chauffe-eau en panne", "تبديل الروبيني"],
    "electricien": ["Tableau électrique à revoir", "Prises à ajouter", "الضو طافي فالصالون"],
    "peintre": ["Repeindre le salon", "Façade à rafraîchir", "صباغة بيت النعاس"],
    "menuisier": ["Placard sur mesure", "Porte à ajuster", "خزانة ديال الخشب"],
    "lavage-auto": ["Lavage complet à domicile", "Nettoyage des sièges", "غسيل الطوموبيل فالدار"],
    "climatisation": ["Pose d'un split", "Recharge de gaz", "تركيب مكيف"],
    "macon": ["Mur à monter", "Dalle de terrasse", "ترميم الحيط"],
    "serrurier": ["Porte claquée", "Serrure à changer", "تبديل القفل"],
    "carreleur": ["Carrelage salle de bain", "Sol du salon", "تبليط الحمام"],
    "jardinier": ["Taille des arbres", "Entretien du jardin", "تشذيب الشجر"],
    "menage": ["Grand nettoyage", "Ménage après travaux", "تنظيف الدار"],
    "demenagement": ["Déménagement 2 pièces", "Transport d'un canapé", "نقل الأثاث"],
    "vitrier": ["Vitre cassée", "Miroir à poser", "تبديل الزاج"],
    "electromenager": ["Lave-linge qui fuit", "Frigo qui ne refroidit plus", "إصلاح الثلاجة"],
    "soudeur": ["Portail à souder", "Grille de fenêtre", "لحام الباب"],
    "antenne": ["Parabole à régler", "Antenne à poser", "ضبط البارابول"],
}

#: What a request actually says. Short, specific, and in whichever language
#: the person thinks in — M7 shows these to the tradesman on his phone, and a
#: row of blanks there is what makes a seeded database look broken.
JOB_DESCRIPTIONS = [
    "L'eau coule depuis deux jours et ça commence à abîmer le meuble."
    " J'ai fermé le robinet d'arrêt en attendant.",
    "Le logement est au 3e étage, sans ascenseur."
    " Il faut prévoir le matériel, je n'ai rien sur place.",
    "الخدمة ماشي كبيرة، غير خاصها شي حد يعرف. الدار فوسط المدينة.",
    "C'est urgent, j'ai des invités ce week-end. Je suis disponible toute la journée.",
    "بغيت واحد يجي يشوف قبل ويعطيني الثمن النهائي. عندي الوقت، ماشي مستعجل.",
    "Ça fait deux fois que quelqu'un passe sans régler le problème."
    " J'aimerais quelqu'un d'expérimenté.",
    "L'appartement est vide, je peux vous donner accès quand vous voulez en semaine.",
    "خدمة صغيرة ولكن خاصها تتدار مزيان. كنخدم النهار، نقدر نتلاقى معاك العشية.",
]

#: Streets that exist in Moroccan cities, so an address reads as an address.
STREETS = [
    "12 rue Al Massira, Maârif",
    "45 avenue Hassan II",
    "8 rue Ibn Battouta, appartement 3",
    "Résidence Al Firdaous, bloc C, 2e étage",
    "23 rue de Fès, près de la pharmacie",
    "Lotissement Riad Salam, villa 14",
    "67 boulevard Zerktouni, 5e étage",
    "Rue Oued Ziz, immeuble 9, appartement 12",
]


#: What people actually write. Short, specific, and in whichever language they
#: think in — which is the mix the page has to lay out without breaking.
GOOD_COMMENTS = [
    "Travail propre et rapide, je recommande.",
    "Ponctuel et très professionnel. Merci !",
    "Bon rapport qualité-prix, rien à redire.",
    "Il a bien expliqué le problème avant de commencer.",
    "Nickel, il a même nettoyé après lui.",
    "Très satisfait, je le rappellerai sans hésiter.",
    "Sérieux et bien équipé. Rien à signaler.",
    "Intervention le jour même, problème réglé.",
    "Prix annoncé, prix payé. Ça fait plaisir.",
    "Il a pris le temps de bien faire les choses.",
    "Poli, à l'heure, et le résultat est impeccable.",
    "Deuxième fois que je fais appel à lui, toujours au top.",
    "خدمة نظيفة و بسرعة، الله يعطيه الصحة.",
    "جا فالوقت و الثمن كان معقول.",
    "معلّم فحالو، خدم مزيان.",
    "الله يبارك، خدمة متقنة و ثمن مناسب.",
    "شرح ليا كلشي قبل ما يبدا، و صايب المشكل.",
    "نصحت بيه جيراني، خدام نقي.",
    "جا نهار داكشي، ماخلاش المشكل يتعطل.",
    "راجل خدّام و كيحترم الوقت.",
]
MIXED_COMMENTS = [
    "Bon travail mais il est arrivé avec du retard.",
    "Correct dans l'ensemble, un peu cher à mon avis.",
    "Le résultat est bien, la finition pouvait être plus soignée.",
    "Ça fonctionne, mais il a fallu insister pour la facture.",
    "خدم مزيان ولكن تعطل شوية.",
    "الخدمة مزيانة، والثمن شوية غالي.",
    "صايب المشكل، ولكن خلا شوية دالوسخ.",
]
POOR_COMMENTS = [
    "Il a fallu le rappeler deux fois pour terminer.",
    "Pas convaincu par la finition.",
    "Devis dépassé sans prévenir.",
    "ما عجباتنيش الخدمة بزاف.",
    "تعطل بزاف و ما كملش الخدمة نهار الأول.",
]
REPLIES = [
    "Merci pour votre confiance !",
    "Merci beaucoup, à votre service.",
    "شكرا بزاف على الثقة.",
]


BIO_TEMPLATES = [
    "{years} ans d'expérience. Je travaille à {city} et dans les environs. "
    "Devis gratuit, travail garanti.",
    "Artisan installé à {city} depuis {years} ans. Je me déplace rapidement et "
    "je laisse le chantier propre.",
    "Je fais ce métier depuis {years} ans. Matériel professionnel, prix clair "
    "annoncé avant de commencer.",
    "{years} سنة دالخبرة. كنخدم فـ{city} و النواحي، و الثمن كنتفاهمو عليه قبل "
    "ما نبدا.",
    "معلّم فـ{city}، {years} سنة فالميدان. خدمة نظيفة و فالوقت.",
]


def backfill_bios(db: Session, *, rng: random.Random) -> int:
    """A profile page with an empty description is a page with a hole in it."""
    empty = (
        db.execute(
            select(ProviderProfile)
            .join(User, User.id == ProviderProfile.user_id)
            .where(User.phone.like(f"{DEMO_PHONE_PREFIX}%"), ProviderProfile.bio == "")
        )
        .scalars()
        .unique()
    )

    touched = 0
    for profile in empty:
        profile.bio = rng.choice(BIO_TEMPLATES).format(
            years=max(1, profile.years_experience), city=profile.city.name_fr
        )
        touched += 1
    return touched


def refresh_comments(db: Session, *, rng: random.Random) -> int:
    """Re-pick a comment for every demo review.

    The first pool was small enough that one tradesman's page showed the same
    sentence twice, which reads as a bug rather than as two people agreeing.
    Demo rows only — nothing here touches a review a real person wrote.
    """
    demo_authors = select(User.id).where(User.phone.like(f"{DEMO_CLIENT_PREFIX}%"))
    reviews = list(
        db.execute(
            select(Review)
            .where(Review.author_id.in_(demo_authors))
            .order_by(Review.provider_id, Review.id)
        )
        .scalars()
        .unique()
    )

    # Draw without replacement per tradesman. Picking at random put the same
    # sentence twice on one page often enough to read as a bug rather than as
    # two people happening to agree.
    per_provider: dict[int, dict[str, list[str]]] = {}
    touched = 0

    for review in reviews:
        bucket = "good" if review.rating >= 4 else "mixed" if review.rating == 3 else "poor"
        pools = per_provider.setdefault(review.provider_id, {})

        if not pools.get(bucket):
            source = (
                GOOD_COMMENTS
                if bucket == "good"
                else MIXED_COMMENTS
                if bucket == "mixed"
                else POOR_COMMENTS
            )
            shuffled = list(source)
            rng.shuffle(shuffled)
            pools[bucket] = shuffled

        review.comment = pools[bucket].pop()
        touched += 1

    return touched


def seed_clients(db: Session, *, total: int, rng: random.Random) -> list[User]:
    """Somebody has to have written the reviews."""
    existing = list(
        db.execute(select(User).where(User.phone.like(f"{DEMO_CLIENT_PREFIX}%"))).scalars()
    )
    if len(existing) >= total:
        return existing[:total]

    password_hash = hash_password(DEMO_PASSWORD)
    cities = list(db.execute(select(City)).scalars())

    for index in range(len(existing), total):
        user = User(
            phone=f"{DEMO_CLIENT_PREFIX}{index:07d}",
            password_hash=password_hash,
            full_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            role=Role.CLIENT,
            city_id=rng.choice(cities).id,
            language="ar",
        )
        db.add(user)
        existing.append(user)

    db.flush()
    return existing


def seed_history(db: Session, *, rng: random.Random) -> tuple[int, int]:
    """Give every demo tradesman a past: requests, offers, jobs, reviews.

    The rating on a card has to be the average of reviews somebody can open and
    read. Inventing `rating_avg` was fine while nothing displayed the reviews;
    P3 displays them, and a profile whose stars do not match its reviews is the
    first thing a visitor notices.
    """
    providers = list(
        db.execute(
            select(ProviderProfile)
            .join(User, User.id == ProviderProfile.user_id)
            .where(
                User.phone.like(f"{DEMO_PHONE_PREFIX}%"),
                ProviderProfile.status == ProviderStatus.APPROVED,
            )
        )
        .scalars()
        .unique()
    )
    if not providers:
        return 0, 0

    # Already done? Leave it alone rather than doubling everyone's history.
    if db.execute(select(func.count()).select_from(Job)).scalar_one() > 0:
        return 0, 0

    clients = seed_clients(db, total=90, rng=rng)
    now = utcnow()
    jobs_made = 0
    reviews_made = 0

    for profile in providers:
        trades = profile.trades
        if not trades:
            continue

        # A long tail: most tradesmen have a handful of jobs, a few have many.
        count = rng.choice([0, 0, 1, 2, 3, 3, 4, 5, 6, 8, 11, 14])
        # Backdate the account so "member since" is not all the same week.
        profile.created_at = now - timedelta(days=rng.randint(20, 900))

        for _ in range(count):
            trade = rng.choice(trades)
            client = rng.choice(clients)
            done_at = now - timedelta(days=rng.randint(1, 420), hours=rng.randint(0, 23))

            price = profile.starting_price_centimes or dirhams(200)
            agreed = int(price * rng.choice([1.0, 1.2, 1.5, 2.0, 2.5]))

            request = ServiceRequest(
                client_id=client.id,
                trade_id=trade.id,
                city_id=profile.city_id,
                title=rng.choice(JOB_TITLES.get(trade.slug, ["Petit travail"])),
                description=rng.choice(JOB_DESCRIPTIONS),
                address=rng.choice(STREETS),
                urgency=rng.choice(list(Urgency)),
                status=RequestStatus.DONE,
                offers_count=0,  # set below, from the offers actually written
                created_at=done_at - timedelta(days=rng.randint(1, 6)),
            )
            db.add(request)
            db.flush()

            offer = Offer(
                request_id=request.id,
                provider_id=profile.id,
                price_centimes=agreed,
                message="",
                status=OfferStatus.ACCEPTED,
                responded_at=done_at,
                lead_fee_centimes=dirhams(10),
                created_at=request.created_at,
            )
            db.add(offer)
            db.flush()

            # The ones he did not pick. They exist: C3 lists every offer a
            # request drew, and `offers_count` is what C2 shouts — a count
            # invented above a single row is the same lie as a rating with no
            # reviews behind it.
            losers = [
                other
                for other in rng.sample(providers, min(len(providers), 8))
                if other.id != profile.id and other.city_id == profile.city_id
            ][: rng.randint(0, 3)]
            for loser in losers:
                db.add(
                    Offer(
                        request_id=request.id,
                        provider_id=loser.id,
                        price_centimes=int(agreed * rng.uniform(0.8, 1.4)),
                        message="",
                        status=OfferStatus.REJECTED,
                        responded_at=done_at,
                        created_at=request.created_at + timedelta(hours=rng.randint(1, 20)),
                    )
                )
            request.offers_count = 1 + len(losers)
            db.flush()

            job = Job(
                request_id=request.id,
                offer_id=offer.id,
                client_id=client.id,
                provider_id=profile.id,
                agreed_price_centimes=agreed,
                status=JobStatus.CONFIRMED,
                started_at=done_at - timedelta(hours=3),
                finished_at=done_at,
                confirmed_at=done_at + timedelta(hours=2),
                created_at=request.created_at,
            )
            db.add(job)
            db.flush()
            jobs_made += 1

            # Four jobs in five get reviewed, which is about what a marketplace
            # sees and enough to make "no reviews yet" a state that appears.
            if rng.random() >= 0.8:
                continue

            roll = rng.random()
            if roll < 0.74:
                rating, comments = rng.choice([4, 5, 5, 5]), GOOD_COMMENTS
            elif roll < 0.93:
                rating, comments = 3, MIXED_COMMENTS
            else:
                rating, comments = rng.choice([1, 2]), POOR_COMMENTS

            review = Review(
                job_id=job.id,
                author_id=client.id,
                provider_id=profile.id,
                rating=rating,
                comment=rng.choice(comments),
                created_at=done_at + timedelta(days=rng.randint(0, 3)),
            )
            if rating >= 4 and rng.random() < 0.3:
                review.reply = rng.choice(REPLIES)
                review.replied_at = review.created_at + timedelta(days=1)

            db.add(review)
            reviews_made += 1

    db.flush()
    recompute_caches(db, providers)
    return jobs_made, reviews_made


def recompute_caches(db: Session, providers: list[ProviderProfile]) -> None:
    """Derive the numbers on the card from the rows behind them.

    `jobs_done`, `rating_avg` and `rating_count` are caches. Seeding them by
    hand and the reviews separately is how a profile ends up claiming 4.9 over
    a page of three-star reviews.
    """
    for profile in providers:
        profile.jobs_done = db.execute(
            select(func.count())
            .select_from(Job)
            .where(Job.provider_id == profile.id, Job.status == JobStatus.CONFIRMED)
        ).scalar_one()

        count, average = db.execute(
            select(func.count(), func.avg(Review.rating)).where(
                Review.provider_id == profile.id, Review.is_hidden.is_(False)
            )
        ).one()

        profile.rating_count = int(count)
        profile.rating_avg = 0.0 if not count else round(float(average), 1)


def _document_png(width: int = 480, height: int = 300) -> bytes:
    """A stand-in identity document.

    Bands rather than a flat square, so the approvals screen shows something
    shaped like a document instead of a colour swatch — and so a broken image
    is obvious rather than plausible.
    """
    import struct
    import zlib

    def pixel(x: int, y: int) -> tuple[int, int, int]:
        if y < height // 6:
            return (16, 58, 94)  # a header band
        if height // 3 < y < height // 3 + 14 and width // 4 < x < width - 40:
            return (150, 165, 180)  # a line of text
        if height // 2 < y < height // 2 + 14 and width // 4 < x < width - 120:
            return (150, 165, 180)
        if height // 3 < y < height - 40 and 24 < x < width // 5:
            return (196, 208, 220)  # the photo box
        return (232, 238, 244)

    raw = b"".join(
        b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(width)) for y in range(height)
    )

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\x0a"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def _photo_png(tint: tuple[int, int, int], width: int = 640, height: int = 480) -> bytes:
    """A stand-in photograph of the problem, for C3's gallery.

    Shaped like a room — a wall, a floor line, an object standing on it, and
    enough grain that it reads as a photograph rather than a swatch. A flat
    rectangle in a photo slot looks like an image that failed to load, which is
    the one thing a placeholder must not look like.
    """
    import struct
    import zlib

    red, green, blue = tint
    floor = int(height * 0.68)
    grain = random.Random(sum(tint))

    def pixel(x: int, y: int) -> tuple[int, int, int]:
        if y < floor:
            shade = 1.05 - (y / floor) * 0.3  # light falling down the wall
        else:
            shade = 0.55 - ((y - floor) / (height - floor)) * 0.12  # darker floor

        # Something standing against the wall, casting the eye somewhere.
        if floor - height // 3 < y < floor and width // 3 < x < width // 3 + width // 5:
            shade *= 0.6

        # A vignette, then grain: both are what a phone photo actually has.
        dx = (x - width / 2) / (width / 2)
        dy = (y - height / 2) / (height / 2)
        shade *= 1 - 0.18 * (dx * dx + dy * dy)
        shade += grain.uniform(-0.02, 0.02)

        return (
            max(0, min(255, int(red * shade))),
            max(0, min(255, int(green * shade))),
            max(0, min(255, int(blue * shade))),
        )

    raw = b"".join(
        b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(width)) for y in range(height)
    )

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\x0a"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


OFFER_MESSAGES = [
    "Je peux passer demain matin, le déplacement est compris dans le prix.",
    "غادي نجي نشوف المشكل قبل، ومن بعد نعطيك الثمن النهائي.",
    "Prix ferme, matériel inclus. Je travaille aussi le dimanche.",
    "J'ai fait le même travail dans votre quartier la semaine dernière.",
    "الخدمة كتاخد نهار واحد، والضمانة 6 شهور.",
]

#: The client whose screens the demo shows. The first seeded client, so the
#: same account every time.
DEMO_CLIENT_INDEX = 0


def backfill_request_details(db: Session, *, rng: random.Random) -> int:
    """Give the seeded history a description and an address.

    Both were left blank while nothing displayed them. M7 shows the tradesman
    the address he is driving to and the description he is quoting on, so a
    dash and an empty paragraph now read as a broken screen rather than as
    absent demo data.
    """
    fixed = 0
    for request in db.execute(select(ServiceRequest)).scalars():
        if not request.description.strip():
            request.description = rng.choice(JOB_DESCRIPTIONS)
            fixed += 1
        if request.address.strip() in ("", "—"):
            request.address = rng.choice(STREETS)
            fixed += 1

    db.flush()
    return fixed


def backfill_offer_counts(db: Session) -> int:
    """Make `offers_count` equal the offers that actually exist.

    Earlier seeds invented the number above a single offer row. C3 lists every
    offer a request drew, so the two are now read side by side and any gap
    between them is visible on screen.
    """
    counts = select(Offer.request_id, func.count().label("n")).group_by(Offer.request_id).subquery()
    real: dict[int, int] = {
        int(request_id): int(number)
        for request_id, number in db.execute(select(counts.c.request_id, counts.c.n))
    }

    fixed = 0
    for request in db.execute(select(ServiceRequest)).scalars():
        expected = real.get(request.id, 0)
        if request.offers_count != expected:
            request.offers_count = expected
            fixed += 1

    db.flush()
    return fixed


def seed_live_requests(db: Session, *, rng: random.Random) -> int:
    """Give one demo client requests that are still alive.

    `seed_history` only writes finished work, which leaves C2 and C3 with
    nothing but grey rows: no open request, no offer anyone can still choose
    between, and no way to see the screens do their job.
    """
    from app.config import get_settings
    from app.services.storage import Bucket, LocalDiskStorage

    clients = list(
        db.execute(
            select(User).where(User.phone.like(f"{DEMO_CLIENT_PREFIX}%")).order_by(User.phone)
        ).scalars()
    )
    if not clients:
        return 0
    client = clients[DEMO_CLIENT_INDEX]

    # Already done? Leave it alone rather than pushing him over the open cap.
    already = db.execute(
        select(func.count())
        .select_from(ServiceRequest)
        .where(
            ServiceRequest.client_id == client.id,
            ServiceRequest.status.in_([RequestStatus.OPEN, RequestStatus.CANCELLED]),
        )
    ).scalar_one()
    if already:
        return 0

    # A request is answered by tradesmen in its own city — so put him where the
    # tradesmen are, rather than posting into an empty one.
    city_id, _ = db.execute(
        select(ProviderProfile.city_id, func.count())
        .where(ProviderProfile.status == ProviderStatus.APPROVED)
        .group_by(ProviderProfile.city_id)
        .order_by(func.count().desc())
        .limit(1)
    ).one()
    city = db.get(City, city_id)
    if city is None:
        return 0
    client.city_id = city.id

    def providers_for(trade: Trade, limit: int) -> list[ProviderProfile]:
        return list(
            db.execute(
                select(ProviderProfile)
                .join(provider_trades, provider_trades.c.provider_id == ProviderProfile.id)
                .where(
                    ProviderProfile.city_id == city.id,
                    ProviderProfile.status == ProviderStatus.APPROVED,
                    provider_trades.c.trade_id == trade.id,
                )
                .order_by(ProviderProfile.rating_avg.desc())
                .limit(limit)
            )
            .scalars()
            .unique()
        )

    trades = list(db.execute(select(Trade).where(Trade.is_active.is_(True))).scalars())
    busy = next((t for t in trades if providers_for(t, 3)), None)
    if busy is None:
        return 0
    quiet = next((t for t in trades if t.id != busy.id), busy)

    storage = LocalDiskStorage(get_settings().upload_dir)
    now = utcnow()
    made = 0

    # 1. The one the screens are for: open, and three tradesmen have answered.
    answered = ServiceRequest(
        client_id=client.id,
        trade_id=busy.id,
        city_id=city.id,
        title=JOB_TITLES.get(busy.slug, ["Petit travail"])[0],
        description=(
            "L'eau coule sous l'évier depuis deux jours et ça a commencé à "
            "abîmer le meuble. J'ai fermé le robinet d'arrêt en attendant. "
            "Le logement est au 3e étage, sans ascenseur."
        ),
        address="14 rue Ibn Sina, appartement 8",
        urgency=Urgency.THIS_WEEK,
        status=RequestStatus.OPEN,
        budget_min_centimes=dirhams(200),
        budget_max_centimes=dirhams(600),
        offers_count=0,
        expires_at=now + timedelta(days=REQUEST_EXPIRY_DAYS),
        created_at=now - timedelta(days=2),
    )
    db.add(answered)
    db.flush()

    for order, tint in enumerate([(168, 152, 132), (132, 148, 168)]):
        path = storage.save(
            _photo_png(tint), bucket=Bucket.PUBLIC, folder=f"requests/{answered.id}"
        )
        db.add(
            RequestPhoto(request_id=answered.id, url=f"/api/v1/uploads/{path}", sort_order=order)
        )

    candidates = providers_for(busy, 3)
    for index, provider in enumerate(candidates):
        db.add(
            Offer(
                request_id=answered.id,
                provider_id=provider.id,
                price_centimes=dirhams(rng.choice([250, 320, 400, 480])),
                message=rng.choice(OFFER_MESSAGES),
                available_from=now + timedelta(days=index + 1),
                status=OfferStatus.PENDING,
                created_at=answered.created_at + timedelta(hours=3 * index + 2),
            )
        )
    answered.offers_count = len(candidates)
    made += 1

    # 2. Open, and nobody has answered yet — the state C3 has to be honest about.
    waiting = ServiceRequest(
        client_id=client.id,
        trade_id=quiet.id,
        city_id=city.id,
        title=JOB_TITLES.get(quiet.slug, ["Petit travail"])[0],
        description=(
            "بغيت واحد يجي يشوف الخدمة ويعطيني الثمن. الدار فوسط المدينة "
            "والخدمة ماشي كبيرة، غير خاصها شي حد يعرف."
        ),
        address="Résidence Al Firdaous, bloc C",
        urgency=Urgency.TODAY,
        status=RequestStatus.OPEN,
        offers_count=0,
        expires_at=now + timedelta(days=REQUEST_EXPIRY_DAYS),
        created_at=now - timedelta(hours=4),
    )
    db.add(waiting)
    made += 1

    # 3. One he changed his mind about, so the closed group is not empty either.
    dropped = ServiceRequest(
        client_id=client.id,
        trade_id=busy.id,
        city_id=city.id,
        title=JOB_TITLES.get(busy.slug, ["Petit travail"])[-1],
        description="Finalement un voisin s'en est occupé, je n'ai plus besoin.",
        address="14 rue Ibn Sina, appartement 8",
        urgency=Urgency.FLEXIBLE,
        status=RequestStatus.CANCELLED,
        offers_count=0,
        cancelled_at=now - timedelta(days=9),
        cancel_reason="Réglé autrement",
        created_at=now - timedelta(days=11),
    )
    db.add(dropped)
    made += 1

    db.flush()
    return made


def seed_pending_applications(db: Session, *, total: int, rng: random.Random) -> int:
    """Applications waiting for an admin.

    Every demo tradesman is approved, which leaves A2 empty and impossible to
    judge. These wait in the queue with a real identity document behind them,
    because reviewing one is the entire point of the screen.
    """
    from app.config import get_settings
    from app.services.storage import Bucket, LocalDiskStorage

    existing = set(
        db.execute(
            select(User.phone).where(User.phone.like(f"{DEMO_PENDING_PREFIX}%"))
        ).scalars()
    )
    if len(existing) >= total:
        return 0

    cities = list(db.execute(select(City)).scalars())
    trades = list(db.execute(select(Trade)).scalars())
    storage = LocalDiskStorage(get_settings().upload_dir)
    password_hash = hash_password(DEMO_PASSWORD)
    document = _document_png()
    created = 0

    for index in range(len(existing), total):
        city = rng.choice(cities)
        trade = rng.choice(trades)

        user = User(
            phone=f"{DEMO_PENDING_PREFIX}{index:06d}",
            password_hash=password_hash,
            full_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            role=Role.PROVIDER,
            city_id=city.id,
            language="ar",
        )
        db.add(user)
        db.flush()

        years = rng.randint(1, 20)
        profile = ProviderProfile(
            user_id=user.id,
            city_id=city.id,
            radius_km=rng.choice([5, 10, 20, 35]),
            headline=rng.choice(HEADLINES.get(trade.slug, ["Services à domicile"])),
            bio=rng.choice(BIO_TEMPLATES).format(years=years, city=city.name_fr),
            years_experience=years,
            starting_price_centimes=dirhams(BASE_PRICE_DH.get(trade.slug, 150)),
            status=ProviderStatus.PENDING,
            id_card_url=storage.save(
                document, bucket=Bucket.PRIVATE, folder=f"id-cards/{user.id}"
            ),
        )
        profile.trades = [trade]
        db.add(profile)
        db.flush()

        db.add(
            CreditAccount(
                provider_id=profile.id,
                balance_centimes=0,
                free_leads_left=FREE_LEADS_NEW_PROVIDER,
            )
        )
        created += 1

    return created


def main() -> int:
    settings = get_settings()
    if settings.is_production:
        print("refusing to run against a production database", file=sys.stderr)
        return 1

    rng = random.Random(20260829)  # deterministic: the same demo every time
    with session_scope() as db:
        created, backfilled = seed_demo(db, total=240, rng=rng)
        jobs, reviews = seed_history(db, rng=rng)
        bios = backfill_bios(db, rng=rng)
        comments = refresh_comments(db, rng=rng)
        live = seed_live_requests(db, rng=rng)
        fixed = backfill_offer_counts(db)
        details = backfill_request_details(db, rng=rng)
        waiting = seed_pending_applications(db, total=6, rng=rng)

    print(f"demo tradesmen created: {created}, headlines backfilled: {backfilled}")
    print(f"jobs: {jobs}, reviews: {reviews}, bios: {bios}, comments: {comments}")
    print(f"live requests for the demo client: {live}, offer counts fixed: {fixed}")
    print(f"request descriptions and addresses filled in: {details}")
    print(f"applications waiting for an admin: {waiting}")
    print(f"they all sign in with the password {DEMO_PASSWORD!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
