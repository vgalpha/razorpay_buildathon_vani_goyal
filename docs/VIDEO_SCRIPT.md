# Pitch video — script and click sequence

Numbers below are real output from `seed=42` (default composition). For why
the script is shaped this way, the research trail, and reproduction steps
for the numbers, see `docs/STATUS.md`'s "Deterministic demo seed +
finalized pitch-video script" and "Video script: intro fix, failure beat,
and card-based restructure" entries. This doc is action-only.

## Before recording: turn on the fixed demo seed

```
VERCEL_TOKEN=$(grep '^VERCEL_TOKEN=' .env | cut -d= -f2-)
echo "42" | npx --yes vercel env add DEMO_FIXED_SEED production --token "$VERCEL_TOKEN"
npx --yes vercel deploy --prod --token "$VERCEL_TOKEN" --yes
```
Wait for the deploy to finish, then every "Generate sample data" click
reproduces the same output.

**Immediately after the last take, turn it back off:**
```
npx --yes vercel env rm DEMO_FIXED_SEED production --token "$VERCEL_TOKEN" --yes
npx --yes vercel deploy --prod --token "$VERCEL_TOKEN" --yes
```
Confirm it's off: generate twice, check the `seed` differs each time.

## Submission requirements

Confirmed on razorpay.com/buildathon: three things —
1. "a repo that actually runs"
2. "a 5-minute video of it working"
3. "what broke at 2 AM, and how you got out"

Format: unconfirmed against the real form (secondary sources suggest
unlisted YouTube link) — check the actual Google Form yourself once you
reach its later pages, and use that instead if it says otherwise.

## Structure and budget

Problem cards → TieOut card → demo → failure-recovery card → conclusion.
Budget: **~4:45** (5:00 ceiling).

### 0:00–0:20 — Problem cards

**Card 1** (~10s): *"A customer pays. The gateway settles it. The books
record it. Three numbers — that are supposed to be the same number."*

**Card 2** (~10s): *"Most companies still check that by hand. One missed
mismatch is real money, quietly gone."*

### 0:20–0:35 — TieOut card

**Card 3**: *"Presenting TieOut. It checks your payments against what
settled, and what the books say — closes what it's sure about,
automatically, and asks a human about everything else."* Bridge: *"Let's
see it in action."*

### 0:35–1:30 — Generate, customize, run

1. Click **"Generate sample data."** Let it resolve on screen (don't cut).
   Ready screen reads: *"207 transactions generated — 222 payments, 200
   settlement lines, and 117 invoice records are ready to check."*
2. Expand **"Customize this batch (optional)"**: *"Every one of 16 fault
   types is named and countable — not a black box."* Type **150** into
   total-transactions, leave fault-type fields blank, click **"Generate
   sample data"** again. Result: **151 cases, 100.0% accuracy, 0.00% false
   auto-close.**
3. Click **"Discard & start over"**, then generate the real demo batch once
   more (plain default, no customize inputs) — this is the **207-case**
   batch every number below is quoted from.
4. Click **"Reconcile now."** Metric cards on screen:

   | Card | Value at seed=42 |
   |---|---|
   | Accuracy | **100.0%** |
   | Incorrect approvals | **0.00%** |
   | Time taken | a few ms (real, varies run to run — say "a couple of milliseconds," let the number speak) |
   | Transactions checked | **207** |

   Read the caption under the cards on camera: *"Measured against this
   batch's known-correct answers — a validation score for the engine, not a
   live production guarantee."* Then: *"It's a validation run against a
   known-correct answer key — exactly what the track brief asks for. In
   production this same loop runs once offline to earn a fixed accuracy
   figure, then the live engine runs on real transactions with no answer
   key left to grade against."*

### 1:30–2:10 — Prove the accuracy number isn't just asserted

1. Click the **"Expected outcomes"** tab in "What's in this batch" — the
   answer key itself, viewable and downloadable.
2. Click **"Compare against expected outcomes ▸"**: *"No mismatches —
   every case matched its expected outcome."* Toggle **"Show mismatches
   only"** off once: *"If anything had disagreed with the answer key, this
   is exactly where you'd see which case, and why."*

### 2:10–2:50 — Real escalations, read verbatim

Scroll to **"What needs a human" → "Flagged items — with the actual
reason."** Read these four cards' `reason_detail` text on screen, not a
paraphrase:

1. **`multi_payment_ambiguous`**, `order_9tgLb7tKR69yz8`: *"order has
   multiple payments; recon payment-lines carry order_id only (no
   payment_id), so a settlement line cannot be attributed to one specific
   payment."*
2. **`books_duplicate_invoice_collision`**, `order_HcQv4XNiMyjkl1`: *"2
   open invoices match this customer and amount; books alone cannot say
   which one this payment settles -- abstaining."* Say the parallel to
   case 1 explicitly: same principle, books side.
3. **`high_value_gate`**, `order_bdYvpiYKne1WJn`: *"amount exceeds
   ₹50000.00 auto-close ceiling."* Say: not a confidence judgment — a rule.
4. **`disputed`**, `order_sXZoMZwoOmNqRW`: *"dispute_id present; never
   auto-closed regardless of amount."*

### 2:50–3:20 — Where AI actually is, and isn't

Open the chat panel (**"Ask a question"** pill, or the inline **"Ask a
question about this run"** button). Ask **"what's the biggest exception?"**
and read the real answer. Then type something unrecognized — e.g. *"what's
your favorite color?"* — and show it degrade to *"I don't have a canned
answer for that yet..."* Say the design rule here, over this evidence:
*"Plain math decides every match. AI only ever explains a decision — it
can never make one. There's a pluggable LLM layer under this — Anthropic,
OpenAI, Gemini, or any OpenAI-compatible host — and even when one's
configured, it only ever phrases an already-computed fact, or answers
strictly from this run's aggregate numbers, labeled as AI-generated when
it does. No key is set on this deployment right now, and the app doesn't
need one to work — that's the point."*

### 3:20–3:50 — Scorecard and the disclosed limitation

Scroll **"Per-fault-class accuracy"** briefly (all 100.0%, 16 rows). State
the FX limitation: *"International payments settled in INR after
conversion aren't modeled. The engine correctly refuses to auto-close
these — it never mis-closes one — but it can only say the amount doesn't
match, not why."*

### 3:50–4:20 — Failure-recovery card

**Card 4**: *"What broke — and how we found out."*

*"Here's a real one. The History page felt slow, even with almost no
history in it. The obvious guess was a heavy database query — so we read
the actual query and checked the fetch pattern, and that guess was wrong:
the query was already lean, no missing pagination, nothing pulling more
data than it needed. The real cause was upstream of the query entirely —
every server cold start was silently re-running a full schema-migration
check before answering anything at all, every single time. Fixed by
checking once instead of blindly retrying it, and wrote a test that proves
it still repairs a genuinely broken database when one actually shows up."*
Closing line: *"That's the habit this project runs on — check before you
guess, then fix the thing that's actually wrong, not the thing that looked
wrong."* Say it with this exact specificity, not "we checked" — the detail
is what sells it.

### 4:20–4:45 — Close

**Card 5**: Order data can be pulled live from Razorpay's actual test-mode
API (`order_mode="live"`, `reconciler/orders_source.py`); payment and
settlement data is synthesized but built field-for-field to match
Razorpay's documented schema, including the real `order_id`-only linkage
on payment-type settlement lines that makes the multi-payment case
genuinely ambiguous. Tie back to the internship pitch: this is the
judgment — knowing when *not* to act — that the role is asking to see.

## Division of labor

**Already done:** the demo seed, this script with real numbers/case IDs,
the click sequence above.

**Only Vani:** voice and on-camera delivery, operating the recording
software, the edit, uploading, and filling in/submitting the actual
application form (not something this session does on your behalf).

## Recording guidance

- **Tool**: QuickTime screen recording (Mac) or Windows Game Bar (Win+G).
  A phone voice memo as backup audio if the built-in mic sounds bad.
- **One dry run, then the real take.** Rehearse once end-to-end with the
  demo seed on, timed with a stopwatch, before the take you keep.
- **Delivery**: narrate like explaining to an engineer, not a recruiter.
  Pause between points instead of filler words. Start the demo within the
  first 20 seconds.
- **No separate PPT/slide deck as a submission artifact** — the 5 cards
  live inside the video edit, not a separate file.
- **Making the cards**: build them natively in Premiere's **Essential
  Graphics** panel — solid dark background matching the app's own theme,
  centered text, simple fade-in/out. If it's easier to lay text out
  visually first, Keynote/PowerPoint/Canva → export as PNG → import as an
  image clip works the same; a plain screenshot of a static slide is fine
  too.
- **Editing**: the 5 cards, each held ~2-4s longer than the spoken line
  needs. Text overlays for the key numbers (100.0% / 0.00% / 207) during
  the demo. A zoom-to-highlight on the `reason_detail` text at 2:10–2:50.
  No background music (licensing risk, undercuts the plain-spoken tone).
  Otherwise hard cuts are enough; captions are optional.
- **Time estimate**: read script (10 min) + dry run (10 min) + real take
  (5-7 min) + Premiere edit (30-40 min) + upload (5 min) ≈ **65-80 minutes**
  end to end, plus however long the actual application form takes.
