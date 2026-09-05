# TieOut — Razorpay AI Buildathon 2026, Track 04 (AI Finance Controller)

Closes one finance-ops loop end to end: reconciling a merchant's payments
against Razorpay's settlement recon report *and* internal invoices (a 3-way
loop), auto-closing what it's certain about and escalating everything else
with a plain-English reason instead of guessing.

Deterministic rules make every close/escalate decision. An LLM (optional —
works with none present) only ever writes explanations or answers questions
about numbers that are already computed. It can never change a decision.

**Live app:** [https://tieout-lemon.vercel.app](https://tieout-lemon.vercel.app)
— generate a batch, run the loop, ask it a question, no setup needed.

Full background, the competitive analysis, and the technical spec live in
[`docs/STATUS.md`](docs/STATUS.md) (read this first), [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md),
and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Quick start

Requires Python 3.9+. No account, no API key, and no database needed to run
any of this.

```bash
pip3 install -r requirements.txt   # only needed for the API layer; the CLI below needs nothing extra
```

**Run the CLI** — generates a fresh 207-case batch, reconciles it, scores it,
and writes a report:

```bash
python3 run.py
```

Prints the summary (accuracy, false-auto-close rate, throughput, invariants,
a canned Q&A demo) to the terminal and writes `out/report.html` — open that
file in a browser for the full case-by-case breakdown.

**Run the tests:**

```bash
python3 -m unittest discover -s tests
```

38 tests, all passing. Hand-built per fault type, independent of the data
generator (see `docs/ARCHITECTURE.md`'s "Testing philosophy") — this is the
load-bearing evidence that the engine is actually correct, not just
internally consistent with itself.

**Run the API + frontend console:**

```bash
uvicorn reconciler.api:app --reload
```

Then open `frontend/index.html` directly in a browser (it talks to
`http://localhost:8000` by default — see `API_BASE` at the top of the file's
`<script>` tag). Generate a batch, run the loop, ask it a question.

## What it deliberately does and doesn't use AI for

**Plain math decides, AI only explains.** Every match, mismatch, and
ambiguous-case abstention is a Python comparison in `reconciler/engine.py`,
unit-tested against a fault taxonomy (`reconciler/taxonomy.py`) that is the
single source of truth for what's correct — an LLM never sees a payment or
settlement record, and never picks between two candidates. The one place an
LLM is *allowed* in (`reconciler/notes.py`) is optional cosmetic phrasing of
an already-decided, already-true sentence: it can only rephrase a fact, never
add one or change a decision. It requires `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY` to be set; **neither is set in this deployment**, so the
live app runs on the deterministic template path with zero LLM calls, and
falls back to that template automatically if the call ever failed anyway.

This is a deliberate choice, not a missing feature: verification correctness
matters more here than generation, and a non-deterministic model has no
business being the thing that decides whether money is accounted for.

## What "accuracy" means here, and why it won't look like this in production

The live app generates a batch *with* a hidden answer key and then grades
itself against it — that's a validation run, not a production one, and the
accuracy card says so. This is intentional, not a shortcut: it's the same
generate-labeled-data / run-the-engine / report-the-score loop the track
brief itself asks for ("a 50+ record batch of synthetic data, reporting its
match rate"), so what's on screen *is* the deliverable, not a placeholder for
one.

A real deployment would use this exact same loop differently: run it once,
offline, against a large labeled batch to earn a fixed SLA accuracy figure
("this engine auto-closes correctly 99.x% of the time"), then ship the
engine to run on live, unlabeled transactions. At that point there's no
answer key left to grade against, so accountants would never see a live
accuracy number — they'd see decisions and exceptions, backed by the SLA
figure earned during validation. Note that `order_mode="live"` (pulling real
Orders from Razorpay's test API, see "Data sources" below) does not change
this: it only changes where `order_id` strings come from, not whether the
batch is labeled — every payment, settlement line, and fault is still
synthetically constructed with a known-correct answer either way, so it's
not a production mode.

If you want to check the accuracy number is honest rather than taking the
UI's word for it, don't trust the card — reproduce it: the generator
(`reconciler/generate.py`) and the engine (`reconciler/engine.py`) are
independent code paths that never see each other's internals, `tests/`
hand-asserts the expected decision for every fault type without going
through the generator at all, and `/batches/{id}/data` (used by "View data"
in the UI) exposes every input record without the answer key, so any run is
independently re-checkable.

## The one thing it's honest about not solving

International/FX-converted payments settle in INR after conversion, and this
engine has no FX model. It correctly refuses to auto-close these (never
mis-closes one), but it can only label them a generic amount mismatch, not
identify the true cause.

By the time a payment reaches the reconciler its currency is already INR and
carries no FX marker, so there's no honest way to tag which specific
`amount_mismatch` rows are FX-caused in the UI without peeking at the
generator's answer key — doing that would defeat the point of the exercise.
This gap is disclosed here instead of as a claim the UI can't actually back up.

## Data sources

- **Orders**: pulled live from Razorpay's real test-mode API by default when
  `order_mode="live"` is passed (see `reconciler/orders_source.py`); the
  default `synthetic` mode is deterministic and used for the reproducible
  test suite.
- **Payments and settlement-recon lines**: synthesized, but built
  field-for-field to match Razorpay's actually-documented API schema (not
  guessed) — including a real, verified schema quirk that payment-type
  settlement lines carry `order_id` but not `payment_id`, which is what makes
  a multi-payment order genuinely ambiguous to reconcile at the line level.
- **Invoices/books**: synthesized, matched only on `(customer_id, amount)` —
  deliberately, since a real books system often can't cross-reference the
  gateway's `order_id`. That's what makes the duplicate-invoice-collision
  case (two open invoices, same customer, same amount, one payment) possible,
  and the correct response is to abstain, not guess.

Real settlement objects require an activated, KYC'd Razorpay account, which
is out of reach for a student test account — so that layer stays synthetic,
stated plainly rather than implied to be something it isn't.
