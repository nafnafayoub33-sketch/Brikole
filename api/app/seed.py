"""Seed a fresh database: trades, cities, settings, and the first admin.

    python -m app.seed

Safe to run twice — everything is matched on its slug or key and left alone if
it is already there.

The first admin is created only when SEED_ADMIN_PHONE and SEED_ADMIN_PASSWORD
are in the environment. There is deliberately no default password: an admin
account with a known password is how a platform gets taken over on day one.
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.errors import DomainError
from app.core.phone import normalise_phone
from app.core.policy import DEFAULTS
from app.core.security import hash_password
from app.db import session_scope
from app.models.catalog import City, Trade
from app.models.system import PlatformSetting
from app.models.user import User

TRADES: list[tuple[str, str, str, str, str]] = [
    # slug, ar, fr, en, icon
    ("plombier", "سباك", "Plombier", "Plumber", "droplet"),
    ("electricien", "كهربائي", "Électricien", "Electrician", "zap"),
    ("peintre", "صباغ", "Peintre", "Painter", "brush"),
    ("menuisier", "نجار", "Menuisier", "Carpenter", "hammer"),
    ("lavage-auto", "غسيل السيارات بالمنزل", "Lavage auto à domicile", "Mobile car wash", "car"),
    ("climatisation", "تكييف الهواء", "Climatisation", "Air conditioning", "wind"),
    ("macon", "بنّاء", "Maçon", "Mason", "brick"),
    ("serrurier", "حدّاد أقفال", "Serrurier", "Locksmith", "key"),
    ("carreleur", "مبلّط", "Carreleur", "Tiler", "grid"),
    ("jardinier", "بستاني", "Jardinier", "Gardener", "leaf"),
    ("menage", "تنظيف المنازل", "Ménage", "House cleaning", "sparkles"),
    ("demenagement", "نقل الأثاث", "Déménagement", "Moving", "truck"),
    ("vitrier", "زجّاج", "Vitrier", "Glazier", "square"),
    (
        "electromenager",
        "إصلاح الأجهزة المنزلية",
        "Réparation électroménager",
        "Appliance repair",
        "plug",
    ),
    ("soudeur", "لحّام", "Soudeur", "Welder", "flame"),
    ("antenne", "تركيب الهوائيات", "Antenne & parabole", "Antenna & satellite", "radio"),
]

CITIES: list[tuple[str, str, str, float, float]] = [
    # slug, ar, fr/en, lat, lng
    ("casablanca", "الدار البيضاء", "Casablanca", 33.5731, -7.5898),
    ("rabat", "الرباط", "Rabat", 34.0209, -6.8416),
    ("sale", "سلا", "Salé", 34.0531, -6.7985),
    ("marrakech", "مراكش", "Marrakech", 31.6295, -7.9811),
    ("fes", "فاس", "Fès", 34.0181, -5.0078),
    ("tanger", "طنجة", "Tanger", 35.7595, -5.8340),
    ("agadir", "أكادير", "Agadir", 30.4278, -9.5981),
    ("meknes", "مكناس", "Meknès", 33.8935, -5.5473),
    ("oujda", "وجدة", "Oujda", 34.6867, -1.9114),
    ("kenitra", "القنيطرة", "Kénitra", 34.2610, -6.5802),
    ("tetouan", "تطوان", "Tétouan", 35.5785, -5.3684),
    ("safi", "آسفي", "Safi", 32.2994, -9.2372),
    ("el-jadida", "الجديدة", "El Jadida", 33.2549, -8.5079),
    ("nador", "الناظور", "Nador", 35.1681, -2.9335),
    ("beni-mellal", "بني ملال", "Béni Mellal", 32.3373, -6.3498),
    ("mohammedia", "المحمدية", "Mohammedia", 33.6866, -7.3830),
    ("khouribga", "خريبكة", "Khouribga", 32.8811, -6.9063),
    ("essaouira", "الصويرة", "Essaouira", 31.5085, -9.7595),
    ("laayoune", "العيون", "Laâyoune", 27.1536, -13.2033),
    ("ouarzazate", "ورزازات", "Ouarzazate", 30.9335, -6.9370),
]


def seed_trades(db: Session) -> int:
    existing = {slug for slug in db.execute(select(Trade.slug)).scalars()}
    added = 0
    for order, (slug, ar, fr, en, icon) in enumerate(TRADES, start=1):
        if slug in existing:
            continue
        db.add(
            Trade(
                slug=slug,
                name_ar=ar,
                name_fr=fr,
                name_en=en,
                icon=icon,
                sort_order=order * 10,
                is_active=True,
            )
        )
        added += 1
    return added


def seed_cities(db: Session) -> int:
    existing = {slug for slug in db.execute(select(City.slug)).scalars()}
    added = 0
    for slug, ar, latin, lat, lng in CITIES:
        if slug in existing:
            continue
        db.add(
            City(
                slug=slug,
                name_ar=ar,
                name_fr=latin,
                name_en=latin,
                latitude=lat,
                longitude=lng,
                is_active=True,
            )
        )
        added += 1
    return added


def seed_settings(db: Session) -> int:
    existing = {key for key in db.execute(select(PlatformSetting.key)).scalars()}
    added = 0
    for key, value in DEFAULTS.items():
        if key in existing:
            continue
        db.add(PlatformSetting(key=key, value=value))
        added += 1
    return added


def seed_admin(db: Session) -> str:
    raw_phone = os.environ.get("SEED_ADMIN_PHONE", "").strip()
    password = os.environ.get("SEED_ADMIN_PASSWORD", "").strip()
    name = os.environ.get("SEED_ADMIN_NAME", "Administrateur").strip()

    if not raw_phone or not password:
        return (
            "skipped — set SEED_ADMIN_PHONE and SEED_ADMIN_PASSWORD to create the first admin"
        )

    try:
        phone = normalise_phone(raw_phone)
    except DomainError:
        return f"skipped — SEED_ADMIN_PHONE {raw_phone!r} is not a valid Moroccan number"

    if db.execute(select(User.id).where(User.phone == phone)).scalar_one_or_none() is not None:
        return f"already exists ({phone})"

    try:
        password_hash = hash_password(password)
    except DomainError as exc:
        return f"skipped — SEED_ADMIN_PASSWORD rejected ({exc.code.value})"

    db.add(
        User(
            phone=phone,
            password_hash=password_hash,
            full_name=name,
            role=Role.ADMIN,
            language="ar",
        )
    )
    return f"created ({phone})"


def main() -> int:
    with session_scope() as db:
        trades = seed_trades(db)
        cities = seed_cities(db)
        settings = seed_settings(db)
        admin = seed_admin(db)

    print(f"trades:   +{trades}")
    print(f"cities:   +{cities}")
    print(f"settings: +{settings}")
    print(f"admin:    {admin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
