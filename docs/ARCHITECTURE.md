# Brikole — Architecture

A web marketplace for small trade services in Morocco. One React app serving four
roles, one FastAPI backend, one MySQL database.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | **React 19 + TypeScript strict + Vite** | asked for; Vite keeps the deploy story to one static bundle + one API, with no second Node runtime to host |
| Styling | **Tailwind v4** | tokens defined once in `web/src/ui/theme.ts` and exposed as CSS variables, so light/dark and RTL are one source of truth |
| Data | TanStack Query (server state) + Zustand (UI state) | cache, retry and invalidation for free; Zustand only for things the server does not own |
| Routing | React Router | route groups per role, guarded by a single `<RequireRole>` |
| Backend | **FastAPI + Pydantic v2** | typed request/response, and an OpenAPI schema we generate the frontend's types from |
| ORM | SQLAlchemy 2 (typed `Mapped[]`) + Alembic | explicit migrations, no magic |
| DB | **MySQL 8** | asked for. No PostGIS, so proximity is Haversine over an index on `(city_id)` then a bounding box on `(lat, lng)` — fine well past a million rows |
| Auth | phone + password → JWT | short-lived access token in memory, refresh token in an httpOnly cookie. SMS OTP costs money per message, so it is Phase 4 behind `SmsProvider` |
| Passwords | argon2id | via `passlib` |
| Files | `StorageProvider` interface, local disk in dev | S3/R2 later without touching a screen. **Two buckets:** `public` for avatars and portfolio photos, `private` for identity documents. A bucket is public or it is not — one bucket does not survive contact with what goes in it. The declared content type is a hint from the client, so uploads are typed by their first bytes instead. |
| i18n | i18next — `ar` (default, RTL) · `fr` · `en` | the API returns error *codes*; only the client owns wording |

MySQL 8 is the production target. Local development runs the same schema on
MariaDB 10.11 or MySQL 8 — the migrations stay inside the common subset of both,
which is why no migration uses functional indexes or `CHECK ... JSON_*`.

## Folder structure

```
brikole/
├─ api/
│  ├─ app/
│  │  ├─ core/            # framework-free: rules, no FastAPI, no SQLAlchemy, no I/O
│  │  │  ├─ security.py   # hashing, JWT encode/decode
│  │  │  ├─ phone.py      # Moroccan number → E.164
│  │  │  ├─ money.py      # centimes
│  │  │  ├─ permissions.py# what each role may do
│  │  │  └─ errors.py     # the error-code vocabulary
│  │  ├─ models/          # SQLAlchemy tables
│  │  ├─ schemas/         # Pydantic in/out
│  │  ├─ repositories/    # every query lives here
│  │  ├─ services/        # use cases that need the database
│  │  ├─ api/             # routers — parse, authorize, delegate
│  │  ├─ deps.py          # current_user, require_role
│  │  ├─ config.py        # settings from .env
│  │  └─ db.py            # engine + session
│  ├─ migrations/         # Alembic
│  ├─ tests/              # pytest
│  └─ pyproject.toml
│
└─ web/
   ├─ src/
   │  ├─ app/             # routes and role gates only, no logic
   │  ├─ features/        # one folder per feature, UI + hooks together
   │  ├─ data/            # api client, TanStack Query hooks, generated types
   │  ├─ ui/              # design system: theme.ts, Button, Field, Card…
   │  ├─ hooks/  lib/     # i18n, formatters, small hooks
   │  └─ main.tsx
   └─ package.json
```

Rules: routes hold no business logic, features never import each other, money is
always integer centimes, and the API decides what is allowed.

## The four roles

`role` is a column on `users`, set at registration and **changeable only by an
admin**. Two of the four are staff roles and cannot be self-registered at all: a
moderator or an admin is created by an existing admin.

| | client | m3allem | moderator | admin |
|---|---|---|---|---|
| Post a request / send an offer | ✅ / — | — / ✅ | — | — |
| Read and rule on disputes | own only | own only | ✅ all | ✅ all |
| Suspend a user | — | — | ✅ temporary | ✅ permanent |
| Approve a tradesman | — | — | — | ✅ |
| Money: top-ups, ledger, revenue | — | own only | **never** | ✅ |
| Trades, cities, platform settings | — | — | — | ✅ |

A moderator deliberately cannot see money. That separation is the whole reason the
role exists as something other than a weaker admin.

## Key flows

**Registration and sign-in**
1. The number is normalised to E.164 (`+212XXXXXXXXX`) before it is stored or looked
   up, so `0612…`, `+212612…` and `212612…` are one account
2. Register takes phone, name, password and one of two self-serviceable roles
   (`client`, `provider`); anything else is rejected by the API, not by the form
3. Login returns a short access token plus a refresh token in an httpOnly cookie
4. A `provider` lands with no `provider_profile` → the app sends him to M1
5. Five wrong passwords → the account locks for 15 minutes, counted server-side

**Tradesman onboarding (M1 → M2 → A2)**
1. M1 collects trades, city and radius, the headline and description, years of
   experience, an optional starting price, an optional avatar, the identity
   document, and up to ten portfolio photos — over four steps, beside a live
   preview of the card a client will see
2. The profile is created `pending`; the guard in the service layer forces that
   status regardless of what the client sent, and an approved profile cannot be
   resubmitted at all — it is edited at M8, because resubmitting would take a
   tradesman out of the grid he was let into
3. The identity document goes to the private bucket and is readable by its owner
   and an admin, nobody else. Asking for one that is not yours is a 404, not a
   403: whether somebody has uploaded an identity document is itself private
4. A2 is the admin queue: `approve` or `reject` with a reason
5. Rejected shows the reason at M2 and can be resubmitted once answered
6. Only an `approved` profile appears in search or sees the request feed

**Counting who is available, and where**
`GET /trades` returns each trade with `providers_count`, and takes an optional
`city_id`. The join is an outer join on purpose: a trade nobody works in still
comes back, with zero, because hiding it leaves the visitor wondering whether the
trade exists at all. Only `approved` profiles count — a pending application is not
somebody you can hire. `python -m app.demo_seed` fills a development database with
240 tradesmen spread unevenly across trades and cities, so the screens are judged
against numbers that look like a real marketplace rather than a uniform one.

**Request → offer → job**
1. C1 creates a `request` (`open`) with a trade, description, photos, address, and
   an urgency
2. The feed at M4 shows a tradesman the open requests whose trade is one of his and
   whose city is his — capped by his radius
3. He sends an `offer` (price in centimes, message, when he can come). One live
   offer per tradesman per request
4. The client accepts one offer at C3. In a single transaction: the offer becomes
   `accepted`, the other offers `rejected`, the request `assigned`, a `job` is
   created, and **the lead fee is charged** to the tradesman
5. The job runs `assigned → in_progress → done`, then the client confirms and rates
6. Either side can open a `dispute` on a job until 7 days after it is done

**The lead fee — the only money the platform takes**
The fee is charged at *offer acceptance*, not at completion: that is the moment the
platform delivered what it promised, and it does not depend on a cash payment
nobody can observe. The amount comes from the trade's `lead_fee_centimes`, falling
back to the platform default. A tradesman with free leads left spends one of those
instead. Balance below the fee → he is not shown the feed, so he can never take a
lead he cannot pay for. Every movement is a `credit_transactions` row; the balance
column is a cache of that ledger and is only ever written in the same transaction.

**Top-up (Phase 2, decided)**
Bank transfer with an admin in the loop, exactly like the old car-wash app: the
tradesman submits an amount and a transfer reference, `topup_requests` records it
as `pending` and **no balance moves**; an admin checks the statement and approves,
which credits the balance and writes the ledger row. Card payment later implements
the same `PaymentGateway` interface without changing M9.

**Cash, and what that means for disputes**
The client pays the tradesman directly. The platform never holds the money, so a
dispute is never a refund — it is about the work, and the outcomes are a warning, a
suspension, and a refund of the *lead fee* to the tradesman when the client was at
fault.

## Build order

| Phase | Content |
|---|---|
| 0 | Schema and migrations, auth and the four roles, design system, i18n |
| 1 | C1 request wizard, M4 feed, M5 offer, C3 accept |
| 2 | Job lifecycle, reviews, lead fee, credit and top-up |
| 3 | Moderator disputes, admin approvals, settings, statistics |
| 4 | Chat, fixed-price catalogue, SMS OTP, online payment |

## Decisions still open

1. Brand name and colours. `brikole` is a working name; renaming is cheap now and
   expensive after the first deploy.
2. The default lead fee, and whether it should differ per trade from day one. The
   column exists either way.
3. Whether a client may re-open a request after cancelling it, or must create a new
   one. Currently: a new one.
