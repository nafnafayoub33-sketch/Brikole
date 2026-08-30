# Brikole

A web marketplace for small trade services in Morocco — plumber, painter, carpenter,
electrician, mobile car wash and the rest. A client describes the job, tradesmen send
priced offers, the client picks one and pays him directly in cash.

Four roles: **client**, **m3allem** (tradesman), **moderator** (disputes), **admin**.

> Brikole is a project of its own. Where it sits beside the Lavage car-wash app, the
> two are unrelated and share no code, build or database.

Read [`CLAUDE.md`](CLAUDE.md) before writing code. The specs are in
[`docs/SCREENS.md`](docs/SCREENS.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Running it

You need Python 3.11+, Node 20+, and MySQL 8 (MariaDB 10.11 also works).

**Database**

```bash
mysql -uroot -e "CREATE DATABASE brikole CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -uroot -e "CREATE USER 'brikole'@'127.0.0.1' IDENTIFIED BY 'devpassword';"
mysql -uroot -e "GRANT ALL ON brikole.* TO 'brikole'@'127.0.0.1';"
```

**API** — http://127.0.0.1:8000, docs at `/docs`

```bash
cd api
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # then set SECRET_KEY and DATABASE_URL
alembic upgrade head
python -m app.seed            # trades, cities, and the first admin
python -m app.demo_seed       # optional: 240 tradesmen, so the counts are real
uvicorn app.main:app --reload
```

**Web** — http://127.0.0.1:5173

```bash
cd web
npm install
cp .env.example .env
npm run dev
```

## Scripts

| Where | Command | What it does |
|---|---|---|
| `api` | `pytest` | unit tests (no database) and API tests |
| `api` | `ruff check . && mypy app` | lint and types |
| `api` | `alembic revision --autogenerate -m "..."` | new migration |
| `web` | `npm run dev` / `build` | Vite |
| `web` | `npm run typecheck` | `tsc --noEmit` |
| `web` | `npm run lint` | ESLint |
| `web` | `npm test` | Vitest |

## Layout

```
api/app/core/          framework-free rules, unit-tested without a database
api/app/models/        SQLAlchemy tables
api/app/repositories/  every query lives here
api/app/services/      use cases that need the database
api/app/api/           routers: parse, authorize, delegate
web/src/app/           routes and role gates only
web/src/features/      one folder per feature
web/src/ui/            the design system, including theme.ts
web/src/data/          api client and TanStack Query hooks
```

## A build warning you will see, and should not "fix"

`npm run build` and `npm test` print one warning:

```
▲ [WARNING] Cannot find base config file "expo/tsconfig.base" [tsconfig.json]
    ../../tsconfig.json:2:13
```

That is the *repository root's* tsconfig, belonging to the unrelated Lavage
Expo app. Vite compiles `vite.config.ts` with esbuild before any of our config
is read, and esbuild's tsconfig discovery walks up out of this folder to find
it. It affects nothing: `vite.config.ts` has no JSX and no `@/` imports, and
every source file is compiled against `web/tsconfig.json`.

Two things follow:

- **Do not edit the root tsconfig.** It belongs to the other project.
- **Keep `web/tsconfig.json` strict JSON, with no `//` comments.** esbuild's
  parser rejects comments *silently* and keeps climbing — which is how it found
  the root config in the first place, along with a `paths` mapping that points
  `@/*` at the other project's `src`. `src/test/tsconfig.test.ts` guards this.

Running `vite build --configLoader native` silences the warning on Node 22.6+,
which is why the scripts do not do it: it would raise the Node floor for
cosmetics.

## Money

Always integer centimes. `3000` is 30,00 DH. Formatted only at render time.

## Secrets

`.env` is gitignored on both sides; `.env.example` is the template. `SECRET_KEY`
must be a real random value in production — the API refuses to start with the
placeholder when `ENV=production`.

## What is built

Phase 0, plus the front of the marketplace: the schema and its migrations,
phone+password auth with JWT, the four-role permission layer, seed data, and the
React shell with the design tokens, the three languages and the role-gated router.

On top of that, **P1** (home: hero, tradesmen, trades with live counts per city)
and **P2** (`/services` and `/services/:slug`: search, city and sort controls,
pagination), served by `GET /providers` and `GET /trades`.

Everything past that names the screen it stands in for, using the IDs from
`docs/SCREENS.md`.
