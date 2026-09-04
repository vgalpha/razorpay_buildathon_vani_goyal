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

- **Uses it for:** writing the plain-English explanation for a flagged case,
  and phrasing answers to questions about the run (match rate, what broke,
  throughput, biggest exception, what it refuses to guess on).
- **Never uses it for:** deciding whether a case is a match, computing an
  amount, or picking between two ambiguous candidates. Those are answered by
  Python comparisons in `reconciler/engine.py`, unit-tested against a fault
  taxonomy (`reconciler/taxonomy.py`) that is the single source of truth for
  what's correct.

## The one thing it's honest about not solving

International/FX-converted payments settle in INR after conversion, and this
engine has no FX model. It correctly refuses to auto-close these (never
mis-closes one), but it can only label them a generic amount mismatch, not
identify the true cause. Stated here, and on its own screen in the report/
frontend — not a footnote.

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
