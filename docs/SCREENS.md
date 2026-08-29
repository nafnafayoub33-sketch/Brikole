# Screens — full specification

Every screen lists: **Purpose** · **Contents** · **Actions** · **States** · **Goes to**.
Screen IDs (`C1`, `M4`, `D2`, `A5`…) are used in commit messages.

URLs are Latin and untranslated — they are technical identifiers, not user-facing
strings. Everything a human reads is an i18n key.

---

## Navigation

**Public** — top bar: logo · trades menu · "How it works" · language switcher ·
*Sign in* · *Become a m3allem*.

**Client** — top bar: *New request* (primary) · My requests · Notifications (badge) ·
avatar menu (profile, language, sign out).

**M3allem** — top bar: Requests · My offers · My jobs · Credit (shows the balance) ·
Notifications (badge) · avatar menu. The balance is in the bar on purpose: it is the
thing that stops him working when it hits zero.

**Moderator** — side rail: Disputes · Reports · Account.

**Admin** — side rail: Dashboard · Approvals · Users · Requests & jobs · Finance ·
Trades & cities · Settings · Audit log.

---

# 1. Public — no account needed

### P1 · Landing — `/`
- **Purpose:** explain the thing in five seconds and start a request
- **Contents:** hero with a *what* field and a **city select** side by side, grid of
  trades with icons, "how it works" in three steps, a strip for tradesmen with the
  value proposition and a *Become a m3allem* button
- **The city is half the question, not a filter.** It sits in the search bar, and
  everything below is counted inside it: each trade tile shows how many approved
  tradesmen work in that trade **in that city**, and says "nobody yet" when the
  answer is none. A national count would tell somebody in Meknès that forty
  plumbers are available when every one of them is in Casablanca.
- The choice is remembered between visits, and the "most asked for" chips are
  ordered by who is actually available there.
- **Actions:** search · pick a city · pick a trade · sign in · register
- **States:** loading skeleton for the trade grid · trades failed to load (retry) ·
  a trade with nobody in this city (shown, with zero, never hidden)
- → P2, P4, P5

### P2 · Trade page — `/services/:slug`
- **Contents:** trade name and description, city filter, list of approved tradesmen
  (photo, name, rating, jobs done, city), and a permanent *Describe your job* card
- **Actions:** filter by city · open a profile · start a request
- **States:** loading · no tradesman in this city yet (still offer to post the
  request — it is how the marketplace fills) · error with retry
- → P3, C1

### P3 · Tradesman profile — `/brikole/:id`
- **Contents:** photo, name, trades, city and radius, bio, portfolio gallery, rating
  with review count, jobs done, member since, reviews list
- **Actions:** *Ask this m3allem* (pre-fills C1 with his trade)
- **States:** loading · not found · suspended profile → 404, not a message
- **Never shows:** phone number. Contact details appear only after an accepted offer.
- → C1

### P4 · Sign in — `/login`
- **Contents:** phone field with a fixed `+212`, password, "forgot password"
- **Actions:** sign in
- **States:** wrong credentials · account locked (5 attempts → 15 minutes) ·
  account suspended · offline
- → the app, by role

### P5 · Register — `/register`
- **Contents:** two cards — *I need a job done* / *I am a m3allem* — then phone,
  full name, password, terms
- **Important:** only `client` and `provider` can be self-registered. The API
  rejects anything else; it is not merely hidden in the form.
- **States:** number already registered · weak password · invalid number
- → client: C2 · m3allem: M1

### P6 · Forgot password — `/forgot`
- Phase 4 — needs SMS. Until then the screen explains that an admin resets it.

---

# 2. Client — `/client`

### C1 · New request — `/client/requests/new` ⭐
- **Purpose:** the single most important screen in the product
- **Contents:** four steps with a progress bar
  1. **Trade** — grid, searchable
  2. **The job** — title, description, up to 6 photos
  3. **Where and when** — city, address, optional map pin, urgency (today / this
     week / flexible)
  4. **Budget and review** — optional budget range, then a summary of everything
- **Actions:** next / back / publish
- **States:** per-step validation · uploading photos with progress · draft kept if
  the browser is closed · already has 3 open requests (the cap) · publish failed
  with retry
- → C3

### C2 · My requests — `/client/requests`
- **Contents:** cards grouped by status — open (with the offer count as the loudest
  element), assigned, done, cancelled
- **Actions:** open · cancel (confirms) · new request
- **States:** loading skeleton · empty ("You have no request yet" + primary CTA) ·
  error with retry · data
- → C3, C4

### C3 · Request and its offers — `/client/requests/:id` ⭐
- **Contents:** the request as published; below it the offers, each with the
  tradesman's photo, name, rating, jobs done, **price**, message, and when he can
  come. Sortable by price, rating, soonest.
- **Actions:** accept an offer (confirms, and says plainly that the others will be
  declined) · decline one · cancel the request · edit while no offer has arrived
- **States:** loading · no offer yet ("Tradesmen are being notified — offers usually
  arrive within a few hours") · request cancelled · request already assigned
  (offers become read-only) · accept failed because someone else's offer was
  withdrawn
- → C4

### C4 · Job — `/client/jobs/:id`
- **Contents:** status timeline (accepted → started → finished → confirmed), the
  tradesman with **his phone number, revealed here and nowhere else**, the agreed
  price, the address, and a reminder that payment is cash and direct
- **Actions:** call · confirm the work is done · cancel with a reason · open a
  dispute
- **States:** each timeline state · cancelled by the tradesman (with his reason) ·
  awaiting your confirmation (the primary action) · auto-confirmed after 7 days
- → C5, C8

### C5 · Rate — `/client/jobs/:id/review`
- **Contents:** 1–5 stars, optional comment, optional photos of the result
- **Actions:** publish · skip
- **States:** already rated (read-only) · submitting · failed with retry
- → C2

### C6 · Notifications — `/client/notifications`
- Offer received · offer about to expire · tradesman on his way · work finished,
  please confirm · dispute answered. Read/unread, mark all read.

### C7 · Account — `/client/account`
- Name, photo, phone (read-only — it is the identity), city, language, change
  password, sign out, delete account (confirms twice, and refuses while a job is
  running).

### C8 · Open a dispute — `/client/jobs/:id/dispute`
- **Contents:** reason from a fixed list (never came, work not done, damage, price
  disagreement, behaviour), description, evidence photos
- **Important:** the platform holds no money, so this is never a refund request.
  The screen says so before submission.
- **States:** already open · outside the 7-day window
- → D1's queue

---

# 3. M3allem — `/pro`

Owner-facing controls are large: these are tapped on a phone, outdoors, sometimes
with wet or dirty hands. Minimum touch target 52px.

### M1 · Become a m3allem — `/pro/onboarding` ⭐
- **Contents:** four steps
  1. **Trades** — one or more, from the same grid as C1
  2. **Where** — city and a radius in km
  3. **Who you are** — bio, years of experience, CIN photo (private, never public)
  4. **Your work** — up to 10 portfolio photos
- **Actions:** submit for approval
- **States:** per-step validation · uploading · submitted · submit failed with retry
- → M2

### M2 · Approval status — `/pro/status`
- **Contents:** pending ("usually under 24h"), or rejected with the admin's reason
  spelled out and an edit button
- **Actions:** resubmit after fixing
- → M3 once approved

### M3 · Dashboard — `/pro`
- **Contents:** balance and free leads left (loudest element, and red under one
  lead), new matching requests count, offers awaiting an answer, jobs in progress,
  rating
- **States:** loading · out of credit → a full-width banner "Top up to keep
  receiving jobs" · not yet approved → redirect to M2

### M4 · Request feed — `/pro/requests` ⭐
- **Contents:** open requests matching his trades and inside his radius. Each row:
  trade, title, city and distance, urgency, budget if given, how long ago, and how
  many offers already exist
- **Actions:** filter by trade and urgency · open
- **States:** loading skeleton · empty ("No request in your trades right now — widen
  your radius or add a trade" with both as buttons) · error with retry ·
  **out of credit → the feed is replaced by the top-up call to action.** He is not
  shown work he cannot take.
- → M5

### M5 · Request detail and offer — `/pro/requests/:id` ⭐
- **Contents:** the full request with photos, the approximate area (**never the
  exact address before acceptance**), and the offer form: price, message, when he
  can come
- **Actions:** send the offer (confirms, and states the lead fee that will be
  charged **if the client accepts** — never at this moment) · withdraw an offer
- **States:** already offered (form becomes the current offer, editable) · request
  taken by someone else · request cancelled · insufficient credit → blocked with
  the top-up CTA
- → M6

### M6 · My offers — `/pro/offers`
- Grouped: awaiting an answer, accepted, declined, expired. Each shows the request
  and the price offered.
- **States:** loading · empty · error with retry

### M7 · My jobs — `/pro/jobs`
- **Contents:** assigned / in progress / finished, each with the client's name,
  **phone**, address, agreed price
- **Actions:** *Start* → in progress · *Finished* → done · cancel with a mandatory
  reason
- **Note:** cancellation rate is tracked. It is shown to him honestly on this screen
  before it ever becomes a suspension.

### M8 · My profile — `/pro/profile`
- Trades, city, radius, bio, portfolio, availability. Editing trades or city takes
  effect on the feed immediately.

### M9 · Credit — `/pro/credit`
- **Contents:** balance, free leads left, the transaction ledger (date, type,
  amount, what it was for), and a top-up panel
- **Top-up:** pick an amount, see the platform's bank details, transfer, then submit
  the reference and a photo of the receipt. **The balance does not move until an
  admin approves it,** and the screen says so.
- **States:** loading · empty ledger · a pending top-up (shown at the top with its
  submitted date) · rejected top-up with the admin's reason

### M10 · Reviews — `/pro/reviews`
- Rating breakdown and the reviews themselves. He may reply once to each.

### M11 · Account — `/pro/account`
- Same as C7, plus notification preferences per trade.

---

# 4. Moderator — `/mod`

### D1 · Disputes — `/mod/disputes` ⭐
- **Contents:** queue with tabs — open, assigned to me, resolved. Each row: job,
  reason, who opened it, age (over 48h is flagged)
- **Actions:** claim · open
- **States:** loading · empty ("Nothing to arbitrate") · error with retry

### D2 · Dispute — `/mod/disputes/:id` ⭐
- **Contents:** the job, both parties with their history (jobs done, rating, past
  disputes), each side's statement and evidence, and a message thread the moderator
  can write in
- **Actions:** ask a party for more detail · decide: **client at fault / m3allem at
  fault / no fault** · then the outcome: warn, suspend for 48h, refund the lead fee
  to the tradesman
- **Important:** the moderator sees the **lead fee** because he can refund it, and
  nothing else about money — no balance, no top-up, no revenue.
- **States:** unclaimed (read-only until claimed) · already resolved (read-only with
  who decided and when) · a party has been deleted

### D3 · Reports — `/mod/reports`
- Reported profiles, reviews and messages. Actions: dismiss, hide the content, warn,
  suspend 48h. Anything heavier is escalated to an admin.

### D4 · Account — `/mod/account`

---

# 5. Admin — `/admin`

### A1 · Dashboard — `/admin`
- New users this week, tradesmen awaiting approval, open requests, jobs done,
  leads sold and their value, disputes open. Every tile links to its screen.

### A2 · Approvals — `/admin/approvals` ⭐
- **Contents:** queue of pending tradesmen; the detail shows everything from M1
  including the CIN photo
- **Actions:** approve · reject with a reason the tradesman will read at M2
- **States:** loading · empty · already handled by another admin (refresh and say so)
- Writes an `audit_log` row either way.

### A3 · Users — `/admin/users`
- Search by phone or name, filter by role and status. The detail shows the account,
  its activity, and its disputes.
- **Actions:** suspend · reactivate · **change role** (the only place a role can
  change) · create a moderator or an admin
- All of it confirmed, all of it audited.

### A4 · Requests and jobs — `/admin/requests`
- Read-only browser with filters, for support questions. Cancelling a request from
  here is possible and audited.

### A5 · Finance — `/admin/finance` ⭐
- **Tabs:** top-up requests (approve/reject with the receipt visible), the credit
  ledger across all tradesmen, and revenue by period and by trade
- **Approving a top-up** credits the balance and writes the ledger row in one
  transaction. Rejecting moves nothing and records a reason.
- **States:** loading · empty · approve failed because it was already handled

### A6 · Trades and cities — `/admin/catalog`
- CRUD on trades (name in three languages, icon, `lead_fee_centimes`, active) and
  cities. Deactivating a trade hides it from C1 and stops its feed; it never deletes
  history.

### A7 · Settings — `/admin/settings`
- Default lead fee, free leads for a new tradesman, request cap per client, offer
  expiry, dispute window, the platform's bank details shown at M9, and maintenance
  mode. Every change is audited with the old and the new value.

### A8 · Audit log — `/admin/audit`
- Who did what to whom and when, filterable by actor, action and target. Read-only,
  and never deletable from the UI.

### A9 · Staff — `/admin/staff`
- Moderators and admins, what they have handled, and deactivation.

---

# 6. Shared

### S1 · Not found — `*`
### S2 · No permission — shown when a route does not match the role, with a link to that role's home. Never a blank page.
### S3 · Suspended — replaces the whole app for a suspended account, with the reason and until when.
### S4 · Maintenance — when A7's switch is on. Admins still get in.
