# Pitch video — shot list, script, and production plan

Rewritten 2026-09-05 against the actual live product (previous version was
written before today's ground-truth transparency, chat-visibility, and LLM
layer changes, and referenced button labels that no longer exist). Every
number quoted below is real output from `seed=42` at its default
composition (no customize-panel overrides), captured directly by running
`generate_dataset(seed=42)` → `reconcile()` → `evaluate()` locally on
2026-09-05 — not invented placeholders. See "How the numbers were produced"
at the bottom for exact reproduction steps.

## Before you record: turn on deterministic mode

The live app normally seeds every batch from the current time, so two
recordings never match — fine for real use, fatal for rehearsing a
narration against specific numbers. A `DEMO_FIXED_SEED` env var fixes this
(see `reconciler/api.py`, right above `create_batch`, for the code comment
explaining it — operator-only, not a UI toggle, off by default).

**To turn it on:**
```
VERCEL_TOKEN=$(grep '^VERCEL_TOKEN=' .env | cut -d= -f2-)
echo "42" | npx --yes vercel env add DEMO_FIXED_SEED production --token "$VERCEL_TOKEN"
npx --yes vercel deploy --prod --token "$VERCEL_TOKEN" --yes
```
Wait for the deploy to finish (check the deployed URL responds), then every
"Generate sample data" click — with or without customize-panel inputs —
reproduces byte-identical output. Verified live on 2026-09-05: two
back-to-back generations, and one with `total_cases=150` typed into the
customize panel, all came back byte-for-byte identical on
`https://tieout-lemon.vercel.app/`.

**Immediately after your last take, turn it back off — do not skip this:**
```
npx --yes vercel env rm DEMO_FIXED_SEED production --token "$VERCEL_TOKEN" --yes
npx --yes vercel deploy --prod --token "$VERCEL_TOKEN" --yes
```
Confirm it's off by generating twice and checking the `seed` in the
response differs each time (or just watch the case count/first few IDs
change). A production deployment stuck on a fixed seed would mean every
judge who tries the live link sees the exact same canned batch — leave it
in demo mode by accident and that's a bug they'd notice, not the honest
"self-generating" story the rest of this project earns.

## What Razorpay actually asks for (re-verified 2026-09-05, live browser)

Confirmed directly on razorpay.com/buildathon (a JS SPA — screenshots, not
a text fetch, see docs/PROJECT_CONTEXT.md's "Video/submission requirements"
entry for the full trail): three things, called "the proof" on their own
site —

1. "a repo that actually runs"
2. "a 5-minute video of it working"
3. "what broke at 2 AM, and how you got out"

That third one is not incidental — it's the same axis as the general
judging card's "Failure recovery — what broke, and what you did about it."
The new 3:50–4:10 beat below exists specifically to answer it on camera —
a real bug, wrongly diagnosed at first, corrected by evidence — not just
disclosed in the README the way the FX limitation is. Secondary sources (not Razorpay's own page — see
PROJECT_CONTEXT.md for caveats) suggest the actual submission form wants an
**unlisted YouTube link**, not a raw file upload; this is unconfirmed
against the primary source (the real Google Form requires personal info to
reach past its first page, which nothing in this session was authorized to
fill in) — default to unlisted YouTube unless the real form says otherwise
when Vani fills it in herself.

## The 5-minute structure

**Chronology, per Vani's explicit direction**: problem card(s) → TieOut
intro card → transition → live demo → failure-recovery card/story →
conclusion. This is a deliberate revision from an earlier draft of this
doc that opened cold on product footage with no framing at all — that
version was rejected as boring, and the fix isn't just "add energy," it's
"add shape": cards give the video a visible structure a judge can follow
in the first 20 seconds, as long as the cards themselves are punchy, not
recited mission statements. The one thing carried over from the earlier
draft's insight: don't let a card state an unproven claim before there's
any evidence for it. The TieOut card below says **what** the product does
(believable immediately). The **how it's built** claim — plain math
decides, AI only explains — is held for the chat beat, where it lands as a
caption on evidence already on screen, not an assertion up front.

Budget: **~4:45**, not the full 5:00 ceiling — a video that breathes beats
one that's rushed to a mark, per the pacing advice already cited below.

### 0:00–0:20 — Problem card(s): the mismatch, stated plainly and with energy

Two cards, delivered with real pace and a beat of silence between them —
this is a hook, not an essay, so keep each line short enough to say without
a breath:

**Card 1** (~10s): *"A customer pays. The gateway settles it. The books
record it. Three numbers — that are supposed to be the same number."*
**Card 2** (~10s): *"Most companies still check that by hand. One missed
mismatch is real money, quietly gone."*

No invented statistic here (no "$X billion lost industry-wide" claim) —
this project's whole differentiator is not overclaiming what isn't
verified, and that discipline should show up in the very first line, not
just the README.

### 0:20–0:35 — The TieOut card: what it does, no architecture claim yet

**Card 3**: *"Presenting TieOut. It checks your payments against what
settled, and what the books say — closes what it's sure about,
automatically, and asks a human about everything else."* Then the bridge,
spoken over the card or a quick cut to the loading hero screen: *"Let's see
it in action."*

### 0:35–1:30 — Generate, customize, run

1. Click **"Generate sample data."** Let it resolve (real elapsed time,
   don't cut — the honesty of "this actually ran" matters more than speed
   here). Land on the "ready" screen: *"207 transactions generated — 222
   payments, 200 settlement lines, and 117 invoice records are ready to
   check."*
2. Briefly expand **"Customize this batch (optional)"** — one sentence,
   don't rebuild the batch on camera: *"Every one of 16 fault types is
   named and countable — not a black box."* Type **150** into the
   total-transactions field, leave fault-type fields blank, click
   **"Generate sample data"** again. Result at this exact input (verified
   2026-09-05): **151 cases, 100.0% accuracy, 0.00% false auto-close.**
3. Click **"Discard & start over"** (added specifically because there was
   previously no way off this screen except a page reload) back to a clean
   hero, then generate the real demo batch once more — the plain default,
   no customize inputs. This is the **207-case** batch every number below
   is quoted from.
4. Click **"Reconcile now."** Let the metric cards populate on screen:

   | Card | Value at seed=42 |
   |---|---|
   | Accuracy | **100.0%** |
   | Incorrect approvals | **0.00%** |
   | Time taken | a few ms (real wall-clock timing, varies run to run — narrate "a couple of milliseconds," let the real number speak for itself) |
   | Transactions checked | **207** |

   Read the caption under the cards on camera — new today, and the single
   most important sentence for judging honesty: *"Measured against this
   batch's known-correct answers — a validation score for the engine, not a
   live production guarantee."* One tight sentence on what that means:
   *"It's a validation run against a known-correct answer key — exactly
   what the track brief asks for. In production this same loop runs once
   offline to earn a fixed accuracy figure, then the live engine runs on
   real transactions with no answer key left to grade against."*

### 1:30–2:10 — Prove the accuracy number isn't just asserted

Today's ground-truth transparency feature, answering "why should I trust
that 100%":

1. Click the **"Expected outcomes"** tab in "What's in this batch" — the
   answer key itself (fault type, expected decision), viewable and
   downloadable, before or after the run.
2. Click **"Compare against expected outcomes ▸"**. At 100% accuracy:
   *"No mismatches — every case matched its expected outcome."* Toggle
   **"Show mismatches only"** off once to prove the full case-by-case
   table exists: *"If anything had disagreed with the answer key, this is
   exactly where you'd see which case, and why."*

### 2:10–2:50 — The trust moment: real escalations, read verbatim

Scroll to **"What needs a human" → "Flagged items — with the actual
reason."** All four of these are load-bearing — the first two are opposite
halves of the same abstention thesis (gateway-side ambiguity, books-side
ambiguity), so both stay in, tightened rather than cut:

1. **`multi_payment_ambiguous`**, case `order_9tgLb7tKR69yz8`: *"order has
   multiple payments; recon payment-lines carry order_id only (no
   payment_id), so a settlement line cannot be attributed to one specific
   payment."* — a real, documented Razorpay schema constraint, not an
   invented difficulty.
2. **`books_duplicate_invoice_collision`**, case `order_HcQv4XNiMyjkl1`:
   *"2 open invoices match this customer and amount; books alone cannot say
   which one this payment settles -- abstaining."* Same principle, books
   side — say that parallel explicitly.
3. **`high_value_gate`**, case `order_bdYvpiYKne1WJn`: *"amount exceeds
   ₹50000.00 auto-close ceiling."* Not a confidence judgment — a rule.
4. **`disputed`**, case `order_sXZoMZwoOmNqRW`: *"dispute_id present; never
   auto-closed regardless of amount."*

### 2:50–3:20 — Where AI actually is, and isn't — the architecture claim, now earned

Open the chat panel — the labeled **"Ask a question"** pill or the inline
**"Ask a question about this run"** button (both new today, added because
the launcher used to be an unlabeled icon nobody could find). Ask a
quick-chip question first (**"what's the biggest exception?"**) and read
the real answer. Then type something the fixed templates don't cover —
e.g. *"what's your favorite color?"* — and show it gracefully degrade to
*"I don't have a canned answer for that yet..."* rather than hallucinate
one. **This is where the design rule finally gets said** — as a caption on
what's already on screen, not a slide-one assertion: *"Plain math decides
every match. AI only ever explains a decision — it can never make one.
There's a pluggable LLM layer under this — Anthropic, OpenAI, Gemini, or
any OpenAI-compatible host — and even when one's configured, it only ever
phrases an already-computed fact, or answers strictly from this run's
aggregate numbers, labeled as AI-generated when it does. No key is set on
this deployment right now, and the app doesn't need one to work — that's
the point."* This is the single best on-camera demonstration of the
judging rubric's exact words: *"the right tool in the right place, and
where you chose not to use one."*

### 3:20–3:50 — The honest scorecard, and the one disclosed limitation

Scroll to **"Per-fault-class accuracy"** briefly — real per-class numbers
(all 100.0% at seed=42, 16 rows). Then state the FX limitation plainly,
from the README (no in-UI banner for this anymore — moved there
deliberately): *"International payments settled in INR after conversion
aren't modeled. The engine correctly refuses to auto-close these — it
never mis-closes one — but it can only say the amount doesn't match, not
why."* Don't compare this to any other submission; let it stand on its own.

### 3:50–4:20 — Failure-recovery card, and the story that shows the work

**Card 4**: *"What broke — and how we found out."* Razorpay's own site
says it reads exactly three things: a repo that runs, a 5-minute video,
and "what broke at 2 AM, and how you got out." The FX limitation above is
a *known* limitation, not a thing that broke — this beat is the one that
actually answers that third ask, and it's a real story from this build:

*"Here's a real one. The History page felt slow, even with almost no
history in it. The obvious guess was a heavy database query — so we read
the actual query and checked the fetch pattern, and that guess was wrong:
the query was already lean, no missing pagination, nothing pulling more
data than it needed. The real cause was upstream of the query entirely —
every server cold start was silently re-running a full schema-migration
check before answering anything at all, every single time. Fixed by
checking once instead of blindly retrying it, and wrote a test that proves
it still repairs a genuinely broken database when one actually shows up."*
Closing line, said plainly: *"That's the habit this project runs on —
check before you guess, then fix the thing that's actually wrong, not the
thing that looked wrong."*

The specificity here is the point, not a flourish — "we checked" is a
weaker sentence than "we read the query and it was already lean." Say the
second one. This is exactly the kind of debugging judgment an internship
reviewer is trying to see evidence of, not just told about.

### 4:20–4:45 — Why it's real, and the close

**Card 5** (conclusion): One line on data authenticity: order data can be
pulled live from Razorpay's actual test-mode API (`order_mode="live"`,
`reconciler/orders_source.py`); payment and settlement data is synthesized
but built field-for-field to match Razorpay's documented schema, including
the real `order_id`-only linkage on payment-type settlement lines that
makes the multi-payment case genuinely ambiguous, not invented. Close by
tying back to the internship pitch directly: this is the judgment —
knowing when *not* to act — that the role is actually asking to see.

## Division of labor

**Already done, ready to use as-is:**
- The deterministic demo seed (this doc's first section) — flip it on,
  it's tested and verified live.
- This script, with real numbers and real case IDs already captured — no
  more numbers need inventing, just narrate what's on screen.
- The click sequence above, in order, synced to the script.

**Only Vani can do:**
- Her own voice and on-camera framing/delivery.
- Actually operating the recording software.
- The final edit/trim and uploading to wherever the real submission form
  wants it (unlisted YouTube is the safe default per above — confirm
  against the actual Google Form when she reaches its later pages).
- Filling in and submitting the actual application form (this session
  deliberately did not proceed past the form's first page — entering
  personal data and submitting are both outside what an unattended agent
  should do without her sitting there).

## Practical recording guidance

- **Tool**: OS-native screen recording is enough — QuickTime's screen
  recording (Mac, free, no signup, File → New Screen Recording) or the
  built-in Windows Game Bar (Win+G). Don't adopt a new tool on deadline
  day. A separate voice memo recorded simultaneously (phone) is a fine
  fallback if QuickTime's own mic capture sounds bad — sync in the edit.
- **One dry run, then the real take.** Do exactly one full rehearsal
  end-to-end with the demo seed on, timing it with a stopwatch, before the
  take you intend to keep — this is standard advice across every
  hackathon-video guide surveyed (Devpost, Colosseum, HackQuest all say
  the same thing: rehearse once, then record, don't wing it live).
- **Delivery tips** (from Devpost's own judging/demo-video guidance,
  cross-checked against general hackathon-pitch sources): narrate like
  explaining to an engineer, not a recruiter — say what each screen proves
  and why it matters, not just what it shows. Pause between points instead
  of using filler words ("um," "so basically"). Start the demo within the
  first 20 seconds; judges decide fast.
- **No separate PPT/slide deck as a submission artifact.** Nothing in the
  verified requirements asks for one (repo + video + "what broke at 2 AM"),
  and a second artifact can end up contradicting the first if it drifts out
  of sync. The 5 cards in the structure above (2 problem cards, TieOut,
  failure-recovery, conclusion) are *inside* the video edit, not a separate
  file anyone submits.
- **How to actually make the cards — one answer, not three options**:
  build them natively in Premiere Pro's **Essential Graphics** panel (New
  Item → Text, or the Type tool directly on the timeline) — solid dark
  background matching the app's own theme (near-black, the same blue accent
  the UI already uses), centered text, simple fade-in/fade-out. This is
  less work than round-tripping through PowerPoint/Keynote, because there's
  no export step and no risk of the card's look clashing with the screen
  recording it cuts into (a default PPT template's white background and
  different font would visibly jar against the dark product UI). If it's
  genuinely easier to lay out text visually in PowerPoint/Keynote/Canva
  first, that's fine too — export each slide as a PNG and import it as a
  static image clip, same as inserting a screenshot. A plain screenshot of
  a static slide (no animation) works exactly as well as an image import;
  don't overthink this step, none of these three produce a visibly
  different result for plain text on a solid background.
- **Editing budget**: this is where "a bit more jazz, not too much" goes —
  the plain-spoken register is this project's whole differentiator and
  shouldn't be undercut by a hype-video treatment.
  - The 5 cards above, each on screen ~2-4s longer than the spoken line
    needs, so it doesn't feel rushed.
  - Text overlays holding the key numbers on screen for a beat or two when
    they're narrated (100.0% / 0.00% / 207) during the demo — reinforces
    without requiring the viewer to read small UI text off a screen
    recording.
  - A simple zoom-to-highlight on the `reason_detail` text during the
    2:10–2:50 escalations beat — that quoted text is the single most
    persuasive frame in the video; make sure it's legible, not just visible.
  - Skip background music. Licensing risk on deadline day, and it works
    against the plain-spoken tone more than it adds energy — let cuts,
    cards, and pacing carry it instead.
  - Beyond that, a hard cut between beats is enough; captions are a
    nice-to-have, not a requirement (nothing in the research found a stated
    captioning requirement).
- **Time estimate today**: reading this script once (10 min) + one dry run
  with the demo seed on (10 min) + the real take (5-7 min, allow for one
  retry) + Premiere edit — 5 cards, overlays, one zoom-highlight (30-40 min,
  a bit more than a bare trim since there's real card-making above, still
  modest) + upload (5 min, network dependent) ≈ **65-80 minutes end to
  end**, plus however long re-reading the actual Google Form's later pages
  and submitting takes once she's ready to do that herself.

## How the numbers in this script were produced

Every number above came from running this locally on 2026-09-05, not from
the deployed app's UI (though the deployed app was separately verified to
produce byte-identical output under `DEMO_FIXED_SEED=42`, see the top of
this doc):

```python
from reconciler.generate import generate_dataset, scale_taxonomy_counts
from reconciler.engine import reconcile
from reconciler.evaluate import evaluate

ds = generate_dataset(seed=42)                 # the main 207-case walkthrough
run = reconcile(ds.payments, ds.settlement_lines, ds.invoices)
ev = evaluate(run, ds.ground_truth)

ds2 = generate_dataset(seed=42, fault_counts=scale_taxonomy_counts(150))  # the customize-panel beat
```

If today's date has moved on and you re-record later, `seed=42`'s exact
output is deterministic and reproducible forever (see
`tests/test_generate.py`) — the numbers in this doc will still be exactly
right as long as `reconciler/generate.py`'s builders haven't changed. If
they have, re-run the snippet above before trusting this doc's numbers
again.
