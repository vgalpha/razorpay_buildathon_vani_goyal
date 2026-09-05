# Pitch video — script and click sequence

Numbers below are real output from the live demo batch (seed=42, id
`266ce9f5d719`), captured directly from production on 2026-09-05 — **not**
the same numbers as an earlier draft of this doc, which used the generator
called directly (207 cases) rather than through the actual "Generate
sample data" button (229 cases, since that path applies jitter even with
the seed fixed). If you regenerate and get different specific numbers or
case IDs than what's quoted below, that's expected — the fault categories
and structure will be identical either way; read whatever's actually on
your screen instead of the literal quoted text.

**A live LLM (Gemini) is now configured in production** — the chat panel's
free-form-question beat behaves differently from what's written below; see
that beat's own note.

For why the script is shaped this way, the research trail, and reproduction
steps for the numbers, see `docs/STATUS.md`'s "Deterministic demo seed +
finalized pitch-video script" and "Video script: intro fix, failure beat,
and card-based restructure" entries. This doc is action-only.

## Before recording: turn on the fixed demo seed

**Already done for this session** — `DEMO_FIXED_SEED=42` is live in
production. If it's ever off, turn it on with:
```
VERCEL_TOKEN=$(grep '^VERCEL_TOKEN=' .env | cut -d= -f2-)
echo "42" | npx --yes vercel env add DEMO_FIXED_SEED production --token "$VERCEL_TOKEN"
npx --yes vercel deploy --prod --token "$VERCEL_TOKEN" --yes
```

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

Each beat below is split into **Action** (what to click/show on screen)
and **Speak** (what to say). Follow them in order, top to bottom.

---

### 0:00–0:20 — Problem cards

**Action:** Show Card 1 (~10s), then Card 2 (~10s). No clicks, no app on
screen yet.

**Speak (Card 1):** *"A customer pays. The gateway settles it. The books
record it. Three numbers — that are supposed to be the same number."*

**Speak (Card 2):** *"Most companies still check that by hand. One missed
mismatch is real money, quietly gone."*

---

### 0:20–0:35 — TieOut card

**Action:** Show Card 3.

**Speak:** *"Presenting TieOut. It checks your payments against what
settled, and what the books say — closes what it's sure about,
automatically, and asks a human about everything else. Let's see it in
action."*

---

### 0:35–1:30 — Generate, customize, run

**Action 1:** Click **"Generate sample data."** Let it resolve on screen —
don't cut. Screen will show: *"229 transactions generated — 249 payments,
220 settlement lines, and 128 invoice records are ready to check."*

**Speak 1:** *(no line needed here — let the real load time and the
on-screen count speak for themselves)*

**Action 2:** Expand **"Customize this batch (optional)."** Type **150**
into the total-transactions field, leave every fault-type field blank,
click **"Generate sample data"** again. Screen will show: **151 cases,
100.0% accuracy, 0.00% false auto-close.**

**Speak 2:** *"Every one of 16 fault types is named and countable — not a
black box."*

**Action 3:** Click **"Discard & start over,"** then click **"Generate
sample data"** once more with no customize input — this is the real demo
batch (**229 cases**) every number below is quoted from.

**Speak 3:** *(no line — this is a reset step)*

**Action 4:** Click **"Reconcile now."** Let the metric cards populate on
screen:

| Card | Value |
|---|---|
| Accuracy | **100.0%** |
| Incorrect approvals | **0.00%** |
| Time taken | a few ms (real, varies run to run) |
| Transactions checked | **229** |

**Speak 4:** *(reading the metric cards)* *"A couple of milliseconds."*
Then, pointing at the caption under the cards: *"Measured against this
batch's known-correct answers — a validation score for the engine, not a
live production guarantee. It's a validation run against a known-correct
answer key — exactly what the track brief asks for. In production this
same loop runs once offline to earn a fixed accuracy figure, then the live
engine runs on real transactions with no answer key left to grade
against."*

---

### 1:30–2:10 — Prove the accuracy number isn't just asserted

**Action 1:** Click the **"Expected outcomes"** tab in "What's in this
batch."

**Speak 1:** *(no line — just show it's there, viewable and downloadable)*

**Action 2:** Click **"Compare against expected outcomes ▸."** Toggle
**"Show mismatches only"** off once, to show the full case-by-case table.

**Speak 2:** *"No mismatches — every case matched its expected outcome. If
anything had disagreed with the answer key, this is exactly where you'd
see which case, and why."*

---

### 2:10–2:50 — Real escalations, read verbatim

**Action:** Scroll to **"What needs a human" → "Flagged items — with the
actual reason."** Find and open each of these four categories (your exact
case IDs will differ from the ones below if you regenerated — use whatever
real card is on your screen for each category, the text will be
equivalent):

1. **`multi_payment_ambiguous`** (example seen: `order_eRo7qYYOLQZ7mB`)

   **Speak:** *"Order has multiple payments; recon payment-lines carry
   order_id only, no payment_id, so a settlement line cannot be attributed
   to one specific payment."*

2. **`books_duplicate_invoice_collision`** (example seen:
   `order_B4zVC59yvlFSFx`)

   **Speak:** *"Two open invoices match this customer and amount; books
   alone cannot say which one this payment settles — abstaining. Same
   principle as the last one, books side."*

3. **`high_value_gate`** (example seen: `order_iWqsuhaFVBliyI`)

   **Speak:** *"Amount exceeds the auto-close ceiling. Not a confidence
   judgment — a rule."*

4. **`disputed`** (example seen: `order_uBuQqx9jR7Eef1`)

   **Speak:** *"Dispute ID present; never auto-closed regardless of
   amount."*

---

### 2:50–3:20 — Where AI actually is, and isn't

**Note before recording this beat**: a real Gemini key is now configured
in production. This changes the beat from what's scripted below — see the
callout after the Speak line.

**Action 1:** Open the chat panel (**"Ask a question"** pill, or the
inline **"Ask a question about this run"** button). Click the
**"what's the biggest exception?"** chip. Wait for the answer (~10-15s now
that a live key is configured — let it load, don't cut).

**Action 2:** Type an unrecognized question — e.g. *"what's your favorite
color?"* — and send it. Wait for the answer (**~20-25s** — a real live
Gemini call, not instant; let it load, don't cut, or trim the wait in the
edit).

**Speak (over both answers loading/appearing):** *"Plain math decides every
match. AI only ever explains a decision — it can never make one. There's a
pluggable LLM layer under this — Anthropic, OpenAI, Gemini, or any
OpenAI-compatible host — and even when one's configured, it only ever
phrases an already-computed fact, or answers strictly from this run's
aggregate numbers, labeled as AI-generated when it does."*

**Callout — what you'll actually see now:** the free-form question will
come back as a real, live AI-generated answer (labeled "Answered by AI" in
the panel), not the old static "I don't have a canned answer" fallback —
that's expected with a key configured, and it's arguably a stronger demo.
Don't say the line "no key is set on this deployment" — it's no longer
true. If you'd rather show the graceful-degradation-to-template behavior
specifically, that requires the key to be unset first; ask before this
beat if you want that instead.

---

### 3:20–3:50 — Scorecard and the disclosed limitation

**Action:** Scroll **"Per-fault-class accuracy"** briefly (all 100.0%, 16
rows).

**Speak:** *"International payments settled in INR after conversion aren't
modeled. The engine correctly refuses to auto-close these — it never
mis-closes one — but it can only say the amount doesn't match, not why."*

---

### 3:50–4:20 — Failure-recovery card

**Action:** Show Card 4.

**Speak:** *"What broke — and how we found out. Here's a real one. The
History page felt slow, even with almost no history in it. The obvious
guess was a heavy database query — so we read the actual query and checked
the fetch pattern, and that guess was wrong: the query was already lean,
no missing pagination, nothing pulling more data than it needed. The real
cause was upstream of the query entirely — every server cold start was
silently re-running a full schema-migration check before answering
anything at all, every single time. Fixed by checking once instead of
blindly retrying it, and wrote a test that proves it still repairs a
genuinely broken database when one actually shows up. That's the habit
this project runs on — check before you guess, then fix the thing that's
actually wrong, not the thing that looked wrong."*

Say it with this exact specificity, not "we checked" — the detail is what
sells it.

---

### 4:20–4:45 — Close

**Action:** Show Card 5.

**Speak:** *"Order data can be pulled live from Razorpay's actual
test-mode API; payment and settlement data is synthesized but built
field-for-field to match Razorpay's documented schema, including the real
order_id-only linkage on payment-type settlement lines that makes the
multi-payment case genuinely ambiguous. This is the judgment — knowing
when not to act — that the role is asking to see."*

---

## Division of labor

**Already done:** the demo seed, the Gemini key, this script with real
numbers/case IDs, the click sequence above.

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
  needs. Text overlays for the key numbers (100.0% / 0.00% / 229) during
  the demo. A zoom-to-highlight on the flagged-card text at 2:10–2:50. Two
  places you'll likely want to trim dead air in the edit: the ~15s and
  ~20-25s chat-answer waits at 2:50–3:20 (see that beat's note). No
  background music (licensing risk, undercuts the plain-spoken tone).
  Otherwise hard cuts are enough; captions are optional.
- **Time estimate**: read script (10 min) + dry run (10 min) + real take
  (5-7 min) + Premiere edit (30-40 min, a bit more if trimming the chat
  waits) + upload (5 min) ≈ **65-80 minutes** end to end, plus however long
  the actual application form takes.
