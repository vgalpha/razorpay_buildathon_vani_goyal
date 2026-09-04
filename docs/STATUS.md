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

## Remaining — needs Vani specifically

**Recording the actual pitch video.** Not just pending — actively prepped:
`docs/VIDEO_SCRIPT.md` is a full shot-by-shot script mapped to the real,
working, now-live console (exact button labels, panel names, a real example
answer from the Q&A demo) — and it can now be shot against the actual
deployed URL instead of a local server if preferred. Recording itself still
needs Vani; nothing else in the build is blocking it.
