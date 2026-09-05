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
This script's beat 6 below exists specifically to answer it on camera, not
just in the README. Secondary sources (not Razorpay's own page — see
PROJECT_CONTEXT.md for caveats) suggest the actual submission form wants an
**unlisted YouTube link**, not a raw file upload; this is unconfirmed
against the primary source (the real Google Form requires personal info to
reach past its first page, which nothing in this session was authorized to
fill in) — default to unlisted YouTube unless the real form says otherwise
when Vani fills it in herself.

## The 5-minute structure

Total budget: 5:00. Timings are targets, not hard cuts — pacing advice
from hackathon-judging sources (Devpost's own judging/demo-video guides)
says pause between points and cut filler words rather than rush to hit a
mark exactly; a 4:45 video beats a rushed 5:00 one.

### 0:00–0:20 — Cold open: the problem, shown not explained

Camera on the empty hero screen (fresh page load, nothing generated yet).
One sentence, no slide: *"Every payment a business takes has to be checked
against what actually settled, and what the books say — by hand, today,
at most companies."* Do not click "Generate sample data" yet.

### 0:20–0:45 — The design rule, stated once, not sloganeered

Still on the empty screen, or a single plain-text slide: *"Plain math
decides every match. AI only ever explains a decision — it can never make
one. And the big-amount cases always go to a human, no matter how clean the
match looks."* This is literally what `reconciler/engine.py` does — say it
because it's true, not because it sounds good.

### 0:45–2:00 — Generate, customize, run

1. Click **"Generate sample data."** Let it resolve (real elapsed time,
   don't cut — the honesty of "this actually ran" matters more than speed
   here). Land on the "ready" screen: *"207 transactions generated — 222
   payments, 200 settlement lines, and 117 invoice records are ready to
   check."*
2. Briefly expand **"Customize this batch (optional)"** — don't rebuild the
   whole batch on camera, just prove the knob is real. Type **150** into
   the total-transactions field, leave every fault-type field blank, click
   **"Generate sample data"** again. Narrate: *"Every one of these 16 fault
   types is named and countable — this isn't a black box, and it isn't
   theater either."* Result at this exact input (verified 2026-09-05):
   **151 cases, 100.0% accuracy, 0.00% false auto-close.**
3. Click **"Discard & start over"** (the button now on this screen — added
   specifically because there was previously no way off it except a page
   reload) to go back to a clean hero, then generate the real demo batch
   one more time for the rest of the walkthrough — the plain default,
   no customize inputs. This is the **207-case** batch every number below
   is quoted from.
4. Click **"Reconcile now."** Let the metric cards populate on screen:

   | Card | Value at seed=42 |
   |---|---|
   | Accuracy | **100.0%** |
   | Incorrect approvals | **0.00%** |
   | Time taken | a few ms (varies run to run — this is real wall-clock timing of the compute, not a stored number, so don't script an exact ms figure; narrate "a couple of milliseconds" and let the real number speak for itself on screen) |
   | Transactions checked | **207** |

   Read the caption under the cards on camera — it's new today and it's the
   single most important sentence for judging honesty: *"Measured against
   this batch's known-correct answers — a validation score for the engine,
   not a live production guarantee."* Say plainly: *"This is a validation
   run against a synthetic batch with a known-correct answer key — exactly
   what the track brief asks for. In production this same loop runs once
   offline to earn a fixed accuracy figure, then the live engine runs on
   real transactions with no answer key left to grade against."*

### 2:00–2:45 — Prove the accuracy number isn't just asserted

New beat, didn't exist in the previous script — this is today's ground-truth
transparency feature and it directly answers "why should I trust that
100%":

1. Click the **"Expected outcomes"** tab in "What's in this batch" — show
   that the answer key itself (fault type, expected decision) is sitting
   right there, viewable and downloadable, before or after the run.
2. Click **"Compare against expected outcomes ▸"**. At 100% accuracy this
   shows: *"No mismatches — every case matched its expected outcome."*
   Toggle **"Show mismatches only"** off to show the full case-by-case
   table exists (case id, fault type, expected vs. actual, per row) — say
   *"If anything had disagreed with the answer key, this is exactly where
   you'd see which case, and why."*

### 2:45–3:30 — The trust moment: real escalations, read verbatim

Scroll to **"What needs a human" → "Flagged items — with the actual
reason."** Pick these real cards from the seed=42 batch and read the
`reason_detail` text on screen, not a paraphrase:

1. **`multi_payment_ambiguous`**, case `order_9tgLb7tKR69yz8`: *"order has
   multiple payments; recon payment-lines carry order_id only (no
   payment_id), so a settlement line cannot be attributed to one specific
   payment."* Narrate: this is a real, documented Razorpay schema
   constraint, not an invented difficulty.
2. **`books_duplicate_invoice_collision`**, case `order_HcQv4XNiMyjkl1`:
   *"2 open invoices match this customer and amount; books alone cannot say
   which one this payment settles -- abstaining."* Narrate the parallel
   explicitly: same principle, books side.
3. **`high_value_gate`**, case `order_bdYvpiYKne1WJn`: *"amount exceeds
   ₹50000.00 auto-close ceiling."* Narrate: this one isn't about confidence
   at all — it's a rule, not a judgment call.
4. **`disputed`**, case `order_sXZoMZwoOmNqRW`: *"dispute_id present; never
   auto-closed regardless of amount."*

### 3:30–4:00 — Where AI actually is, and isn't

Open the chat panel — click the labeled **"Ask a question"** pill or the
inline **"Ask a question about this run"** button (both new today, added
because the launcher used to be an unlabeled icon nobody could find). Ask a
quick-chip question first (**"what's the biggest exception?"**) and read
the real answer that comes back. Then, on camera, type something the fixed
templates don't cover — e.g. *"what's your favorite color?"* — and show it
gracefully degrade to *"I don't have a canned answer for that yet..."*
rather than hallucinate one. Narrate: *"There's a pluggable LLM layer under
this — Anthropic, OpenAI, Gemini, or any OpenAI-compatible host — and even
when one's configured, it only ever phrases an already-computed fact, or
answers strictly from this run's aggregate numbers, labeled as AI-generated
when it does. No key is set on this deployment right now, and the app
doesn't need one to work — that's the point."* This is the single best
on-camera demonstration of the judging rubric's exact words: *"the right
tool in the right place, and where you chose not to use one."*

### 4:00–4:30 — The honest scorecard, and the one disclosed limitation

Scroll to **"Per-fault-class accuracy"** briefly — real per-class numbers
(all 100.0% at seed=42, 16 rows). Then state the FX limitation plainly, from
the README (no in-UI banner for this anymore — moved there deliberately):
*"International payments settled in INR after conversion aren't modeled.
The engine correctly refuses to auto-close these — it never mis-closes
one — but it can only say the amount doesn't match, not why."* Don't
compare this to any other submission; let it stand on its own.

### 4:30–5:00 — Why it's real, and the close

One line: order data can be pulled live from Razorpay's actual test-mode
API (`order_mode="live"`, `reconciler/orders_source.py`); payment and
settlement data is synthesized but built field-for-field to match
Razorpay's documented schema, including the real `order_id`-only linkage on
payment-type settlement lines that makes the multi-payment case genuinely
ambiguous, not invented. Close by tying back to the internship pitch: this
is the judgment — knowing when *not* to act — that the role is actually
asking to see.

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
- **Editing**: minimal is fine — a hard cut between beats is enough,
  captions are a nice-to-have not a requirement given nothing in the
  research found a stated captioning requirement.
- **Time estimate today**: reading this script once (10 min) + one dry run
  with the demo seed on (10 min) + the real take (5-7 min, allow for one
  retry) + a quick trim/export (10-15 min) + upload (5 min, network
  dependent) ≈ **45-60 minutes end to end**, plus however long re-reading
  the actual Google Form's later pages and submitting takes once she's
  ready to do that herself.

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
