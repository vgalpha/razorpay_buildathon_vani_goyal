# Architecture — the how

This is the technical deep-dive on the finished system: data model, the
deterministic engine's passes in order, where the LLM layer is (and isn't)
allowed in, and how correctness is checked. See the top-level `README.md`
for the pitch and quick start.

## Core principle

Deterministic code decides. AI explains or phrases, never decides. This is
not a slogan — it's enforced by keeping the decision (`auto_close` /
`escalate`) computed entirely by plain comparisons in `engine.py`, with the
LLM layer only ever called after a decision is already made, to write a
human-readable note or answer a question about already-computed numbers.
Nothing the LLM produces should ever be able to change a decision or a
number.

## Data model (`reconciler/schema.py`)

Mirrors Razorpay's actually-documented API entities (verified by fetching
their public docs, not guessed):

- **Payment**: `id`, `order_id`, `amount`, `currency`, `method`, `fee`,
  `tax`, `captured`, `amount_refunded`, `dispute_id`, `created_at`.
  `fee`/`tax` computed from `FEE_RATE_BY_METHOD` (illustrative rates,
  labeled as such — not Razorpay's real published pricing) + 18% GST.
- **SettlementLine** (from the real Settlement Recon Combined API shape):
  `entity_id`, `type` (payment/refund/transfer/adjustment), `amount`,
  `currency`, `fee`, `tax`, `settled`, `settlement_id`, `settlement_utr`,
  `payment_id`, `order_id`, `method`, `dispute_id`, `created_at`,
  `settled_at`. **Real, verified schema quirk**: payment-type lines carry
  `order_id` but `payment_id` is null; refund/transfer-type lines carry
  both. This is what makes multi-payment orders genuinely ambiguous — not
  an invented difficulty.
- **Invoice/books**: `id`, `customer_id`, `amount`, `order_id` (present for
  descriptive/audit purposes only — **never used for matching**), `status`
  (always `"open"` in this dataset, representing the pre-reconciliation
  state), `created_at`. Matched purely on `(customer_id, amount)` —
  deliberately, since a real books system often can't cross-reference the
  gateway's own `order_id`. See below for what this choice makes possible.

`HIGH_VALUE_THRESHOLD_PAISE` (₹50,000) and `ROUNDING_TOLERANCE_PAISE` (₹1)
live here as named constants, not magic numbers scattered through the engine.

## Taxonomy (`reconciler/taxonomy.py`) — single source of truth

`TAXONOMY` maps each fault type to a `FaultSpec(fault_type, description,
expected_decision, expected_reason_category, count)`. This is the one place
that defines "what's correct." Both `generate.py` and `engine.py` are
independently checked against it:

- `generate.py` uses it to know how many of each case to build, and emits
  ground truth sourced directly from the spec (not from its own opinion of
  what it built).
- `tests/test_engine.py` builds minimal hand-crafted `Payment`/
  `SettlementLine` objects **directly from the taxonomy's prose description**
  for each fault type — not by calling `generate.py` — and asserts the
  engine's decision matches `expected_decision`. This independence is the
  entire point: if `generate.py` and `engine.py` ever shared a wrong
  assumption, a test built from the spec instead of from the generator would
  still catch it. **Do not let this discipline slip as the taxonomy grows.**

Current taxonomy (16 classes, 207 records at the default seed — counts
chosen so every class has enough instances for a defensible per-class
precision/recall, not sampled by probability weight):

| fault_type | expected_decision | why |
|---|---|---|
| `clean_match` | auto_close | baseline |
| `rounding_noise` | auto_close | ≤ ₹1 diff |
| `amount_mismatch` | escalate | > tolerance |
| `multi_payment_ambiguous` | escalate | schema can't disambiguate — see above |
| `missing_settlement` | escalate | payment captured, no recon line |
| `duplicate_settlement` | escalate | >1 line for one payment |
| `refund_clean` | auto_close | refund line matches `amount_refunded` |
| `refund_mismatch` | escalate | it doesn't |
| `disputed` | escalate | `dispute_id` present — always, regardless of amount |
| `high_value_gate` | escalate | otherwise clean, but above ₹50k — value-based gate, independent of match confidence |
| `international_fx` | escalate (safe), but `expected_reason_category` is deliberately the generic `amount_mismatch` | **the disclosed limitation** — no FX model, so it correctly refuses to auto-close but can't name the true cause. This is a safe-failure gap (over-escalates, never mis-closes), which is the right kind of gap to have and to admit. |
| `quarantine` | quarantine | structurally malformed record (missing field, negative amount) — isolated before matching logic runs at all |

**Books leg** adds 4 more classes: `books_clean_match` (22),
`books_duplicate_invoice_collision` (11, the centerpiece — two open
invoices, same customer, same amount, one payment; correct behavior is to
abstain, never pick one), `books_missing_invoice` (8, no invoice raised at
all), `books_amount_mismatch` (8, invoice exists, wrong amount). Because the
books pass matches only on `(customer_id, amount)`, two open invoices for
the same customer and amount are genuinely indistinguishable at the books
layer — the collision case exists to make that a tested, admitted
abstention rather than a silent gap.

**Design detail worth preserving**: the books check only ever runs on a case
whose gateway-side decision (from the passes below) is already `auto_close`
— these 4 classes exist specifically to test the books layer, not to
re-test gateway matching. This meant three of the *original* 12 classes
needed a matching invoice attached too (`clean_match`, `rounding_noise`,
`refund_clean` — the ones whose gateway decision reaches `auto_close`), so
the books check has something to evaluate for them. Their ground-truth
`fault_type` and `expected_decision` are unchanged; only their `reason
category` may now read `books_clean_match` instead of `clean_match` in a
full 3-source run, which is fine because `evaluate.py`'s correctness check
only ever compares `decision`, never `reason_category` — see "Eval" below.
The remaining 9 original classes (already escalating for a gateway reason)
never reach the books check at all, and get no invoice.

`reconcile()` treats `invoices=None` (the default) as "books data wasn't
collected for this run" and skips the pass entirely — this is what keeps
every pre-books-leg caller, including all of step 1's unit tests, exactly
as it was. Passing `invoices=[]` or a real list is what turns the pass on,
even if that list happens to be empty for a given customer (which is
precisely what `books_missing_invoice` represents).

## Engine (`reconciler/engine.py`)

Deterministic passes, evaluated in order, first match wins. Roughly:

1. **Quarantine** — isolates structurally malformed records (missing
   required fields, negative amounts) before any matching logic runs. The
   run never crashes on bad input; what was quarantined and why is reported
   like any other decision.
2. Disputed check (always escalate regardless of amount).
3. High-value gate (always escalate above threshold, regardless of match
   quality) — demonstrates gating independent of confidence, not just
   anomaly-based escalation.
4. Multi-payment order → always escalate (schema-level ambiguity, not a
   confidence judgment).
5. Single-payment exact/tolerance match → auto-close or escalate on amount
   diff.
6. Missing / duplicate settlement checks.
7. Refund-line checks (matched via `payment_id`, which the real schema does
   carry for refund/transfer types).
8. **Books-matching pass** — runs only when the gateway-side
   decision above is `auto_close` and `invoices` was passed as a real list
   (not `None`). Keyed on `(customer_id, amount)`; a collision (2+ open
   invoices matching) escalates rather than guessing, same abstention
   principle as the multi-payment `order_id` case.

Every decision is logged with: record id(s), rule fired, decision, a
plain reason category, and a timestamp — this is the audit trail.

**Invariant self-checks** run after every full run and are reported
explicitly, pass/fail, rather than assumed: every case is covered exactly
once, no settlement line or invoice is consumed by more than one decision,
and decision counts conserve the total batch size.

## Explainer notes (`reconciler/notes.py`)

Pluggable: if an LLM provider is configured (see `reconciler/llm.py` below),
call it to write the human-readable note for an escalated record, citing the
specific fields examined. If none is configured, fall back to a
template-based note so the whole pipeline still runs end-to-end. Never let
this layer touch the decision.

## LLM provider layer (`reconciler/llm.py`)

One small client shared by `notes.py` and `qa.py`, so neither has to know
which provider is actually configured. `LLM_PROVIDER` env var selects
`anthropic` / `openai` / `gemini` / `openai_compatible` (any host that speaks
the OpenAI chat-completions wire format — Groq, Together, OpenRouter, a local
Ollama — via `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`), or it's auto-detected
from whichever of `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` is
set. This module only ever makes the network call and raises on failure —
the "phrase, never decide" rule is enforced by its two callers, not by it.

## Q&A layer (`reconciler/qa.py`)

Same principle as notes: a deterministic planner maps a question to an
intent against already-computed metrics/audit log (match rate, what broke,
why was a specific case escalated, throughput, the biggest exception, what
the engine refuses to guess on) and only the phrasing goes through the LLM.
Canned quick-question chips drive this in the UI. The one exception: a
question matching none of the fixed intents falls through to a free-form
LLM answer scoped to the run's aggregate summary only (never a raw record),
and the response carries a `source` field (`"template"` or `"llm"`) so the
frontend can label the free-form case explicitly rather than blending it in
silently alongside the templated answers' cosmetic phrasing.

## Eval (`reconciler/evaluate.py`)

Per-fault-class precision/recall/F1 against taxonomy-sourced ground truth,
overall false-auto-close rate (the headline safety number — target zero),
throughput (records/sec, wall-clock timed), and the per-rule scorecard
(same numbers, grouped by which rule fired instead of by fault type — cheap,
it's a second view of data already computed).

## Real API integration (`reconciler/orders_source.py`)

`load_orders(count, mode="live" | "synthetic")`. In `live` mode, it calls
Razorpay's real test-mode `POST /v1/orders` (credentials from `.env`, never
hard-coded, never committed) to generate real order objects and fails
loudly on any error rather than silently falling back to synthetic data;
`synthetic` mode generates schema-matching fake order IDs deterministically
from a seed. Payments and settlement lines are always synthetic (see "Data
sources" in the README for why) but are generated *against* whichever order
set was loaded, so the same downstream pipeline works unmodified either
way. This loader boundary is the whole point — it's the only place that
knows whether order data is real or synthetic, so the swap is a one-line
change, never a scattered assumption. `order_mode="live"` is gated off by
default in the deployed API (`ALLOW_LIVE_ORDERS`) since the endpoint is
unauthenticated and live mode spends real Razorpay API calls.

## Persistence (`reconciler/db.py`)

Batches are stored in a real database via SQLAlchemy, not an in-memory
dict — `DATABASE_URL` selects the backend: Postgres (Neon, in production)
or SQLite (local dev and the test suite, which needs no external service).
`make_engine()` creates the schema if it doesn't exist, adds any new summary
columns via a guarded `ALTER TABLE` (skipped once already applied), and sets
`pool_pre_ping=True` so a serverless Postgres instance that suspended itself
after idle gets transparently reconnected instead of surfacing a stale
connection as a 500. Each batch row holds the generated dataset, the run
result (once run), and denormalized summary columns so the batch-history
list can render without pulling every blob over the wire.

## Backend (FastAPI, `reconciler/api.py`)

A thin API wrapping the real Python engine — `POST /batches` (generate a
batch), `GET /taxonomy` (fault-type catalog for the customize panel),
`POST /batches/{id}/run` (reconcile), `GET /batches/{id}` (results),
`GET /batches/{id}/data` (raw input records, no answer key),
`GET /batches/{id}/ground_truth` (the answer key, served separately and
explicitly), `GET /batches` (history), and `POST /batches/{id}/ask` (Q&A).
No second implementation of the matching logic in JS, ever — the frontend
only renders what this API returns.

## Frontend (`frontend/index.html`)

Dark theme, card-based layout: headline metric cards, color-coded record
table, exceptions panel grouped by category, a quarantine panel for
structurally malformed records, a per-fault-class and per-rule accuracy
breakdown, an engine-trace panel (rule firing + timing, rendered from
`pass_timings_ms`/`pass_hit_counts`), a case drilldown that explains an
individual escalation (including calling out an FX-caused amount mismatch
inline where relevant), and the Q&A chat panel with quick-question chips.
All of it renders data fetched from the FastAPI backend above — no
client-side reimplementation of any matching or scoring logic.

## Testing philosophy

`tests/test_engine.py` is the load-bearing test file: hand-built minimal
cases per taxonomy entry — including the quarantine pass and the
books-leg duplicate-invoice-collision abstention — asserted independently
of the generator (see "Taxonomy" above for why this specific independence
matters). `tests/` also covers the generator, the DB layer, the LLM client,
and the Q&A router (84 tests total; run `python3 -m unittest discover -s
tests`).
