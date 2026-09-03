# CLAUDE.md — Brikole

Project rules for Brikole. Read this before writing any code here.

> **Brikole is a separate project.** Where it sits beside the Lavage car-wash app,
> it shares nothing with it — not a dependency, not a build, not a database, not a
> line of code. Never import across that boundary in either direction, and never
> edit anything outside Brikole's own tree.

## What this is

A web marketplace for small trade services in Morocco: plumber, painter, carpenter,
electrician, mobile car wash, and so on. Three parties, four roles:

- **Client** — describes the job, receives offers from tradesmen, talks to one in the
  chat until they agree a price, pays the tradesman in cash, rates the work.
- **M3allem** (tradesman) — is approved by an admin, sees job requests matching his
  trades and his area, sends a priced offer, settles the terms in the chat, does the
  work.
- **Moderator** — resolves disputes and handles reports. Sees nothing about money.
- **Admin** — approves tradesmen, manages users, money, trades, settings, statistics.

**Business model:** the platform charges the *tradesman* a fixed fee **only when the
client and he have both agreed the same terms** — that is the moment a real lead was
delivered. The fee is deducted from a prepaid balance and is set per trade in
`platform_settings`. A new
tradesman gets a number of free leads. Balance at zero → he stops seeing the request
feed. There is **no commission on the job price**, and the platform never holds
client money: the client pays the tradesman directly, in cash.

## The rule the product is built around

**No contact detail reaches the other side until both have agreed.** The platform
earns its dirham when a lead becomes a job, and only if the job goes through the
platform; a phone number handed over early is the business model walking out of the
door. So:

- The tradesman's phone number is on the **job** payload and on no other. Never on a
  profile, never on an offer, never in a chat message. If a screen needs a way to
  reach somebody and no job exists, the answer is that it does not get one.
- The chat between them (C9 / M12) strikes numbers, emails, links and `@handles` out
  of every message in both directions, including numbers spelled in words and typed
  in Arabic-Indic digits. The message is still delivered, with the contact struck
  out; the struck contact is never stored.
- That redaction is a **deterrent**, not a wall — somebody can photograph a card. The
  wall is the schema, and the schema is what must never be loosened.
- A job exists only when **both** sides have signed the same version of the deal. Any
  change to the price or the terms clears both signatures, including the changer's
  own.

## Read these first

| File | What it holds |
|---|---|
| `docs/SCREENS.md` | Every screen, its contents, its states, per role. |
| `docs/ARCHITECTURE.md` | Stack, folder layout, key flows, build order. |
| `api/app/models/` | The database, as SQLAlchemy models. |
| `web/src/ui/theme.ts` | Design tokens — light and dark. |
| `web/src/lib/i18n.ts` | Arabic, French, English. |

If a request contradicts these files, say so instead of silently doing something else.

## Stack

React 19 + TypeScript strict + Vite + Tailwind · TanStack Query + Zustand ·
React Router · i18next — talking to — Python 3.11 + FastAPI + Pydantic v2 +
SQLAlchemy 2 + Alembic + MySQL 8.

## Rules

**Architecture**
- The **API is the security boundary.** Every endpoint declares the role it needs.
  The React app decides what to *show*, never what is *allowed*.
- Business rules live in `api/app/core/` and are framework-free: no FastAPI, no
  SQLAlchemy, no I/O. They are unit-tested without a database.
- Routers (`api/app/api/`) only parse, authorize and delegate. No SQL in a router.
- All database access goes through `api/app/repositories/`. A service never writes
  a query inline.
- On the web side, components never call `fetch` directly — data goes through
  `web/src/data/` hooks built on TanStack Query.
- Features never import from each other. Shared code goes to `web/src/ui`,
  `web/src/hooks`, `web/src/lib`.

**Money**
- Always integer **centimes**, named `*_centimes`. `3000` is 30,00 DH. Never floats,
  never `DECIMAL` in a column that JavaScript will read.
- Format only at render time, with `formatDH()` from `web/src/lib/format.ts`.
- Every balance change is a row in `credit_transactions`. Never `UPDATE` a balance
  without writing the ledger row in the same transaction.

**Design**
- Never hardcode a colour, font size, radius or spacing value. Use the Tailwind
  tokens defined from `web/src/ui/theme.ts`.
- Both light and dark must work. Check every new screen in both.
- One primary button per screen.
- Motion only when something real changes.

**Language**
- No hardcoded user-facing strings, on either side. Every string is an i18n key.
  The API returns machine-readable error **codes**, never sentences to display.
- Three languages: `ar` (default, RTL), `fr`, `en`.
- Use logical CSS properties: `ms-*`/`me-*`, never `ml-*`/`mr-*`; `text-start`,
  never `text-left`.
- Numbers, prices and phone numbers stay Latin digits and LTR in all three
  languages. Never build a sentence by concatenation — use interpolation.
- **The `numeric` class goes on the number, never on a line that also holds
  words.** It sets `direction: ltr`, so an element carrying both a translated
  label and a number lays the whole line out left to right — in Arabic that
  turned `07 55 00 00 01` into `01 00 00 55 07`, and it is invisible in French.
  Wrap the value: `{t('phone')}: <span className="numeric">{number}</span>`.

**Database**
- Never edit a migration that has been committed. Add a new one.
- Every foreign key gets an explicit `ondelete`. Decide, don't default.
- Times are stored UTC, `DATETIME`, and converted at the edge.
- Phone numbers are stored E.164: `+212XXXXXXXXX`. One format, everywhere.

**Quality**
- Every list screen handles four states: loading skeleton, empty, error with retry,
  and data.
- No `any`, no `# type: ignore`, no `@ts-ignore`.
- Destructive actions (cancel a request, reject an offer, suspend a user) confirm
  first.
- Every admin or moderator action that changes another user's state writes an
  `audit_log` row. No exceptions.

## Do not

- Do not add a UI component library. `web/src/ui` is the design system.
- Do not add a state manager beyond TanStack Query + Zustand.
- Do not touch anything outside Brikole's own tree.
- Do not commit secrets. Everything goes through `.env`, and `.env.example` is the
  template.
- Do not scaffold screens that aren't in `docs/SCREENS.md` without asking.

## Build order

Phase 0 (current): schema + migrations → auth + the 4 roles → design system + i18n.
Phase 1: client posts a request → tradesman feed → offers → accept.
Phase 2: job lifecycle → reviews → lead fee → credit top-up.
Phase 3: moderator disputes → admin approvals, settings, statistics.
Phase 4: chat, fixed-price catalogue, SMS OTP, online payment.

Screen IDs used in commits (`C1`, `M4`, `D2`, `A5`…) come from `docs/SCREENS.md`.

## Working style

- Small commits, one screen or one concern each.
- Before building a screen, re-read its entry in `docs/SCREENS.md` and list the
  states you will implement.
- When the spec is ambiguous, ask rather than guess.
