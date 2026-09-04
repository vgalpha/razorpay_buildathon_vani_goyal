# Architecture — the how

Read PROJECT_CONTEXT.md first if you haven't. This file is the technical
spec to build against.

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
- **Invoice/books** (built — see below): `id`, `customer_id`, `amount`,
  `order_id` (present for descriptive/audit purposes only — **never used for
  matching**), `status` (always `"open"` in this dataset, representing the
  pre-reconciliation state), `created_at`. Matched purely on
  `(customer_id, amount)`, matching how REKON's weakest pass works, and
  deliberately so — see below.

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

Current taxonomy (11 classes, ~150 records total, counts chosen so every
class has enough instances for a defensible per-class precision/recall, not
sampled by probability weight):

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

**Books leg (built)** adds 4 more classes: `books_clean_match` (22),
`books_duplicate_invoice_collision` (11, the centerpiece — two open
invoices, same customer, same amount, one payment; correct behavior is to
abstain, never pick one), `books_missing_invoice` (8, no invoice raised at
all), `books_amount_mismatch` (8, invoice exists, wrong amount). This
mirrors REKON's actual weakest pass (`books_customer_amount`, matched purely
on customer+amount, prone to exactly this collision) — we're not avoiding
that weakness, we're making it the point of the third leg instead of a
silent gap.

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

1. **Quarantine** (to be added per the "failure recovery" rubric item) —
   isolate structurally malformed records (missing required fields, negative
   amounts) before any matching logic runs. Never crash on bad input; report
   what was quarantined and why.
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
8. **Books-matching pass (built)** — runs only when the gateway-side
   decision above is `auto_close` and `invoices` was passed as a real list
   (not `None`). Keyed on `(customer_id, amount)`; a collision (2+ open
   invoices matching) escalates rather than guessing, same abstention
   principle as the multi-payment `order_id` case.

Every decision is logged with: record id(s), rule fired, decision, a
plain reason category, and a timestamp — this is the audit trail.

**Invariant self-checks** (add early, they're cheap and high-signal): after
a full run, assert `auto_closed + escalated == total batch` and "no
settlement line consumed by more than one decision." Report pass/fail
explicitly, the way REKON's `conservation_of_bank_total` /
`no_double_settlement_spend` do — this is good practice independent of
competitive pressure, not feature-chasing.

## Explainer notes (`reconciler/notes.py`)

Pluggable: if an LLM API key is configured, call it to write the
human-readable note for an escalated record, citing the specific fields
examined. If no key is present, fall back to a template-based note so the
whole pipeline still runs end-to-end. Never let this layer touch the
decision.

## Q&A layer (to be added, step 3 in build order)

Same principle as notes: a deterministic planner maps a question to an
intent against already-computed metrics/audit log (match rate, biggest
exception, why was X escalated, throughput) and only the phrasing goes
through the LLM. Canned quick-question chips for the demo, matching the
"ask the ledger" pattern that's clearly effective in REKON's UI — this
specific pattern (deterministic-compute, LLM-phrase-only) is one we already
believe in, not something copied wholesale.

## Eval (`reconciler/evaluate.py`)

Per-fault-class precision/recall/F1 against taxonomy-sourced ground truth,
overall false-auto-close rate (the headline safety number — target zero),
throughput (records/sec, wall-clock timed), and the per-rule scorecard
(same numbers, grouped by which rule fired instead of by fault type — cheap,
it's a second view of data already computed).

## Real API integration (`reconciler/orders_source.py`, to be added)

A loader function, e.g. `load_orders(mode="live" | "synthetic")`. In `live`
mode, calls Razorpay's real test-mode `POST /v1/orders` (credentials from
`.env`, never hard-coded, never committed) to generate real order objects;
`synthetic` mode generates schema-matching fake ones. Payments and
settlement lines are always synthetic (see STATUS.md for why) but are
generated *against* whichever order set was loaded, so the same downstream
pipeline works unmodified either way. This loader boundary is the whole
point — it must be the only place that knows whether data is real or
synthetic, so the swap is a one-line change, never a scattered assumption.

## Backend (FastAPI, step 5 in build order)

A thin API wrapping the real Python engine — endpoints roughly:
`POST /batches` (generate a new batch), `POST /batches/{id}/run` (run
reconciliation), `GET /batches/{id}` (results), `POST /batches/{id}/ask`
(Q&A). No second implementation of the matching logic in JS, ever — the
frontend only renders what this API returns. Deploy to a normal host; test
repeatedly before relying on it, since REKON's own equivalent was observed
failing (see PROJECT_CONTEXT.md). Local execution remains the
guaranteed-reliable path for actually recording the pitch video, independent
of deploy status.

## Frontend (step 6 in build order)

Dark theme, card-based layout: headline metric cards, color-coded record
table, exceptions panel grouped by category, a limitations callout, an
engine-trace panel (rule firing + timing, rendered from the audit log), and
the Q&A chat panel with quick-question chips. All of it renders data fetched
from the FastAPI backend above — no client-side reimplementation of any
matching or scoring logic.

## Testing philosophy

`tests/test_engine.py` is the load-bearing test file: hand-built minimal
cases per taxonomy entry, asserted independently of the generator (see
"Taxonomy" above for why this specific independence matters). Add cases for
the quarantine pass and the books-leg duplicate-collision case when those
land. Keep methods short, names meaningful, no redundant comments, per
standing project style.
