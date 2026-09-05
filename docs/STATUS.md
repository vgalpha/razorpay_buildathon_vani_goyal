# Status — read this first

Any new session (human or agent) picking this up should read this file first,
then `PROJECT_CONTEXT.md` (the why), then `ARCHITECTURE.md` (the how).

## Where things stand

- Track and project are decided (see PROJECT_CONTEXT.md). Not up for debate
  again without a real new fact — this project has already survived several
  rounds of "should we switch."
- Real Razorpay test API keys exist and work (see below). `.env` at repo root
  holds `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`, gitignored. Confirmed via
  live curl calls:
  - `GET /v1/payments`, `GET /v1/orders`, `GET /v1/settlements` all return
    empty-but-authenticated collections (no PAN/KYC block on test-mode API
    access itself).
  - `POST /v1/orders` **works** — real order objects can be created freely.
  - Real `Payment` objects cannot be created via pure API (checkout requires a
    browser/test-card step); `Settlement` objects require an activated,
    KYC'd account (out of reach for a student test account).
  - Resulting data-source decision: **Orders are pulled live from the real
    API. Payments and Settlement-recon lines are synthesized, but built
    field-for-field to match Razorpay's documented schema.** State this
    precisely in the video/README — it's a stronger, more specific claim than
    "modeled on their docs" alone, and it's true.
- **No LLM API key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`) is present in
  this environment.** The explainer-notes and Q&A layers (step 3, below) are
  built to work fully without one — every explanation and answer comes from
  a Python template citing real computed facts, not a placeholder — and
  *optionally* rephrase through an LLM if a key shows up later. The
  LLM-present code path (`notes.py`'s `_call_anthropic`/`_call_openai`) has
  only been exercised against a deliberately fake key (confirms it fails
  gracefully and falls back), never against a real one. If a real key is
  added later, spot-check the actual rephrased output once before recording
  the video — the fallback path is tested, the success path isn't yet.

## Files that exist so far

- `reconciler/schema.py` — `Payment` (now with `customer_id`), `SettlementLine`,
  and `Invoice` dataclasses, fee/tax constants, thresholds.
- `reconciler/taxonomy.py` — the fault taxonomy spec, **16 classes** (12 from
  step 1 + 4 books-leg classes added in step 2: `books_clean_match`,
  `books_duplicate_invoice_collision`, `books_missing_invoice`,
  `books_amount_mismatch`), the single source of truth for "what's correct."
- `reconciler/generate.py` — synthetic generator, one builder function per
  taxonomy class, exact counts (not probability sampling), fixed seed (42).
  Ground truth emitted straight from `TAXONOMY`. Now also builds `Invoice`
  records: attached (as clean, matching invoices) to `clean_match`,
  `rounding_noise`, and `refund_clean` cases — the three original classes
  whose gateway-side decision reaches `auto_close`, so they're the ones the
  books check actually runs against — plus the 4 dedicated books classes.
  207 total cases at seed 42 (was 158).
- `reconciler/engine.py` — deterministic engine. Pass order: quarantine →
  per-order-group (disputed → high-value gate → multi-payment → refund →
  missing/duplicate/amount-diff) → **books check (new)**, which only runs
  when the gateway-side decision is already `auto_close` and `invoices` was
  passed as a real list (not `None`) — this is what keeps the 2-source unit
  tests behaviorally unchanged, since they never pass `invoices` at all.
  Books-matching is deliberately keyed on `(customer_id, amount)` only, never
  `order_id` — a real books/ledger system often can't cross-reference the
  gateway's order_id, and that looseness is exactly what makes the
  duplicate-invoice collision (two open invoices, same customer, same
  amount) possible. On collision, the engine abstains rather than guessing —
  the books-side twin of the `order_id`-only ambiguity from step 1. Invariant
  checks now include `no_invoice_double_consumed` alongside the three from
  step 1.
- `reconciler/evaluate.py` — per-fault-class accuracy, binary
  precision/recall/F1 on the auto_close decision, false-auto-close rate,
  per-rule scorecard, throughput.
- `reconciler/report.py` — static dark-theme HTML report (metric cards,
  invariants panel, per-fault-class table, per-rule scorecard, disclosed
  limitation callout, exceptions grouped by category, quarantine list, full
  case table).
- `reconciler/orders_source.py` — `load_orders(count, mode="synthetic"|"live")`.
  synthetic (default): deterministic given a seed, matches the pre-existing
  order_id shape. live: calls the real `POST /v1/orders` test-mode endpoint
  (credentials from `.env`, read via a tiny manual parser since
  `python-dotenv` isn't installed and `requests` already was — no new
  dependency added). Fails loudly (raises) on any error in live mode rather
  than silently falling back to synthetic. `generate.py` now sources all
  order_ids through this loader instead of synthesizing them inline;
  default mode is "synthetic" so the seed-42 baseline (158 cases, 100%
  accuracy, 0% false-auto-close) is unchanged — reverified after the change.
- `run.py` — CLI entrypoint (`python3 run.py`), writes `out/report.html`. Now
  passes `dataset.invoices` into `reconcile()`, enabling the books pass.
- `reconciler/report.py` — subtitle updated to "3-source loop"; the
  fault-class table, per-rule scorecard, and exceptions section needed **no
  code changes** to display the 4 new classes — they were already generic
  over whatever `evaluate.py` hands them, which is worth knowing before
  assuming a UI change is needed for a taxonomy change.
- `tests/test_engine.py` — **23 tests, all passing** (17 from step 1 + 6 new:
  one per books fault class, one asserting `reconcile()` without an
  `invoices` arg is unaffected by the books pass, one for the
  `no_invoice_double_consumed` invariant). Same independence discipline as
  step 1 — hand-built `Payment`/`Invoice` objects, not generated via
  `generate.py`.
- `.gitignore` — covers `.env`, `out/`, `__pycache__/`. Written before `.env`
  was ever created, so the secret was never at risk of being staged.
- `reconciler/api.py` — FastAPI app, four endpoints, backed by a real
  database (see `db.py` below, and the "Persistence layer" note under
  build-order step 5 for what was actually tested).
- `reconciler/db.py`, `reconciler/serialize.py` — real Postgres/SQLite
  persistence for batches (via `DATABASE_URL`) and the dataclass<->dict
  conversion it needs. See "Persistence layer" under build-order step 5.
- `requirements.txt`, `Procfile` — deployment prep for the API layer.
- `reconciler/notes.py` — `generate_note(decision)`: a plain-English
  explanation for one decided case. Template-based by default (every fact
  comes from `Decision.reason_detail`/`reason_category`, nothing invented);
  `rephrase(fact_sentence)` optionally polishes it through Anthropic (tried
  first) or OpenAI (fallback) via stdlib `urllib` if a key is present in the
  environment, and falls back to the input sentence unchanged on *any*
  failure (no key, network error, bad response) — this can never crash or
  hang the pipeline. Wired into `report.py`'s exceptions section (the
  "Reason" column now shows the full generated note, not the bare category).
- `reconciler/qa.py` — `answer(question, run, ev, payments=None)`: a fixed
  set of keyword-matched intents (match rate, what broke, why was `<id>` not
  matched, throughput, biggest exception by real amount, what it refuses to
  guess on), each computing its answer from real data first and passing the
  result through `notes.rephrase`. Demonstrated via `run.py`'s
  `_print_qa_demo`, which prints canned Q&A pairs after every run (mirrors
  REKON's "quick question chip" pattern, deliberately, per
  `PROJECT_CONTEXT.md`'s competitive analysis).
- `tests/test_qa.py` — 15 new tests: one per Q&A intent against a hand-built
  5-case scenario, one confirming `rephrase`/`generate_note` produce the
  exact template with no key present, four confirming each abstention/gate
  class's note cites real fields (not a generic label), one confirming the
  LLM-present code path fails gracefully against a fake key. Caught one real
  bug during this step: `cls.run = <ReconciliationRun>` in a test class
  silently overwrote `unittest.TestCase`'s own `run()` method and broke the
  test runner — renamed to `cls.recon_run` everywhere; worth remembering as
  a naming trap if more tests are added later.

**Verified sample run** (`python3 run.py`, seed 42, 207 cases): 100% overall
accuracy, 0.00% false-auto-close rate, 100%/100%/100% auto-close
precision/recall/F1, all four invariants hold, 0.92ms wall time
(~224k records/sec — varies run to run, comparisons are cheap either way).
The Q&A demo's "biggest exception" answer correctly picked out the actual
highest-amount escalated case by real data, not a guess. The centerpiece class,
`books_duplicate_invoice_collision`, is 11/11 correct — it abstains every
time, never guesses. Re-checked across seeds 1, 7, 999: same result each
time (100% accuracy, 0% false-auto-close, invariants hold). 100% accuracy is
the *expected* result here, not a red flag: `engine.py` is a correct
implementation of `taxonomy.py`'s rules, verified independently by the
38 hand-built tests (23 engine + 15 notes/Q&A), and `generate.py`'s ground
truth is sourced from the same
spec, not invented — so a clean run confirms internal consistency across
many random instances per class, it does not by itself prove the taxonomy's
rules are the *right* rules (that argument lives in PROJECT_CONTEXT.md / the
video).

## Build order (do not reorder without a reason — see PROJECT_CONTEXT.md
"Sequencing philosophy")

1. **2-source core** — ✅ **DONE**, see "Files that exist so far" above. This
   is genuinely at a "would submit if stopped here" state: tested, honestly
   scored, includes the quarantine/failure-recovery pass, invariants
   reported, and real-Orders-API sourcing available via
   `orders_source.py`. Not yet done: the FastAPI/frontend wrapping
   (steps 5-6).
2. **Books leg (3-way)** — ✅ **DONE.** See "Files that exist so far." 207
   cases, 23/23 tests passing, all invariants hold including the new
   `no_invoice_double_consumed`. The centerpiece duplicate-collision case is
   11/11 correct abstention, not just "present."
3. **Explainer notes + Q&A layer** — ✅ **DONE.** See "Files that exist so
   far" (`notes.py`, `qa.py`). 38/38 tests passing. Runs fully in
   template-only mode in this environment (no LLM key present, see "Where
   things stand") — the optional-rephrase path is written and falls back
   safely, but not yet verified against a real key's actual output quality.
4. **Remaining instrumentation** — ✅ **DONE.** `engine.py`'s `_order_decision`
   is now a named, timed pass list (`disputed`, `high_value_gate`,
   `multi_payment`, `refund`, then `settlement_match` which is attributed
   post-hoc to either `exact_tolerance_match` or
   `missing_duplicate_settlement` depending on the actual outcome, since both
   rubric-named passes share one call site), plus separately timed
   `quarantine` and `books_customer_amount`. `ReconciliationRun` gained
   `pass_hit_counts` alongside the existing `pass_timings_ms` (already in the
   dataclass, just unpopulated before now). All 38 pre-existing tests still
   pass unmodified — no test asserted on timing structure, so this was a
   behavior-preserving refactor, not a risky one. Sample per-pass numbers
   (seed 42): quarantine 0.06-0.11ms, disputed 0.14-0.25ms, high_value_gate
   0.07-0.14ms, multi_payment 0.03ms, refund 0.05-0.06ms,
   exact_tolerance_match 0.22-0.25ms, missing_duplicate_settlement 0.02ms,
   books_customer_amount 0.10-0.15ms — all real, not fabricated, and they'll
   vary slightly run to run since everything here is microsecond-scale.
5. **FastAPI backend** — ✅ **DONE, locally verified, not deployed.**
   `reconciler/api.py`: `POST /batches` (generate, params `seed`/`order_mode`),
   `POST /batches/{id}/run` (reconcile + evaluate), `GET /batches/{id}`
   (fetch prior results, 404 if not run yet), `POST /batches/{id}/ask` (Q&A,
   400 if not run yet). **Update: now backed by a real database, not an
   in-memory dict** — the user explicitly asked for real persistence rather
   than the earlier no-DB stance (which was reasonable at the time but is
   superseded; see [[feedback-demo-risk-tolerance]]-style guidance in
   PROJECT_CONTEXT.md about not over-indexing on dependency risk on this
   project). See "Persistence layer" below for what was built and how it
   was verified. CORS open (demo app, no real user data).
   `fastapi`+`uvicorn` installed locally and added to `requirements.txt`
   (`requests` was already a dependency via `orders_source.py`'s live path).
   All four endpoints, plus the 404/400 edge cases (GET/ask before run) and
   the `seed`/`order_mode` params, were actually started with `uvicorn` and
   hit with real `curl` calls — not just written and assumed to work.
   `Procfile` added for deployment (`web: uvicorn reconciler.api:app --host
   0.0.0.0 --port $PORT`) but **not yet deployed anywhere** — that needs a
   host account (Render/Railway/Fly.io), which is the user's call, not
   something to do unattended. Local execution remains the
   guaranteed-reliable path for recording the pitch video regardless.

**Persistence layer (added after initial build) — ✅ DONE, verified against
real Postgres including an actual process restart, not just SQLite.**
- `reconciler/db.py` — one `batches` table (id, seed, order_mode, created_at,
  dataset_json, run_result_json), via SQLAlchemy Core so the same code works
  against Postgres (production) or SQLite (tests) off a single `DATABASE_URL`
  env var — no provider-specific behavior hard-coded anywhere.
- `reconciler/serialize.py` — clean `to_dict`/`from_dict` for the dataset and
  run/eval dataclasses, used by both `db.py`'s storage and (indirectly)
  `api.py`'s reconstruction of real objects before calling back into
  `engine.reconcile()`/`qa.answer()`.
- `reconciler/api.py` rewritten to read/write through `db.py` instead of an
  in-memory dict — same endpoint behavior and response shapes, no frontend
  changes needed.
- `requirements.txt` gained `sqlalchemy` and `psycopg2-binary`.
- **Tests**: `tests/test_db.py`, 3 new tests, run against SQLite (a
  standard, hermetic pattern for automated tests — no external service
  needed to run the suite), each opening a **fresh engine/connection** to
  simulate a restart, not just reading within one open connection. All 41
  tests pass (38 original + 3 new).
- **Real-Postgres verification, not just SQLite**: this machine turned out to
  have a local Postgres server already running (`pg_isready` succeeded); an
  isolated `reconciler_test` database was created on it (not reusing any
  existing database) specifically for this. Full loop tested against it:
  started the API, created a batch (`POST /batches`), ran it (`POST
  /batches/{id}/run`, 207 cases, 100% accuracy), confirmed the row directly
  via `psql`, **killed the server process entirely**, started a **brand
  new** process against the same database, and confirmed `GET
  /batches/{id}` and `POST /batches/{id}/ask` on the old batch ID both
  returned the identical, correct data. This is the actual proof the
  in-memory problem is solved, not an assumption.
- **Still needs the user**: an actual Neon project (or any Postgres) for
  production — this was verified against a local Postgres stand-in, never
  against a real Neon instance. Once a real `DATABASE_URL` exists, point the
  deployed app's env var at it; no code change needed.

6. **Frontend visual pass** — ✅ **DONE, locally verified against the real
   API.** `frontend/index.html` — single self-contained file, no build step,
   no framework, dark theme via CSS custom properties, system fonts only (no
   external font/CDN dependency). Pieces: batch controls (seed input, "new
   batch", "run the loop" — mirrors REKON's pattern intentionally), headline
   metric cards (accuracy, false-auto-close rate called out as the safety
   number with green/red coloring, throughput, records processed), an
   invariants panel (green HOLDS / red FAILED per check, not hidden), a
   per-pass engine-trace panel (timing + hit count per pass, monospace
   log-style), per-fault-class and per-rule tables, an exceptions panel
   grouped by reason category showing each case's real `reason_detail` text
   (not a bare label), a standing "known limitation" callout for the
   international_fx gap (always visible, not conditional on data), and a
   Q&A chat panel with quick-question chips calling `POST /ask`.
   `API_BASE` is a single constant at the top of the `<script>`, currently
   `http://localhost:8000` — change it to the deployed URL once that exists,
   no other code change needed.
   **Actually verified, not just written**: started the API with `uvicorn`,
   hit `POST /batches`, `POST /batches/{id}/run`, `GET /batches/{id}`, and
   `POST /batches/{id}/ask` with the exact same request shapes the frontend
   JS sends, and confirmed every field the JS reads (`invariants`,
   `pass_timings_ms`, `pass_hit_counts`, `eval.per_fault_class`,
   `eval.per_rule`, `decisions[].reason_detail`, the `/ask` response's
   `answer` field) is present with the expected shape in the real response —
   e.g. a real run returned `overall_accuracy: 1.0`,
   `false_auto_close_rate: 0.0`, all four invariants `true`, and the
   `/ask` "what does it refuse to guess on?" call returned a real,
   data-grounded answer (26 abstained cases). Server was stopped after
   verification, per instructions not to leave it running. The API needed no
   changes for this step — every field the frontend wanted was already
   present.
7. **Video**: storyboard already fixed (see ARCHITECTURE.md) — script against
   whatever is actually built, don't invent claims ahead of the code. This is
   the one remaining step that isn't automatable — it needs Vani to actually
   record herself.

## Open items / things to verify before submission

- ~~`orders_source.py` not built~~ — **done.** `generate.py` accepts
  `order_mode="synthetic"|"live"`; default is synthetic (unchanged
  seed-42 baseline). To use real orders: `generate_dataset(order_mode="live")`
  with `.env` credentials present.
- ~~Live-mode verified at small scale only~~ — **resolved with a real
  larger-scale test, not an extrapolation.** Ran `load_orders(40,
  mode="live")` against the real API: **40/40 succeeded in 6.57s (164ms/order
  avg), no rate-limit errors.** This is faster per-order than the earlier
  7-order sample (~300ms/order) and revises the earlier extrapolation down:
  at this rate the full 207-case batch would take roughly ~34s sequentially,
  not 45-50s. Still not run at the full 150-200+ scale — if live mode is used
  for the real submission, run the full batch once ahead of time (not first
  during video recording) to rule out a rate-limit that only appears at
  higher volume.
- **Deployment itself is still pending and needs the user.** The API layer
  is built and locally verified (see build-order step 5) with a `Procfile`
  ready for Render/Railway/Fly.io, but actually creating a hosting account
  and deploying requires the user's own credentials — not something to do
  unattended. Once deployed, warm/test it repeatedly before relying on it —
  REKON's own live console was observed hanging on "loading console…" during
  our research, a real, previously-observed failure mode, not a hypothetical.
- ~~README needs a one-command "how to run"~~ — **done.** Root `README.md`
  rewritten with quick-start (CLI, tests, API+frontend), the AI-judgment
  boundary, the disclosed limitation, and the data-source honesty statement.
  Independently re-verified in the coordinating session (not just trusted
  from fork reports): 38/38 tests pass, `python3 run.py` produces the same
  207-case / 100%-accuracy / 0%-false-auto-close result, and a live
  API+frontend smoke test (uvicorn + curl against `/batches`, `/run`, `/ask`)
  returned correct real data.
- **Security/code-quality review — done.** Full `reconciler/` package,
  `run.py`, `frontend/index.html`, `Dockerfile` reviewed. One real,
  moderate-severity issue found and fixed: `POST /batches` had no guard on
  `order_mode="live"` — combined with wide-open CORS and no auth, any caller
  of a deployed instance could have forced the server to spend the account's
  real Razorpay credentials creating live test orders, with no rate limit.
  **Fixed:** `reconciler/api.py` now rejects `order_mode="live"` with a 403
  unless `ALLOW_LIVE_ORDERS=1` is explicitly set in the environment — off by
  default, so a deployed judge-facing instance can't trigger it accidentally.
  Verified via real `curl`: 403 without the flag, and confirmed (with a
  deliberately fake credential pair) that a live-mode failure returns a bare
  "Internal Server Error" to the client with no secret or exception detail
  leaked — FastAPI's default (non-debug) error handling already covered this
  correctly; the traceback itself never printed the fake secret value into
  the server log either. All 38 tests still pass after the fix.
  Everything else checked out clean: no secret-handling issues elsewhere,
  `qa.py`'s question handling is pure string/regex matching (no eval/exec/
  injection surface), `.gitignore` correctly excludes `.env`/`out/`/
  `__pycache__/` and `git status` confirms `.env` is not staged, and
  `engine.py`/`api.py` code quality holds to the project's style rules
  (short methods, no deep nesting) despite being touched by several separate
  build sessions.

## Neon database — confirmed live

The user's real Neon connection string is in `.env` as `DATABASE_URL`
(gitignored, confirmed not staged). Verified directly against it, not just
assumed: connected (`PostgreSQL 18.6`), created a real batch, ran full
reconciliation (207 cases, 100% accuracy), killed the server process,
started a brand-new one, and fetched the same batch back with identical
data — restart-survival proven against the real production database, not
just the local Postgres/SQLite stand-in the earlier build fork used.

## Deployment — DONE. Live at https://tieout-lemon.vercel.app

The project is named **TieOut** (a real accountant's term — reconciling two
records against each other), propagated across `README.md`,
`frontend/index.html` (title + header), and `docs/ARCHITECTURE_SUBMISSION.md`.

Deployed via the Vercel CLI using a personal access token (`vcp_...`, stored
in `.env`, gitignored, never committed): `vercel link` created project
`vani-goyals-projects/tieout`, `DATABASE_URL` (the real Neon string) was set
as a production environment variable, then `vercel deploy --prod` shipped
it. Aliased URL: **https://tieout-lemon.vercel.app**.

**Verified against the live production deployment itself, not just locally:**
- `GET /` → 200, real frontend HTML, correct `<title>TieOut</title>`
- `POST /batches` → real batch created against real Neon
- `POST /batches/{id}/run` → 207 cases, 100% accuracy, 0% false-auto-close
- `POST /batches/{id}/ask` → correct, data-grounded answer
- Fetched the same batch back via a **separate subsequent request** — this
  is the real, on-platform equivalent of the earlier restart-survival test:
  confirms Postgres-backed state survives across genuinely different
  serverless invocations, which was the entire point of adding the
  database in the first place.

*(Fallback, unused but kept in the repo: `Procfile` (Render/Railway) and
`Dockerfile`+`.dockerignore` (Google Cloud Run) — not needed since Vercel
worked cleanly, not deleted in case Vercel ever needs to be abandoned.)*

## Frontend redesign pass (after user UX/aesthetic critique) — ✅ DONE, real pixels verified

The user flagged the deployed frontend as looking bad both aesthetically and
from a UX standpoint (screenshot of the empty pre-run state showed six
undifferentiated panels, most saying "run a batch to see X"), and asked
whether the vanilla HTML/CSS/JS approach was the wrong call versus a React/
Next.js rebuild. Advisor consulted per the user's explicit request: the stack
was not the problem — layout, information hierarchy, and staging were.
Rebuilding in React/Next would not by itself fix a flat, undifferentiated
layout, and would add a build step for no functional gain on a page that's
already just rendering API JSON. Stayed with a single self-contained
`frontend/index.html`, no framework, no build step — same file, same API
contract, zero changes to `reconciler/api.py`.

**What changed, concretely:**
- **Pre-run empty state eliminated.** Previously the full six-panel dashboard
  skeleton rendered immediately, mostly showing placeholder "run a batch to
  see X" text. Now `#results` stays `hidden` until a run actually completes;
  the pre-run screen is one centered block: a one-sentence description of
  what TieOut does, plus the seed input and the two batch-control buttons as
  the only visible next action.
- **Visual hierarchy after a run.** The four headline metric cards (accuracy,
  false-auto-close rate, throughput, records) sit in their own `zone-headline`
  block with a distinct tinted background and larger type (32px values, up
  from 26px). Supporting detail — invariants, engine trace, the two
  scorecard tables — moved into visually quieter `section.compact` panels
  (smaller padding, smaller font, page-background fill instead of panel
  fill) grouped under a "How it decided" zone label.
- **Known-limitation panel repositioned.** Moved from before any data (read
  as a warning banner) to after the exceptions section, grouped into a "What
  needs a human" zone alongside exceptions — now reads as an earned
  disclosure following the evidence, not a caveat preceding it.
- **Real zone grouping with spacing.** Four zones total: headline results →
  how it decided → what needs a human → ask it, each with its own
  `zone-title` label and margin between zones, replacing six uniform panels
  stacked with identical spacing.
- **Progressive reveal on run.** The engine-trace lines now fade/slide in
  one at a time (staggered `setTimeout`, ~140ms apart) instead of popping in
  as a static block — called out by the user as the best on-camera moment
  for the pitch video, previously wasted.
- Tailwind was considered (item 6 in the task) but not used — a hand-written
  CSS pass covered the hierarchy/spacing work directly without adding an
  external CDN dependency to a page that otherwise has zero third-party
  script/style dependencies.

**Verified with real rendered pixels, not just API responses** — the earlier
build had been burned once on "the JSON is correct" being treated as
equivalent to "the page looks right." This time: started
`uvicorn reconciler.api:app` locally, served `frontend/` via
`python3 -m http.server 8080` (Chrome can't load `file://` pages through the
extension), connected the Claude-in-Chrome browser tool, and drove the actual
page end-to-end:
- Pre-run hero screenshot confirmed: single centered tagline + controls, no
  placeholder panels.
- Generated a real batch (`POST /batches`) via the UI, confirmed the hero
  stays up with the batch-info status line updated in place, "run the loop"
  enabled.
- Ran the batch via the UI (`POST /batches/{id}/run`, real 207-case result,
  100% accuracy, 0% false-auto-close), screenshotted the headline-card zone,
  the how-it-decided zone (compact secondary panels, all four invariants
  HOLDS, per-pass trace, both scorecard tables), the what-needs-a-human zone
  (grouped exception cards by category, `books_duplicate_invoice_collision`
  abstention cases rendering correctly, limitation panel now positioned
  after exceptions), and the ask-it zone.
- Clicked a real Q&A chip ("what's the match rate?") and confirmed a real,
  data-grounded answer rendered in the chat log.
- Clicked "new batch" after a completed run and confirmed the page correctly
  resets back to the clean hero state (results re-hidden, run button
  re-enabled) — this exercises `resetPanels()`/`setHasRun(false)`, the one
  path most likely to have a stale-state bug.
- All 41 existing tests still pass (`python3 -m unittest discover -s tests`)
  — expected, since no Python file was touched.
- Local API and static-file servers used for verification were stopped
  afterward; no process left running.

This redesign, and every frontend change since, has been deployed to and
verified against the live production URL directly (not just locally) — see
"Auto-ship workflow" below for why that's now the default, not a one-off.

## Auto-ship workflow (standing rule, since 2026-09-04)

The user gave a standing instruction: any code change to this repo gets
committed (plain message, no AI attribution trailer — see the git-commit
memory), pushed to `origin main`, and deployed to Vercel production
automatically, with no confirmation step first. This supersedes the earlier
"no commits without my approval" default *for this project specifically*.
Every change described below in "Post-redesign UI iterations" was shipped
this way — deployed, verified live in a real browser via the Claude-in-Chrome
tool, then committed and pushed.

## Post-redesign UI iterations

Three follow-up fixes since the redesign pass above, each deployed and
verified against https://tieout-lemon.vercel.app directly:

1. **Exceptions list collapsed.** Each fault category in the exceptions panel
   previously rendered every escalated case in full (~90+ cards, long
   scroll). Now shows the first 3 with a "show all N" toggle per category —
   no data removed, confirmed by expanding a real category (11/11
   `books_duplicate_invoice_collision` cards) live.
2. **Seed tooltip fixed.** The seed field's native `title` tooltip was
   correct in markup but unreliable in practice (slow hover delay, easy to
   miss) — replaced with a custom CSS tooltip on the `?` icon that appears
   instantly. (This field was then removed entirely — see next item.)
3. **Seed input removed; replaced with recent-runs history + a benchmark
   button.** The user correctly flagged that asking someone to remember a
   seed number to revisit a past run is bad UX, when batches are already
   persisted in Postgres. Consulted advisor: agreed, killed the input, kept
   the underlying `seed` param. Now: a **"reproduce the seed-42 benchmark"**
   button (the one legitimate surviving use — matching the exact numbers
   cited in README/docs), and a **recent-runs list** (localStorage, last 5
   runs as clickable chips, reload any prior batch via the existing
   `GET /batches/{id}` — deliberately no new backend endpoint). Verified live
   with the scenario that actually matters: ran two different batches,
   clicked back into the older one via its chip, confirmed the dashboard
   correctly repopulated with that exact run's original data (matching
   throughput number, not just matching case count).

4. **Non-technical-user overhaul: real navbar + DB-backed history tab,
   seed/ID clutter removed, data preview & download, collapsed technical
   detail.** The user flagged that a naive/non-technical user shouldn't see
   seed numbers, batch IDs, or raw engine internals as the primary UI, and
   that "previous runs must persist in DB" needed to actually be visible,
   not just true internally (the old "recent runs" list was localStorage,
   last 5 only, not the real persistence layer already built in step 5).
   Consulted advisor before building (per the user's explicit ask) — plan
   held, but advisor caught real bugs before they shipped:
   - `GET /batches` for history would have pulled every batch's full
     dataset/run_result JSON blob over the wire (200-500KB each) just to
     list them — fixed by adding six nullable summary columns
     (`payments_count`, `cases_count`, `accuracy`, etc.) to `batches` via a
     guarded `ALTER TABLE ... ADD COLUMN` (each in its own transaction, so
     "column already exists" on one doesn't abort the rest) in
     `db.make_engine()`, so `list_batches()` now selects scalar columns
     only, never the blobs.
   - Rows written before this change have those columns NULL — added
     `_backfill_summary_columns()`, which runs once per row (computes from
     the existing blobs, sets `cases_count`, then never selects that row
     again) so old local and production batches don't render blank in
     history.
   - `created_at` came back tz-naive from both Postgres and SQLite, which
     JS parses as local time — every history row would have read ~5:30 in
     the past for an IST viewer. Fixed by attaching UTC explicitly before
     `.isoformat()`.
   - The new `GET /batches/{id}/data` endpoint (for the "what are we
     working with" preview/download) deliberately excludes `ground_truth`
     — that's the answer key, and a demo showing it next to the raw data
     would hand a judge the wrong question to ask.
   - History defaults to completed runs only (`WHERE run_result_json IS NOT
     NULL`) — half-created batches from an abandoned session aren't
     "history" to a non-technical viewer.
   Frontend: real navbar with New run / History tabs; the seed-42 benchmark
   button and localStorage recent-runs list are both gone (the one
   legitimate use of seed-42 — reproducing the exact README/docs numbers —
   is still `python3 run.py`, unaffected by any of this); a three-stage New
   Run flow (hero → "N transactions generated" card, no batch ID/seed shown
   → results) with a data-preview modal (Payments/Settlements/Books tabs,
   first 8 rows, CSV and full-JSON download) reachable both before and
   after reconciling; results now lead with a one-line plain-English verdict
   with the rule/invariant/scorecard detail collapsed behind a "show
   technical details" toggle; History tab lists real DB-backed past runs
   (date, transaction count, accuracy badge) and loading one re-renders the
   exact original results plus its own data preview.
   **Caught one real CSS bug during verification, not just written and
   assumed correct**: `#stage-hero`/`#stage-ready`/`#stage-results` each set
   their own `display` by ID selector, which outranks the browser's default
   `[hidden]{display:none}` — so on first load, the hero and the "data
   ready" card rendered simultaneously, stacked. Fixed with an explicit
   `#stage-x[hidden]{display:none!important}` override; caught by an actual
   screenshot via Claude-in-Chrome, not by reading the code.
   **Verified live in a real browser**, full state machine: generate → data
   preview modal (both Payments and Settlements sub-tabs render real rows)
   → reconcile → plain-summary + collapsed/expanded technical detail →
   History tab (4 real past runs, correct dates, no timezone drift) → view
   a historical run (confirmed it's genuinely that run's own data — a
   *different* exception's order_id/diff showed up, not the last-viewed
   run's) → view that historical run's data preview → start a new run
   (clean reset to the hero, no stale state) → asked a real Q&A chip
   question and got a real data-grounded answer back. No console errors at
   any point. All 43 tests pass (41 prior + 2 new `list_batches`/backfill
   tests).

5. **Data preview made automatic, no modal.** The user pushed back on the
   modal-based preview from item 4: on a non-technical user's screen, having
   to click "Preview & download data" then read it inside a popup was an
   extra, avoidable step. Changed to: the preview panel (tabs, table,
   download buttons) now renders automatically, inline on the page, right
   below the "N transactions generated" card the moment a batch exists — no
   click needed. On the results page (already dense with metric cards,
   exceptions, Q&A) it stays behind a "View data" toggle instead of
   auto-showing, since that page has more competing content; clicking it
   opens the same panel inline (not a popup) at the top of the results view
   and smooth-scrolls it into place. Also added real pagination (20 rows/
   page, Previous/Next, "Page X of Y — N records total") plus a bounded,
   independently-scrollable table body with a sticky header, so the actual
   scale of a batch (hundreds of records) is genuinely browsable in place,
   not just an 8-row taste. Caught and fixed one real correctness bug while
   at it: the CSV download had been hardcoded to always export payments
   regardless of which tab (Payments/Settlements/Books) was active — now
   exports whichever record type is currently showing. Verified live:
   generate → preview auto-appears with real data, no click → paginate
   through Payments (12 pages) and Settlements (10 pages), tab switch resets
   to page 1 → reconcile → preview correctly collapses (no floating leftover
   panel) → "View data" toggle opens/closes correctly and relabels itself
   ("View data" ↔ "Hide data") → "start a new run" resets to a clean hero
   with no stale panel. No console errors at any point. All 43 tests still
   pass (no backend changes this round).

6. **Full results-page readability overhaul, prompted by a real PDF export
   of the deployed page** ([to1.pdf], shared by the user): 115 flagged cases
   rendered as one stacked text card each read as "a giant slob of text,"
   the Q&A chat only existed at the very bottom of a long page (findable
   only by scrolling past everything else), and the per-fault-class/
   per-rule/invariants summary was hidden behind the "show technical
   details" toggle from item 4 — exactly backwards from what a non-technical
   viewer wants first (the numbers) versus what they want to drill into
   (individual flagged cases). Researched actual UX sources before touching
   code (NN/g's data-table guidance, Pencil & Paper's enterprise-table
   pattern analysis, current fintech-dashboard exception-queue practice —
   dense filterable/sortable tables, pagination over infinite scroll,
   "exception-first" surfacing) rather than redesigning from instinct alone.
   Consulted advisor on the plan before writing code, per the user's
   explicit ask; advisor caught two ordering bugs during implementation
   before either shipped:
   - **Flagged items**: replaced the per-category card stack with one
     compact table (Category badge / Order ID / Reason), category filter
     chips with live counts, an order-ID search box, and real pagination
     (25/page). This is what actually scales past a handful of cases — the
     DOM holds one page's worth of rows whether the batch has 115 flagged
     cases or 15,000. (Caveat, stated plainly rather than oversold: this
     fixes *rendering*, not payload — `GET /batches/{id}/data` and the run
     endpoint still return every record/decision as JSON, so a genuinely
     10k+-record batch would need paginated *endpoints* too. Not done here;
     correctly scoped as future work, not claimed as solved.)
   - **Summary promoted to always-visible.** Per-fault-class accuracy,
     per-rule scorecard, and the four consistency-check invariants (now
     rendered as a compact pill row instead of a bulleted dot-list) sit
     directly under the headline metric cards with no toggle — this is what
     "summary of the reconciliation" meant per the user's own framing. Only
     the per-pass engine-trace timings (genuinely internal, microsecond
     numbers meaningless to a non-technical reader) stayed behind a small
     "show engine internals" toggle, now demoted below the flagged-items
     section rather than sitting above it.
   - **Q&A moved to a floating chat widget** (fixed bottom-right launcher +
     panel, standard Intercom/Zendesk-style pattern) — reachable from any
     scroll depth on the results page instead of requiring a scroll to the
     very bottom. Shown only while a run's results are the active view;
     hidden on the hero/ready stages and on the History tab (its
     fixed-position panel would otherwise float over content unrelated to
     any run). Real bugs caught in this specific piece, before and during
     verification: (a) the chat panel's `position:fixed` visually overlaps
     the exceptions table's centered pagination footer on ordinary laptop
     widths (confirmed live at 1263px) — checked whether this was a
     functional blocker, not just a visual one: the "Next" button stayed
     genuinely clickable throughout (verified by paging forward with the
     panel open), so left as-is rather than over-engineering a redesign
     around a cosmetic near-miss that real chat widgets exhibit too; (b) a
     history-tab visibility bug where `closeChatPanel()`'s own re-show logic
     (keyed on whether the results stage is still active underneath, which
     tab-switching alone doesn't change) would silently undo the "hide the
     fab on History" line right after it — fixed by reordering so the
     explicit hide runs last.
   - Two null-reference bugs caught and fixed **before** browser testing by
     re-reading the state-machine implications of a rebuildable DOM
     skeleton (the zero-flagged-cases empty state destroys and later
     rebuilds the filter/table/pagination markup): calling
     `renderExceptionFilters()` before confirming the skeleton exists, and
     duplicating the skeleton in both static HTML and JS such that the
     JS-owned rebuild path would never get its event listeners bound on the
     very first run. Consolidated to one JS-owned skeleton
     (`ensureExceptionsSkeleton()`) as the single source of truth.
   **Verified live in-browser**, full pass: generate → reconcile → Summary
   visible immediately (no click) → chat fab visible immediately (no
   scroll) → flagged-items category filter ("Disputed (8)") → combined
   filter+search narrows to the single matching case → chat panel open →
   asked a real quick-question chip, got a real data-grounded answer →
   confirmed "Next" pagination still clickable with chat panel open → chat
   closed, fab reappears → engine-internals toggle expands/collapses →
   History tab correctly hides the chat fab/panel → opened a *different*
   historical run and confirmed the flagged-items filters/search reset
   correctly against that run's own data (not stale state from the
   previous one). No console errors at any point. All 43 tests still pass
   (no backend schema changes this round beyond the `/batches` reliability
   fix below).

**Separately, a real production bug reported by the user**: History tab
showed "Couldn't load history: 500" on the live deployment. Root-caused,
not just patched blind — pulled every production `batches` row directly
from Neon and verified all 14 were structurally intact (valid JSON,
`cases_count` backfilled, no orphaned rows), and the endpoint was already
back to 200 by the time it was checked. That combination (data provably
fine, error already gone, endpoint touches Postgres on every cold
request) points at a classic serverless-Postgres failure mode: Neon
suspends its compute when idle, and the first query after waking can
occasionally hit a stale/dropped connection. Fixed with
`pool_pre_ping=True` on the SQLAlchemy engine (`reconciler/db.py`) — the
standard, minimal mitigation (SQLAlchemy tests the connection with a
cheap `SELECT 1` before handing it to a request, transparently
reconnecting if it's dead, instead of surfacing that as a 500). Low risk:
one line, no schema change, all 43 tests still pass against SQLite.

Also consulted advisor on whether the vanilla-HTML approach itself was
creating friction for adding features like these — answer: no. Recent
feature costs (15-60 lines each) show no structural friction; migrating to
Next.js would mean rewriting `vercel.json`'s routing (currently one Python
function serving both API and page) with real risk to the live URL under
auto-ship, for a page whose actual friction points (one function doing real
work, the deploy-verify loop's cold-starts) aren't framework-shaped anyway.

`docs/VIDEO_SCRIPT.md` has not been updated to match these UI changes yet —
deliberately deferred, per the user, to a single pass later rather than
touched incrementally with each UI iteration.

Two small polish fixes shipped without a STATUS.md entry at the time
(caught up here): `.run-card` was missing `cursor: pointer`, and viewing a
past run from History left "New run" highlighted in the nav instead of
"History" — fixed by extracting `setActiveNavTab()` from `switchTab()` so
the History "View results" handler could set nav state without going
through the New-Run-flow logic. Also clarified the results-page "Speed"
metric card, which read as an ambiguous "84,200/s" with no indication of
what was actually measured — now leads with the real `wall_time_seconds`
("Time taken") and shows the extrapolated rate as an explicitly-labeled
`≈ N/s at this rate` secondary line.

### Source-record drill-down + quarantine visibility (2026-09-04)

Prompted by the user walking through the exceptions table from an
accountant's point of view: "AI has flagged these things, what are my next
steps, using the current UI am I able to do those easily, is there any
friction?" Checked against the actual code rather than guessing, and found
two real gaps, not just polish:

- **Quarantined cases (structurally malformed input — missing order_id,
  non-positive amount, unparseable date) were completely invisible.**
  `initExceptions` only pulled `decision === "escalate"` rows; quarantine is
  a third decision type that never entered the flagged table. A batch could
  have malformed records and the UI would never show them existed.
- **Every flagged row showed only a category badge and one sentence, never
  the underlying records.** `Decision.record_ids` (linking a decision back
  to the real payment/settlement/invoice rows) existed in the backend and
  was already sent to the frontend in every run payload — just never used.
  There was also no way to search by order ID in the data-preview tab, so
  acting on "amount mismatch" or "missing settlement" meant paging through
  raw tables hoping to spot the right ID.

Fixed both. Flagged rows and quarantine rows are now clickable — clicking
one expands an inline detail row (no modal, consistent with the rest of
this UI) that resolves `record_ids` against the already-fetched dataset
and shows the actual payment/settlement/invoice cards. Quarantined cases
get their own section ("Isolated at ingest — not a transaction problem")
with the same drill-down, explicitly framed as a data-quality issue for
whoever owns the upstream export, not something to reconcile.

Bug caught during in-browser verification, not code review: exceptions and
quarantine rows initially shared one `expandedCaseId` variable. Expanding a
quarantine row after an exceptions row left the exceptions section showing
stale (still-expanded) DOM, since only the clicked section's own render
function ran. Fixed by giving each section an independent expansion cursor
(`expandedExceptionId` / `expandedQuarantineId`) — confirmed live that both
can now be open at once with correct, distinct content.

Separately, in the course of answering the user's question about where
`order_id` comes from and how it relates to `payment_id`: the settlement
preview table was missing `order_id` and `payment_id` columns even though
`SettlementLine` always carried both (they were already in the CSV/JSON
export, just never rendered on screen). Added both — `payment_id` shows
"— (ambiguous)" when null, which is itself informative for the
`multi_payment_ambiguous` case.

Also moved the "Known limitation — disclosed on purpose" FX banner off the
results page into the README, per the user's request. One nuance surfaced
while doing this: there is no honest way to add an in-table signal marking
*which* `amount_mismatch` rows are FX-caused, because by the time a payment
reaches the reconciler its currency is already INR with no FX marker — the
engine has no more information than the UI does. Tagging specific rows
would require reading the generator's ground truth, which would defeat the
point of the exercise. Said so plainly in the README rather than
implying a distinction the UI can't actually back up.

Deferred, explicitly queued for a follow-up: "what should I do next" hint
text per fault category (16 categories) in the flagged-items table.
Deliberately not bundled into this change to keep it reviewable — the
drill-down is the fix that closes the loop for every category by giving
real numbers to check; per-category guidance text is a separate, cheap
addition once the user has seen this land.

**Verified live in-browser** end to end: generated a batch, reconciled,
confirmed the settlement preview shows order_id/payment_id, expanded an
`amount_mismatch` row and confirmed the payment/settlement cards show the
real conflicting amounts, expanded a quarantine row and confirmed it shows
the actual malformed record (e.g. a negative amount), confirmed both stay
independently expanded, confirmed collapse works, confirmed the same drill-
down works when viewing a past run from History. No console errors. All 43
backend tests still pass (no backend changes this round — frontend and
README only). Committed as `a5f82bf` and deployed to production
(`https://tieout-lemon.vercel.app`); `curl` against `/batches` and the
served HTML confirmed the deploy went live.

### Brand-mark navigation shortcut + nav-tab contrast fix (2026-09-04)

Two small reported issues: the TieOut logo/name in the header wasn't
clickable ("should take us to the new run page"), and the New run/History
nav pills' selected and hover states were "so dull it's hard to even see
what's selected". Checked the actual colors: active background was
`--panel-3` (`#1e232b`) against the tab strip's own `--panel-2`
(`#191d23`) — two near-identical dark shades, and hover only changed text
color with no background change at all.

Brand mark/name now behaves like clicking the "New run" nav pill itself —
deliberately *not* the same as "Start a new run" (which resets the batch);
clicking the logo mid-flow (e.g. from "ready" or "results" stage) returns
to whatever's currently in the New Run tab rather than discarding it.
Nav-tab active state now uses the same solid accent-blue treatment as
filter chips elsewhere in the UI (`background: var(--accent); color: #fff`
instead of a barely-different dark shade); hover gets its own visible
background change independent of active state.

Committed as `be90711`, deployed, verified live (brand click preserves
in-progress batch state when navigating away and back; active-tab pill is
now clearly a solid accent color in a zoomed screenshot).

### Per-category "what to do next" hints (2026-09-04)

Follow-up explicitly queued from the drill-down work above, once the user
had seen it land: the drill-down shows *what the real numbers are*, but not
*what to actually do about it*. Added a `CATEGORY_HINTS` map in the
frontend keyed by `reason_category`, rendered as a highlighted "Next step"
block above the source-record cards in the same expand-on-click panel.

Scoped to the 11 categories that can actually reach the flagged/quarantine
sections — the 10 `escalate` reason_categories the engine assigns
(`amount_mismatch`, `multi_payment_ambiguous`, `missing_settlement`,
`duplicate_settlement`, `refund_mismatch`, `disputed`, `high_value_gate`,
`books_duplicate_invoice_collision`, `books_missing_invoice`,
`books_amount_mismatch`) plus `quarantine` — verified against the literal
`Decision(...)` call sites in `engine.py`, not just taxonomy.py's fault
list. The 4 `auto_close`-only fault types (`clean_match`, `rounding_noise`,
`refund_clean`, `books_clean_match`) never surface in either section, so
they get no entry — a hint there would be dead code. `international_fx`
has no distinct `reason_category` of its own (the engine folds it into
`amount_mismatch`, which is the whole disclosed limitation); its hint text
lives inside the `amount_mismatch` entry instead, which turned out to be a
better home for that disclosure than the static banner ever was — it shows
up in context, on the specific rows a user is actually investigating,
instead of as prose at the bottom of the page nobody reads mid-task.

Caught and fixed one real bug while verifying live, not in code review:
a quarantined record with a genuinely non-numeric `amount` (the
malformation itself) rendered as literal `₹NaN` in the drill-down card.
`money()` now checks `Number.isFinite` and shows `"(invalid amount)"`
instead — a fix that helps everywhere the formatter is used, not just
quarantine.

Verified live for both an `escalate` category (Disputed) and quarantine;
confirmed hint text renders above the source records as intended. All 43
backend tests pass (frontend-only change). Committed as `c46cac2`,
deployed, confirmed live via curl.

### Randomized and configurable batch generation counts (2026-09-04)

Two asks from earlier in the session, picked back up once the user
confirmed they wanted them: "the number of payments/settlements/invoices
is always the same across runs — can we randomize it within a range?" and
"let the user optionally enter total transaction count and per-fault-type
counts."

The hard constraint going in: `generate_dataset(seed=42)` with no
arguments is the documented "207 cases, seed 42, 100% accuracy" verified
benchmark cited throughout this file and the README, and `run.py`'s CLI
path plus the existing test suite all call it that way. Any change had to
leave that call byte-identical. Captured the exact baseline before
touching anything (case/payment/settlement/invoice counts, first and last
payment IDs, first settlement/invoice IDs) and asserted it in a new
`tests/test_generate.py` — verified unchanged after the refactor.

`generate_dataset()` gained one optional parameter, `fault_counts` (a
`{fault_type: count}` override dict), but stays otherwise pure and
deterministic given its arguments — it does not itself decide whether to
jitter, scale, or use defaults. That policy lives in two new standalone
functions: `jitter_taxonomy_counts(seed, spread=0.3)` (each class bumped
up by a random amount, capped at +30%, **never down** — `_build_quarantine`
cycles through 5 distinct malformation types across its 5 default cases,
so jittering that class below 5 would silently stop exercising some of
them) and `scale_taxonomy_counts(total_cases)` (proportional, no
randomness — deliberately deterministic, since a user who asks for a
specific total wants predictable sizing, not more variety layered on top).

`POST /batches` gained optional `fault_counts` and `total_cases` fields,
resolved in a new `_resolve_fault_counts()`: neither given (the plain
"Generate sample data" click, unchanged for anyone who never opens the new
panel) → jittered, so repeat clicks now visibly vary in size.
`total_cases` alone → scaled, no jitter. `fault_counts` (with or without
`total_cases`) → explicit per-class values win over whatever `total_cases`
would have scaled them to; unknown fault-type keys are rejected with a 400.
A new `GET /taxonomy` endpoint reflects `taxonomy.py`'s fault-type catalog
(description, default count, expected decision) so the frontend doesn't
duplicate that list.

`total_cases` is clamped to `[20, 1000]`. Per earlier advisor guidance —
"pick the ceiling from what the payload can actually carry... test against
the *deployed* function, not locally" — 1000 was verified directly against
the live Vercel deployment before being treated as final, not just assumed
safe from local timing: a `total_cases=1000` batch generated in ~0.85s,
reconciled in ~1.6s at 100% accuracy, and its `/data` response was ~660KB
— all comfortably inside serverless limits. If this ever needs to go
higher, that payload size (not compute time) is the thing to re-check.

Frontend: a collapsed-by-default "Customize this batch (optional)" panel
below "Generate sample data" — deliberately not the default view, matching
this project's standing "non-technical user first" UI principle. A total-
transactions field plus a scrollable list of all 16 fault types (name,
plain-English description, count input defaulting to a placeholder showing
the current default), fetched lazily from `/taxonomy` only on first
expand. Every field left blank is simply omitted from the request body, so
the default jittered behavior needs no special-casing on the frontend.

**Verified end-to-end, live**, both locally and against the deployed
function: generated a batch with `total_cases=400` and an explicit
`quarantine=10` override locally in Chrome — got 397 total cases with
exactly 10 quarantine rows rendered in the flagged/quarantine UI from the
previous change, no console errors; separately hit the deployed
`/batches`, `/batches/{id}/run`, and `/batches/{id}/data` endpoints
directly via curl at the `total_cases=1000` ceiling (see above). All 55
backend tests pass. Committed as `d4f4f4f`, deployed, confirmed live.

## Ground-truth transparency, discoverability fixes, and a pluggable LLM layer (2026-09-05)

**Ground-truth transparency.** A new `GET /batches/{id}/ground_truth`
endpoint (available as soon as a batch is generated, no run required)
serves the answer key — `case_id`, `fault_type`, `expected_decision`,
`expected_reason_category` — straight from `GroundTruthCase`, separately
from `/data`, which still deliberately excludes it. A 4th "Expected
outcomes" tab in the existing data-preview component surfaces it (and gets
CSV/JSON download for free, since that component already had it). A
collapsed "Compare against expected outcomes ▸" toggle in the results view
joins that against the run's own decisions client-side, case by case, with
a mismatches-only filter (defaulted on, since that's where
`false_auto_close_rate`'s meaning was previously invisible — a percentage
with no way to see *which* cases it counted) and drill-down into the real
source records. README gained a "What accuracy means here" section
explaining this is a validation run against a known-correct batch, not a
production guarantee — the same distinction the metrics-row caption states
in one line.

**History-page slowness root-caused and fixed.** Not a payload or N+1 issue
— `list_batches()` was already lightweight. The actual cost: schema setup
(`_ensure_summary_columns`) unconditionally attempted up to 6 `ALTER TABLE`s
plus a backfill on every engine construction, i.e. every serverless cold
start. Now it does one introspection call first and only touches columns
actually missing. A fabricated legacy-table test confirms a genuinely stale
schema still gets migrated correctly.

**"Discard & start over" added to the pre-run screen** (`#stage-ready`),
reusing the existing `resetToNewRunHero()` — previously the only way off
that screen if you didn't like the generated batch was a page reload.

**Chat entry point made discoverable.** The floating launcher was an
unlabeled icon-only circle — easy to miss entirely (reported after a user
loaded a run via History and couldn't find it). Now labeled ("Ask a
question"), plus a second, inline "Ask a question about this run" button in
the results toolbar next to View data / Start a new run.

**LLM layer made multi-provider and given one real use beyond phrasing.**
`reconciler/llm.py` is a new small client shared by `notes.py` and `qa.py` —
`LLM_PROVIDER` selects `anthropic` / `openai` / `gemini` /
`openai_compatible` (any OpenAI-wire-format host via `LLM_BASE_URL` —
Groq, Together, OpenRouter, a local Ollama), or it auto-detects from
whichever of `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` is
set, preserving the original zero-config behavior. `notes.py` was refactored
onto this client with no behavior change. `qa.py` gained one new real
capability: a genuinely unrecognized chat question now falls through to a
free-form LLM answer — scoped to only the run's aggregate summary numbers,
never a raw record, instructed to say "I don't know, check Exceptions"
rather than guess — instead of the old static "I don't have a canned answer"
message. The API's `/ask` response gained a `source` field
(`"template"` | `"llm"`), and the chat panel labels the free-form case
explicitly, so this new capability follows the same "disclosed on purpose"
principle as everything else here rather than blending in silently the way
`notes.py`'s cosmetic rephrasing deliberately does. 17 new tests
(`tests/test_llm.py` plus additions to `test_qa.py`/`test_api.py`), all
without network access — real provider calls are only exercised with a
deliberately fake key to prove they fail gracefully. No key is set in this
deployment as of this writing; setting one is a deliberate call left to
Vani (cost, added latency, demo-failure risk on a live call), not something
changed here.

## Deterministic demo seed + finalized pitch-video script (2026-09-05)

**`DEMO_FIXED_SEED` env var added** (`reconciler/api.py`, next to the
existing `_ALLOW_LIVE_ORDERS` pattern) — operator-only, off by default, no
UI exposure. When set, any `/batches` request that doesn't pass its own
`seed` reuses this one instead of the normal time-based one, so repeated
"Generate sample data" clicks (including with customize-panel inputs typed
on top) reproduce byte-identical output. Exists purely so the pitch video
can be rehearsed and re-shot against fixed narration instead of a different
random batch every take. 3 new tests (`TestDemoFixedSeed` in
`tests/test_api.py`); 80/80 backend tests passing.

**Verified live on production, then reverted**: set `DEMO_FIXED_SEED=42` in
Vercel's prod env, redeployed, confirmed two separate "Generate sample
data" calls (one plain, one with `total_cases=150`, matching what the
customize-panel demo beat will do) came back byte-for-byte identical via
`/batches/{id}/data`, then removed the env var and redeployed again —
confirmed production is back to fresh-seed-per-request. Production is NOT
left in demo mode.

**`docs/VIDEO_SCRIPT.md` fully rewritten** against the actual current
product (the previous version referenced button labels and panels that no
longer exist — "new batch," "run the loop," a "Known limitation" panel that
moved to the README weeks ago). The rewrite: real numbers and real case IDs
captured directly from running `seed=42` locally (not invented
placeholders — 207 cases, 100.0% accuracy, 0.00% false auto-close, four
real escalation examples with their exact `reason_detail` text quoted
verbatim), a beat for today's ground-truth transparency feature, a beat
that deliberately shows the chat's graceful degradation on an unrecognized
question (ties directly to the judging rubric's "the right tool in the
right place, and where you chose not to use one" line), click-by-click
instructions synced to the script, a division of labor (what's already
done vs. what only Vani can do), and practical recording guidance grounded
in Devpost's own hackathon-demo-video advice (searched, no
buildathon-specific example videos exist yet to draw from instead — see
`docs/PROJECT_CONTEXT.md` for why that's the expected result, not a gap).

Also re-verified razorpay.com/buildathon live (screenshots, not text-fetch)
specifically for video-submission requirements beyond "5 minutes" — found
the page's own "THE PROOF" section names "what broke at 2 AM, and how you
got out" as one of exactly three things read, alongside the repo and the
video. Confirmed the real application is a live Google Form (reached via
"Apply now") whose first page only asks eligibility questions before
gating the rest — did not proceed past it, since that requires entering
personal data and submitting a real form, outside what this session should
do unattended. See `docs/PROJECT_CONTEXT.md`'s "Video/submission
requirements" entry for the full trail, including an unconfirmed secondary-
source claim that the video field wants an unlisted YouTube link.

## Video script: intro fix, failure beat, and card-based restructure (2026-09-05)

Three follow-up rounds on `docs/VIDEO_SCRIPT.md` after the initial rewrite
above, each prompted by direct feedback. `VIDEO_SCRIPT.md` itself now stays
action-only (script, click sequence, numbers, recording steps) — this
entry holds the *why*, so future changes to it can be evaluated against the
actual reasoning rather than guessed at.

**Round 1 — the cold open was boring.** The first rewrite opened with two
back-to-back expository beats (a problem statement, then a design-principle
statement) totaling 45 seconds with zero clicks — directly contradicting
the script's own cited advice that judges decide fast. Consulted advisor:
confirmed the fix, collapsed both into a ~15s open that started on-screen
evidence (a completed run's flagged cards) instead of a claim, and moved
the "plain math decides, AI only explains" line out of the intro entirely
into the 3:30 chat beat, where it lands as a caption on evidence already
on screen rather than an unearned claim before anything's run. Advisor also
caught a real structural gap while reviewing: the doc claimed a "beat 6"
answered the buildathon's stated "what broke at 2 AM" requirement, but no
beat actually was a failure-recovery story — the FX limitation is a known
limitation, disclosed, not something that broke and got fixed. Added a
genuine one: the History-slowness investigation (first hypothesis was a
heavy query, disproven by actually reading it; the real cause was the
schema-migration recheck on every cold start).

**Round 2 — explicit chronology requested.** Direction: problem card(s) →
TieOut card → "let's see it in action" → demo → failure-recovery card →
conclusion, with "a little more jazz, not too much" in the delivery, using
Premiere Pro for editing. Consulted advisor again given the apparent
tension with round 1's "don't open on a slide" framing — resolved as: the
intro wasn't boring because it opened on a slide, it was boring because
the slides were dry with nothing distinctive to say. A card can be a hook.
Kept round 1's real insight (the TieOut card states *what* the product
does; the *how it's built* claim stays held for the chat beat, so it's
earned rather than asserted twice) and restructured everything else around
5 cards: 2 problem cards, TieOut, failure-recovery, conclusion. Retimed to
~4:45 by tightening demo narration, not by cutting either
`multi_payment_ambiguous`/`books_duplicate_invoice_collision` escalation
example — advisor flagged both as load-bearing (opposite halves of the same
abstention thesis) and not to trade one for pacing. On the practical "how
do I make a slide in Premiere" question: recommended building cards
natively in Premiere's Essential Graphics panel over round-tripping through
PowerPoint, since a default PPT template's look would visibly clash with
the product's own dark theme; PNG-export-from-Keynote/Canva or a plain
screenshot both work identically as a fallback for anyone who'd rather lay
text out visually first. Recommended against background music (licensing
risk on deadline day, and it works against the plain-spoken register that
is this project's actual differentiator).

**Round 3 — doc cleanup.** `VIDEO_SCRIPT.md` had accumulated meta-commentary
explaining *why* each beat was shaped the way it was (references to earlier
drafts, rationale for keeping/cutting content, "new beat, didn't exist
before" asides) mixed into the actionable script itself. Moved all of that
here; `VIDEO_SCRIPT.md` now reads as a pure shot list — script, click
sequence, numbers, recording steps — with no explanation of its own
editorial history left in it.

**How the numbers in the script were produced** (moved here from
`VIDEO_SCRIPT.md`, reproduce if `reconciler/generate.py`'s builders ever
change):

```python
from reconciler.generate import generate_dataset, scale_taxonomy_counts
from reconciler.engine import reconcile
from reconciler.evaluate import evaluate

ds = generate_dataset(seed=42)                 # the main 207-case walkthrough
run = reconcile(ds.payments, ds.settlement_lines, ds.invoices)
ev = evaluate(run, ds.ground_truth)

ds2 = generate_dataset(seed=42, fault_counts=scale_taxonomy_counts(150))  # the customize-panel beat
```

`seed=42`'s exact output is deterministic and reproducible forever (see
`tests/test_generate.py`) — the script's numbers stay exactly right as long
as the generator hasn't changed since. Also separately verified live
against `https://tieout-lemon.vercel.app/` under `DEMO_FIXED_SEED=42` to
produce byte-identical output to the local run above (see the entry above
this one).

## Live-recording-session fixes: Gemini bugs, real numbers, Action/Speak format (2026-09-05)

Vani started actually recording. Two real bugs were found and fixed live,
in production, mid-session:

**Bug 1 — `DEMO_FIXED_SEED` didn't produce the script's numbers.** The
script's 207-case numbers came from calling `generate_dataset(seed=42)`
directly. The actual "Generate sample data" button sends an empty body,
which routes through `_resolve_fault_counts` → `jitter_taxonomy_counts(seed)`
when neither `fault_counts` nor `total_cases` is given — jitter is applied
even with the seed fixed, giving **229 cases**, not 207, with different
case IDs (jitter changes per-category counts, which shifts every
subsequent RNG draw). Not a code bug — `DEMO_FIXED_SEED` does exactly what
it was built to do (reproducible across repeat clicks) — but the script's
specific numbers were wrong for what the button actually produces.
`VIDEO_SCRIPT.md` corrected to the real numbers from actual batch
`266ce9f5d719` (229 cases, 249 payments, 220 settlement lines, 128
invoices; real case IDs for all four scripted escalation examples). The
`total_cases=150` customize-panel path is unaffected — it goes through
`scale_taxonomy_counts`, not jitter — so the 151-case number was already
correct and unchanged.

**Bug 2 — the Gemini provider was fully broken.** Vani supplied a real
`GEMINI_API_KEY` to demo the chat's LLM layer live. Two separate bugs
surfaced in `reconciler/llm.py`, found by testing directly against
Google's API rather than guessing from the silent "template" fallback:
1. The hardcoded default model, `gemini-2.0-flash`, has been retired by
   Google (confirmed via the API's own 404 response, which names the
   replacement).
2. The replacement (`gemini-3.6-flash`) "thinks" by default — a trivial
   prompt took ~20s, a realistic prompt took ~20-25s, both well past the
   original 8s timeout, so every call was silently timing out and
   returning the template fallback regardless of a valid key.
Fixed: updated the default model, added `thinkingConfig: {thinkingLevel:
"low"}` to the Gemini request body (cuts a short prompt to ~2-4s, though a
long prompt can still take ~20s), and raised `_TIMEOUT_SECONDS` from 8 to
25 to accommodate the slow case rather than silently discarding a
legitimate answer. Verified end-to-end against production after each
change: quick-chip questions now return in ~10-15s (`source: "template"`,
Gemini-rephrased), free-form unrecognized questions in ~20-25s
(`source: "llm"`, real Gemini answer, correctly declining to invent a
number not in the given summary). Both commits (`f887a3c`, `7e26ccd`) were
pushed and deployed live during the recording session, not queued for
later.

**`VIDEO_SCRIPT.md` reformatted** into explicit **Action** / **Speak**
sub-lines per beat, per direct request for something easier to follow
live while recording — separates what to click from what to say, instead
of prose paragraphs mixing both. The chat beat (2:50–3:20) also gained a
callout: with a real key configured, that beat no longer demonstrates
graceful-degradation-to-a-template (the whole point of the original
script) — it now shows a genuine live AI answer instead, correctly
labeled. Noted as arguably a stronger demo, but a different one from what
was scripted, and callable out loud on camera rather than silently
narrated as something it no longer is.

## Remaining — needs Vani specifically

**Recording the actual pitch video.** Not just pending — actively prepped:
`docs/VIDEO_SCRIPT.md` is now a fully rewritten shot-by-shot script mapped
to today's live console (ground-truth transparency, the discoverable chat,
the pluggable LLM layer, all with real numbers from a fixed demo seed) —
turn on `DEMO_FIXED_SEED` (instructions at the top of that file), rehearse
once, record, then turn it back off. Recording itself still needs Vani;
nothing else in the build is blocking it. Opening the real application form
past its eligibility page (to confirm the exact video-submission mechanics)
also needs Vani specifically.
