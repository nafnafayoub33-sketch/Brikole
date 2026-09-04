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
- **Actions:** open the chat on an offer (→ C9; commits to nothing) · decline one ·
  cancel the request (confirms) · edit while no offer has arrived
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
- **There is no accept button any more.** Tapping an offer opens C9, where the
  two of them talk and settle on a price. The job is created when they have
  **both** signed the same terms — see C9 — so nothing on this screen is
  irreversible and nobody is charged for a press.
- → C9

### C4 · Job — `/client/jobs/:id`
- **Contents:** status timeline (accepted → started → finished → confirmed), the
  tradesman with **his phone number, revealed here and nowhere else**, the agreed
  price, the address, and a reminder that payment is cash and direct
- **Actions:** call · confirm the work is done · cancel with a reason · open a
  dispute
- **States:** each timeline state · cancelled by the tradesman (with his reason) ·
  awaiting your confirmation (the primary action) · auto-confirmed after 7 days
- **A short balance never blocks the deal.** If the tradesman cannot cover the
  lead fee when the second signature lands, the balance goes negative and the
  debt is recorded: two people have just agreed on a price, and refusing there
  would break the only flow that earns the platform anything. The guard belongs
  upstream — M5 refuses to send an offer without credit — so a shortfall here is
  the narrow case where the fee changed, or the balance was spent, while they
  were talking.
- **The tradesman's phone number appears here and nowhere earlier.** Not on P3,
  not on C3, and not in the chat that led here — C9 strikes contacts out of
  every message until this screen exists. Before both have signed, nobody has
  agreed to anything and the platform has not been paid.
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

### C9 · Chat with a tradesman — `/client/requests/:id/chats/:conversationId` ⭐
The screen the business model lives on. M12 is the same thread from the other
side, and the same component draws both.

- **Opening it commits to nothing.** No offer changes status, no request is
  assigned, no money moves. The client can open one on every offer he has and
  close none of them.
- **No phone number, no email, no link.** Numbers, emails, links and `@handles`
  are struck out of every message in both directions — including numbers spelled
  in words, in French or Darija, and typed in Arabic-Indic digits. The message
  is still delivered with the contact struck out: refusing it outright would
  teach people to write `zero six` and lose the sentence around it. The struck
  contact is **never stored**; only a count of how many were removed, which is
  what a moderator reads as somebody trying repeatedly.
- **Nobody is refused and nobody is charged for trying.** He types his number,
  the message goes, and the number is not in it. A 402 in the middle of a
  conversation two people are having in good faith is a paywall, and refusing
  the message outright only teaches him to write `zero six`. One banner states
  the rule, worded the same to both of them.
- **Quiet is not secret.** The bubble says a contact was removed, to the person
  who sent it as much as to the person who did not get it. Without that he
  waits for a call that was never coming, and blames the client.
- **What the platform does instead is count.** Past `contact_flag_threshold`
  *different clients* (default 10) it files a report on the tradesman's profile
  and staff decide at D3. Nothing happens to him here — no suspension, no fee,
  no message he can see. A person is only being asked to look.
- **Counted in clients, never in messages.** Writing his number four times to
  one man who is not replying is persistence. The pattern that matters is the
  same move made to stranger after stranger.
- **The client is not counted.** She is not the one who would take the work off
  the platform, and her half of this rule exists to protect her, not to police
  her.
- **What must not fire.** `prix 2000dh`, `1500 2000 2500 3000 dh`, `rab3a d
  nhar`, `2 m x 3 m` and a date are ordinary talk. A rule that eats prices is
  switched off within a week, and a tradesman quoting a list must never learn
  to distrust the box.
- **This is a deterrent, not a wall.** Somebody determined can photograph a
  business card. The wall is structural and elsewhere: the tradesman's phone
  number is on the job payload and on nothing that exists before one.
- **The deal card** carries the price and what it covers, and the two
  signatures. Either side may move either field; **every change clears both
  signatures, including the changer's own**, so nobody is ever held to a number
  he did not see.
- **A signature is against a version, not against "the deal".** Signing a
  version that has moved is refused rather than silently upgraded — the screen
  he pressed on was showing a different price.
- **The second signature is the acceptance**, and it is the same single
  transaction the old button was: the offer wins, every other pending offer is
  declined, the request goes to `assigned`, the job is created **at the price
  they agreed**, and the lead fee is charged with its ledger row — or none of it
  happened.
- **Messages carry photos and documents** (JPEG, PNG, WebP, PDF) in the private
  bucket, readable only by the two people in that conversation — membership is
  asked of the database, never inferred from the folder name.
- **Once the job exists the redaction stops.** The platform has been paid and
  they have each other's number on C4; striking one out here would be
  superstition.
- **Looking at the thread is what marks it read**, and the newest message is
  what "looked at" means — so it fires again when one arrives while the screen
  is open, not only when it mounts.
- **States:** loading · empty thread · talking · one signature · both signed
  (the deal card is replaced by a link to the job) · the offer was withdrawn
- → C4

### M12 · Chat with a client — `/pro/chats/:conversationId` ⭐
The same thread as C9, from the tradesman's side, drawn by the same component.

- **He cannot start one.** The client chooses who to talk to; an unsolicited
  thread from every tradesman who saw the request is a spam channel. M6 links
  into the thread once the client has opened it, and says "no reply yet" when
  he has not.
- **The nav tells him.** He sent an offer and went back to work, so a count of
  unread threads rides on *Mes offres* — and on *Mes demandes* for the client.
  A thread he has never opened counts, which is the case the badge exists for:
  a client tapping his offer writes only a system line, and a rule that watched
  for messages from the other side would stay silent on exactly that.
- **He is the one being counted**, and he is not told so on this screen. The
  banner states the rule; a running tally beside it would read as a threat to
  the twenty tradesmen who will never come near the line, to deter the one who
  will anyway.
- The rest is C9: the same deal card, the same two signatures, the same rule
  about contacts, and the same second signature that creates the job and
  charges him the lead fee — at the price he actually agreed to, not the one he
  guessed before seeing the photos.

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
- **Some reports have no reporter.** The platform files one itself when a
  tradesman has tried to hand his number to more than `contact_flag_threshold`
  different clients in the chat. The card says "flagged automatically —
  nobody complained" rather than showing a dash where a name goes: an absent
  name is not missing data, it is the finding. The count travels as a number
  and the sentence around it is written on the screen, in the language the
  moderator reads.
- **The platform files it once.** While one is open, another is not new
  information, and a queue with the same man in it forty times is a queue
  nobody reads.
- **States:** loading · empty ("Nothing to review") · error with retry ·
  already handled by another moderator → 409 rather than a second suspension.
- Handling writes an `audit_log` row with the outcome and the reason.

### D4 · Account — `/mod/account`

---

# 5. Admin — `/admin`

### A1 · Dashboard — `/admin`
One hero figure, a row of stat tiles, then four panels that answer the questions
the tiles raise.

- **The headline row.** What the platform took, all of it lead fees, as the one
  figure the view leads with; then new sign-ups this week against last week,
  tradesmen awaiting approval, open disputes, open requests, jobs done.
- **Where the money is.** The price of the jobs under dispute — *between a
  client and a tradesman, never on the platform's books; there is no escrow
  before phase 3* — kept apart from the lead fees charged on those same jobs,
  which is the platform's own exposure and refundable by a moderator. Then
  top-ups waiting for A5, credit bought and not spent, and the debt carried by
  tradesmen whose wallet went under. Every row says whose money it is.
- **Revenue month by month.** Thirteen months, so the same month last year is on
  the chart. Quiet months are drawn as quiet months, never dropped.
- **Cities and trades.** Jobs done and money taken, ranked. Past about seven
  categories colour stops carrying identity, so this is a table with the bar
  drawn in it — and the tail it does not show is named and totalled rather than
  quietly dropped.
- **From request to finished work.** Published → answered → hired → confirmed.
  The one panel that says whether the marketplace works: a request nobody
  answers is the failure the platform exists to prevent.

Rules this screen keeps:
- Numbers where a number is the answer, charts only where the shape is. One
  measure per chart, one hue, no second y-axis, and no bar coloured by its own
  value — length already says how much.
- Ordered steps (the funnel) take a one-hue ordinal ramp; nominal categories
  (cities, trades) all take the same hue.
- The trend is pinned left-to-right in Arabic. Time is a number line, and this
  codebase already keeps numbers, prices and dates reading that way.
- Status colour only where somebody is waiting, and never alone — the words are
  in the badge beside it.
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

### A3 · Users — `/admin/users` ⭐
The screen with the most power on the platform. The list on one side, the account
on the other; the list scrolls inside itself and pages, so the detail — the thing
being read — never leaves the screen.

- **Finding somebody.** One box for a name or a phone. Numbers are stored E.164
  and typed nationally, so `0612…` finds `+212612…`. Filters for role and status;
  deleted accounts stay out unless asked for by name.
- **The detail.** The account, then what it has done on *both* sides of the
  marketplace — requests posted, tradesmen hired, money spent, reviews written,
  offers sent, jobs worked — because a client and a tradesman are the same row and
  a zero is a fact worth showing. Then the tradesman profile with its wallet, and
  every dispute the person is in, either side, each linking to D2.
- **Actions:** suspend (7 / 30 / 90 days, or permanent — permanent is an admin's
  alone) · reactivate · **change role**, the only place a role changes · create a
  moderator or an admin.
- All of it confirmed, all of it audited: the change and its audit row are written
  in the same transaction, with the before/after diff and the reason.

What it refuses, and why:
- **An admin acting on his own account.** Suspending yourself locks you out of the
  screen that would undo it. The screen says so on your own row rather than
  letting you press and read an error.
- **Making somebody a tradesman from a dropdown.** A m3allem is an application
  with a CIN behind it (M1, then A2); a role set here would be a provider with no
  profile, invisible to every screen that expects one.
- **Changing the role of somebody who has that profile.** His offers, jobs and
  credit all hang off it. The role panel says this instead of offering a select.
- **Taking the last active admin.** Kept as the platform's invariant even though
  A3 cannot reach it: the caller is always an active admin, so the self-refusal
  gets there first.

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
  expiry, dispute window, how many clients a tradesman may try to hand his number
  to before staff hear about it, the platform's bank details shown at M9, and
  maintenance mode. Every change is audited with the old and the new value.
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
