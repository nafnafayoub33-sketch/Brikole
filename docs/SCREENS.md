# Screens — full specification

Every screen lists: **Purpose** · **Contents** · **Actions** · **States** · **Goes to**.
Screen IDs (`C1`, `M4`, `D2`, `A5`…) are used in commit messages.

URLs are Latin and untranslated — they are technical identifiers, not user-facing
strings. Everything a human reads is an i18n key.

---

## Navigation

**Public** — top bar: logo · **search box** · *Become a m3allem* · theme · language ·
**profile icon** · *Create account*. There is no standalone sign-in button: the
profile icon is the one place "me" lives, and it carries sign-in when signed out
and the account when signed in. Under it, the **trade strip** — the site's real
navigation, scrolling sideways rather than wrapping.

The search lands on P2 with the term in the URL (`/services?q=…`), so a result is
shareable, bookmarkable and survives a reload.

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

### P2 · Browse — `/services` and `/services/:slug`
- **Contents:** the same screen with and without a trade. `/services` lists every
  approved tradesman in the chosen city; `/services/:slug` narrows it to one trade
  and adds its name and description. Cards carry cover, name, city, headline,
  rating, jobs done and the starting price — the same card the home page uses.
  A permanent *Describe your job* card sits in the grid.
- **Sorting:** best rated (default) · most jobs · cheapest to start · newest
- **The whole state is in the URL** — term, trade, sort, page — and changing any
  of them resets the page, because page 4 of a different search is not somewhere
  anybody meant to be.
- **Search matches** a tradesman's name, his headline, and his trades in all three
  languages: whoever types `سباك` means the same as whoever types `plombier`.
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
  come. Sortable by price, rating, soonest — sorted on the page, not by a round
  trip, because it is a decision he changes three times in a row.
- **Every offer is listed, including the withdrawn and the rejected.** C2 shouts
  an offer count; a list that quietly drops some of them makes that number a lie,
  and a closed request is also the record of who answered and who he did not pick.
- **The address is on the page but the note under it says who else sees it** —
  only the tradesman whose offer he accepts. Nothing on a screen should leave him
  guessing what he has just published.
- **Actions:** accept an offer (confirms, and says plainly that the others will be
  declined) · decline one · cancel the request (confirms) · edit while no offer
  has arrived
- **Declining one is its own action**, not a side effect of accepting another. A
  client who knows a price is wrong should be able to clear it out of his list,
  and a tradesman is better off learning it now than sitting in a queue that has
  silently moved past him.
- **Editing stops the moment the first offer arrives**, and the screen says why
  rather than hiding the button. A tradesman priced the job as it was written;
  changing it under his quote turns a 450 DH answer to "unblock a sink" into an
  answer to "retile the bathroom". After that, the way to change the work is to
  cancel and post again — which costs the client nothing and costs the tradesmen
  their guess.
- **Editing reuses C1's wizard** rather than a second form, pre-filled from the
  request. It never touches C1's saved draft: that draft belongs to a request
  being written, and loading an existing one into it would silently eat that work.
- **States:** loading · no offer yet ("Tradesmen are being notified — offers usually
  arrive within a few hours") · request cancelled · request already assigned
  (offers become read-only) · accept failed because someone else's offer was
  withdrawn
- **Accepting is one transaction.** The offer becomes accepted, every other
  pending offer on the request is declined in the same breath, the request goes
  to `assigned`, the job is created, and the lead fee is charged to the
  tradesman with its ledger row — or none of it happened. The button says out
  loud what it does to the offers he is not choosing, because it is the one
  press in the client's flow he cannot take back.
- → C4

### C4 · Job — `/client/jobs/:id`
- **Contents:** status timeline (accepted → started → finished → confirmed), the
  tradesman with **his phone number, revealed here and nowhere else**, the agreed
  price, the address, and a reminder that payment is cash and direct
- **Actions:** call · confirm the work is done · cancel with a reason · open a
  dispute
- **States:** each timeline state · cancelled by the tradesman (with his reason) ·
  awaiting your confirmation (the primary action) · auto-confirmed after 7 days
- **A short balance never blocks the client.** If the accepted tradesman cannot
  cover the lead fee, the balance is allowed to go negative and the debt is
  recorded: the client pressed the button, he cannot see or fix the tradesman's
  wallet, and refusing there would break the only flow that earns the platform
  anything. The guard belongs upstream — M5 refuses to send an offer without
  credit — so a shortfall here is the narrow case where the fee changed, or the
  balance was spent, between the offer and its acceptance.
- **The tradesman's phone number appears here and nowhere earlier.** Before an
  offer is accepted nobody has agreed to anything.
- **Who may move it where is not symmetric.** The tradesman starts and finishes;
  the client confirms. Neither owns the other's arrow, and a client cannot cancel
  once the work is done — that is what C8 is for.
- → C5, C8

### C5 · Rate — `/client/jobs/:id/review`
- **Contents:** 1–5 stars, optional comment, optional photos of the result
- **One question and one optional box.** Every field added here costs reviews,
  and a marketplace with no reviews is a directory. Photos of the result are not
  built for that reason — they can be added once the ratings are arriving.
- **The rating recomputes the profile it is about**, from the reviews, never by
  incrementing an average: that is how a profile ends up claiming 4.9 over a page
  of three-star reviews.
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
- **The "this is not a refund" paragraph comes before the form**, not after
  submission. Somebody arriving here expecting the job price back leaves angrier
  than he came, and telling him at the end is too late.
- **The link to this screen lives on C4 for as long as the API allows a dispute**
  — including on a confirmed job, which is when the argument usually starts. The
  window itself is the API's to enforce; the screen does not duplicate the number
  and drift from it.
- **States:** already open · outside the 7-day window
- → D1's queue

---

# 3. M3allem — `/pro`

Owner-facing controls are large: these are tapped on a phone, outdoors, sometimes
with wet or dirty hands. Minimum touch target 52px.

### M1 · Become a m3allem — `/pro/onboarding` ⭐
- **Contents:** four steps, with a **live preview** of the profile card beside
  them — filling in a form without seeing what it produces is how somebody ends
  up writing "plombier" in a field labelled *your service in one line*.
  1. **Trades** — one to five, from the same grid as C1
  2. **Where** — city, and a radius in km
  3. **Who you are** — headline, description, years of experience, optional
     starting price, optional photo, and the **CIN photo**
  4. **Your work** — up to 10 portfolio photos
- **The CIN is private.** It goes to the private bucket, it is readable only by
  its owner and an admin, and the screen says so where he uploads it. It never
  appears on P3.
- **Actions:** next / back / submit for approval. *Next* is disabled until the
  step is complete, and step 3 is not complete without the CIN — it is the one
  thing an admin's review is actually about.
- **States:** per-step validation · uploading, with the preview drawn from the
  file the browser already has · submitted · submit failed with retry
- → M2

### M2 · Approval status — `/pro/status`
- **Contents:** pending ("usually under 24h"), or rejected with the admin's
  reason spelled out and a button back to M1, or approved with a link to his
  public profile
- **Routing:** `/pro` reads the profile and decides — no application sends him
  to M1, pending or rejected to M2, approved to his dashboard. The *absence* of
  a profile is the signal, so a tradesman who registered and closed the tab
  lands back on the form rather than on an empty dashboard.
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
- **The credit gate is on this page too, not only on the feed.** M4 closing is
  not enough: he reaches M5 by a URL, a stale link or the back button, and a
  page that lets him write a price and refuses only on send is precisely what
  closing the feed was meant to prevent.
- **Withdrawing therefore also lives on M6.** His offer outlives his credit, and
  an offer he can no longer edit is one he must still be able to take back.
- → M6

### M6 · My offers — `/pro/offers`
- Grouped: awaiting an answer, accepted, declined, expired. Each shows the request
  and the price offered.
- **States:** loading · empty · error with retry

### M7 · My jobs — `/pro/jobs`
- **Contents:** assigned / in progress / finished, each with the client's name,
  **phone**, address, agreed price
- **Full cards, not a list that opens a detail.** He is standing outside with one
  hand free: the address and the phone number are the two things he must not have
  to tap twice for. Buttons are 52px for the same reason.
- **Actions:** *Start* → in progress · *Finished* → done · cancel with a mandatory
  reason — the button refuses a blank one before the API does, so he is not told
  off after pressing.
- **Note:** cancellation rate is tracked. It is shown to him honestly on this screen
  before it ever becomes a suspension.
- **He is shown what the lead cost him** on each job, or that it was a free one.

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
- **One pending claim at a time.** A second is almost always him thinking the
  first did not go through, and it is two rows an admin has to reconcile against
  one bank statement.
- **Every amount is shown as the jobs it buys.** "500 DH" means nothing to a
  tradesman deciding how much to transfer; "50 jobs" means everything.
- **The reference is mandatory** — it is what an admin types into a statement
  search, and without it A5 is a list of claims nobody can check.
- The receipt goes to the private bucket, like the CIN: it has an account number
  on it.

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
- **Oldest first**, and unclaimed for over 48 hours is flagged: two people are
  waiting on every row, and a queue where everything looks equally urgent is not
  a queue.
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
- **The refund is legal on one verdict only** — client at fault. The fee bought a
  real introduction to a real job; it comes back when the person who wasted it
  was on the other side, and not as a way of splitting the difference. The tick
  is locked on every other verdict and clears if he switches away from it, so a
  stale tick never reaches an API that would reject it.
- **Internal notes are filtered in the service**, not in this screen: a note a
  moderator wrote about somebody must not be one forgotten `if` away from that
  person reading it.
- **Both parties read the same case**, minus the lead fee, the internal notes and
  the decision panel — passed in as a prop rather than decided by a role check
  inside the component, so a party's copy cannot grow moderator powers.
- **States:** unclaimed (read-only until claimed) · already resolved (read-only with
  who decided and when) · a party has been deleted

### D3 · Reports — `/mod/reports`
- Reported profiles and reviews. Actions: dismiss, hide the content, warn,
  suspend 48h. Anything heavier is escalated to an admin.
- **The ceiling is in the vocabulary, not remembered in code.** `ReportOutcome`
  has four values and none of them closes an account; a moderator cannot reach
  one because there is nothing to reach.
- **The content is quoted on the card.** A moderator judges the thing complained
  about, not the complaint about it.
- **Only a review can be hidden.** A profile is not a piece of content: taking a
  tradesman off the market is a suspension, and calling it "hidden" would leave
  nothing on the record saying why he vanished.
- **Nobody reports their own content**, and nobody files the same complaint
  twice — the second is the same complaint, and staff act rather than queue one
  for themselves.
- **"Other" requires a sentence.** Every other reason carries its own meaning;
  that one carries none, and a moderator cannot act on it.
- Other open reports on the same target are counted on the card: three
  complaints about one review is a different decision from one.
- **States:** loading · empty ("Nothing to review") · error with retry ·
  already handled by another moderator → 409 rather than a second suspension.
- Handling writes an `audit_log` row with the outcome and the reason.

### D4 · Account — `/mod/account`

---

# 5. Admin — `/admin`

### A1 · Dashboard — `/admin`
- One hero figure — what the platform took, all of it lead fees — over a row of
  stat tiles: new sign-ups this week against last week, tradesmen awaiting
  approval, open disputes, open requests, jobs done. Numbers, not charts: a
  one-bar chart of "1 dispute" says less than the number does.
- The two tiles that are somebody waiting (approvals, disputes) carry a status
  colour, and only while there is something to do. The colour never says it
  alone — each carries the words beside it.
- A tile links to its screen only when that screen exists. Approvals and
  disputes do; sign-ups and open requests get theirs with A3 and A4.
- Every figure is counted live at read time. Nothing here is a stored total, so
  nothing here can drift away from the tables it claims to describe.

### A2 · Approvals — `/admin/approvals` ⭐
- **Contents:** the queue on one side, the application on the other. The detail
  shows everything from M1 — headline, description, trades, experience, starting
  price, portfolio — and the **CIN photo**, which is what the review is about.
- **Oldest first.** It is a queue: the person who has waited longest is next.
- **The CIN is fetched with the admin's token**, not pointed at by an `<img src>`
  — an image element sends cookies but no Authorization header, so the bytes are
  pulled and handed over as an object URL, revoked when the admin moves on.
- **Actions:** approve · reject with a reason the tradesman will read at M2. Both
  confirm first, and a rejection with no reason is refused — the reason is the
  only thing M2 can tell him to fix.
- **States:** loading · empty ("nothing waiting") · error with retry · **already
  handled by another admin** → the API answers 409 and the screen says so rather
  than overwriting a decision that has already been sent.
- Writes an `audit_log` row either way, carrying the status before and after and,
  for a rejection, the reason.

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
- **Oldest first.** It is a queue: the tradesman who has waited longest is next,
  and he is blocked from working until somebody looks.
- **Two admins on one queue** get a 409 on the second approval rather than a
  balance credited twice.
- Both actions write an `audit_log` row carrying the balance before and after.
- **States:** loading · empty · approve failed because it was already handled

### A6 · Trades and cities — `/admin/catalog`
- CRUD on trades (name in three languages, icon, `lead_fee_centimes`, active) and
  cities. Deactivating a trade hides it from C1 and stops its feed; it never deletes
  history.

### A7 · Settings — `/admin/settings`
- Default lead fee, free leads for a new tradesman, request cap per client, offer
  expiry, dispute window, the platform's bank details shown at M9, and maintenance
  mode. Every change is audited with the old and the new value.
- **Every value is bounded in `core/settings_rules.py`**, not trusted. A lead fee
  of zero makes the business free and a request cap of zero makes the product
  unusable — both are one mistyped digit away on this form.
- **A bad value rejects the whole batch.** Saving three fields and refusing the
  fourth leaves the admin guessing which of them landed.
- **A partial write only touches the keys it was sent**, so two admins editing
  different halves of the screen do not overwrite each other.
- **Writing the same value is not a line in the log.** An audit trail padded with
  no-ops is one nobody reads.
- A key nobody has ever changed shows as the shipped default rather than
  implying somebody chose it.

### A8 · Audit log — `/admin/audit`
- Who did what to whom and when, filterable by actor, action and target. Read-only,
  and never deletable from the UI.
- **Read-only by construction:** the API has no write and no delete on this path,
  so there is nothing for the screen to offer even if somebody wanted it.
- **The filters are built from what the log contains**, so a choice never returns
  nothing because the screen invented the option.
- **A deleted actor takes his name, not his record** — the row survives with the
  account marked gone, which is the entire point of an audit log.
- Object-valued settings are diffed key by key rather than printed as two JSON
  blobs, on the one screen whose whole job is being readable.

### A9 · Staff — `/admin/staff`
- Moderators and admins, what they have handled, and deactivation.

---

# 6. Shared

### S1 · Not found — `*`
### S2 · No permission — shown when a route does not match the role, with a link to that role's home. Never a blank page.
### S3 · Suspended — replaces the whole app for a suspended account, with the reason and until when.
### S4 · Maintenance — when A7's switch is on. Admins still get in.
