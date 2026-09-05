# Architecture — TieOut (Razorpay AI Buildathon, Track 04)

This is the architecture explanation for submission. (`docs/ARCHITECTURE.md`
is the internal build spec used during development; this document describes
the finished system for a reader seeing it for the first time.)

## The problem

A merchant collecting payments through Razorpay needs to verify, on an
ongoing basis, that money moving through three separate systems actually
agrees: **what the gateway captured**, **what actually settled to the bank**,
and **what the internal books/invoices say was paid**. Today this is done by
a person manually cross-checking spreadsheets. It's slow, and a missed
discrepancy is a real financial error, not a cosmetic bug.

## What this system does

It closes that loop automatically for a batch of records, and for every
single case makes one of two decisions:

- **Auto-close** — the case is unambiguous; no human review needed.
- **Escalate** — something is wrong, or something is inherently ambiguous,
  and a human needs to look at it, along with a plain-English reason why.

It never picks between two plausible answers. When it can't be certain, it
says so instead of guessing.

## System architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Data layer  │ --> │  Rule engine  │ --> │  Explanation   │
│ (generate.py,│     │  (engine.py)  │     │  layer         │
│ orders_source│     │  deterministic│     │  (notes.py,    │
│ .py)         │     │  only         │     │  qa.py)        │
└─────────────┘     └──────────────┘     └───────────────┘
                             │
                             v
                    ┌──────────────────┐
                    │  Eval + audit log  │
                    │  (evaluate.py)     │
                    └──────────────────┘
                             │
                ┌────────────┴────────────┐
                v                          v
        out/report.html          reconciler/api.py
        (static, offline)         (FastAPI, in-memory,
                                   no database)
                                          │
                                          v
                                frontend/index.html
                                (dark-theme console)
```

## Data layer — what's real, what's synthetic, and why

| Source | Status | Why |
|---|---|---|
| **Orders** | Real — pulled live from Razorpay's test-mode `POST /v1/orders` when requested | This endpoint requires no account activation or KYC; verified by actually creating real orders during development, including a 40-order batch at real scale (6.57s, no rate limiting). |
| **Payments** | Synthesized, matching Razorpay's documented `Payment` entity field-for-field (`amount`, `fee`, `tax`, `order_id`, `captured`, `amount_refunded`, `dispute_id`, ...) | Creating a real captured payment requires completing checkout with a test card — a browser/human step, not something a batch script can do. |
| **Settlement recon lines** | Synthesized, matching Razorpay's documented Settlement Recon Combined API shape | Real settlements require an activated, KYC-approved account — out of reach for a student test account. |
| **Invoices (books)** | Synthesized | Represents an internal accounting system, matched only on `(customer_id, amount)` — deliberately, since a real books system often can't cross-reference the gateway's internal `order_id`. |

This is stated precisely, not glossed over as "everything's live" or hidden
as "everything's fake" — each layer is real to the extent that's actually
reachable, and synthetic where it isn't, for a documented reason.

## The rule engine — what decides, and what doesn't

Every decision is made by plain comparisons in `engine.py`. There is no
model in the decision path. The passes, in order:

1. **Quarantine** — a structurally malformed record (missing field,
   negative amount) is isolated and reported. The run never crashes on bad
   input.
2. **Disputed check** — a `dispute_id` present anywhere means escalate,
   regardless of how clean the amounts look.
3. **High-value gate** — above a fixed rupee threshold, escalate
   automatically, independent of match confidence. This demonstrates that
   the gate isn't just "escalate when unsure" — some things are gated by
   policy, not by doubt.
4. **Multi-payment ambiguity** — a real, verified quirk in Razorpay's own
   API: a settlement recon line for a payment-type entry carries `order_id`
   but never `payment_id`. If an order has more than one payment, there is
   no way to know from the schema which payment a given settlement line
   covers. The engine always escalates this — it is a structural limit, not
   a confidence judgment, and no amount of certainty would justify guessing.
5. **Exact/tolerance match, missing/duplicate settlement, refund
   verification** — the ordinary cases.
6. **Books check** — matches invoices to payments by `(customer_id, amount)`
   only. When two open invoices collide (same customer, same amount), the
   engine abstains rather than picking one — the books-side twin of #4.

After every run, three (now four, with the books leg) **invariant
self-checks** run and are reported explicitly: every case is covered exactly
once, no settlement line or invoice is consumed by more than one decision,
and decision counts conserve the total batch size. These are asserted, not
assumed.

## The explanation layer — where AI is actually used

`notes.py` and `qa.py` are the only place an LLM is ever called (via a
small pluggable client, `reconciler/llm.py`, supporting Anthropic, OpenAI,
Gemini, or any OpenAI-wire-format host), and it is never given the power to
decide anything or state a number it wasn't handed. Every explanation and
every answer is computed first in plain Python from real data, then
optionally passed through an LLM purely to rephrase it more naturally — and
if no LLM provider is configured (the default, and the state this was built
and tested in), the plain-Python phrasing is what's shown, and it already
cites real record fields, not a generic label.

The Q&A layer answers a fixed set of question types — match rate, what
broke, why was a specific case escalated, throughput, the largest open
exception, and what the engine refuses to guess on — against the actual
computed results of the run being asked about. A question matching none of
those falls through to a free-form LLM answer, but only when a provider is
configured, and even then it's given nothing but the run's aggregate
summary numbers (never a raw record) and told to say it doesn't know rather
than guess — the UI labels this specific case as AI-generated rather than
blending it in, since it's the one place actually generating a new
sentence instead of rephrasing an already-true one.

## Serving layer

`reconciler/api.py` is a thin FastAPI wrapper with four endpoints (generate a
batch, run reconciliation, fetch results, ask a question), holding batches in
an in-memory dictionary. There is deliberately no database: the whole system
is stateless between separate runs by design, and a database would be solving
a problem (persistence across restarts) this project doesn't have. It also
avoids a specific, observed failure mode in a competing submission's
Postgres-backed architecture (a live hang on load), without needing to.

`frontend/index.html` is a single self-contained page (no build step, no
framework) that renders whatever the API returns — it never computes a
decision or a metric itself.

## The one thing this system is honest about not solving

International payments that settle in INR after currency conversion aren't
modeled. The engine has no FX-conversion logic, so it correctly refuses to
auto-close these — it never silently mis-closes one — but it can currently
only tell you the amount doesn't match, not that the cause is FX conversion
specifically. This is a safe-failure gap (it over-escalates rather than
guessing), and it's stated here, in the report, and in the frontend's
"Known limitation" panel — not discovered by a reader digging through code.

## Verified results (seed 42, reproducible)

- 207 cases (payments, settlements, invoices combined)
- 100% overall decision accuracy against ground truth
- **0.00% false-auto-close rate** — the headline safety number
- All invariants hold
- The centerpiece abstention case (duplicate-invoice collision): 11/11
  correct, never guesses — re-checked across four different random seeds
- 38 unit tests, built independently of the data generator, directly from
  the fault taxonomy's specification — this is what makes "100% accuracy"
  a verified claim rather than a self-consistency artifact
