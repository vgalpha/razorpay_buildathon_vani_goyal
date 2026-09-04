# Video shot list — grounded in the real, running UI

This maps the fixed storyboard (see PROJECT_CONTEXT.md) to the actual
`frontend/index.html` console, so recording is mostly "click through what's
really there and narrate," not staging anything fake. Run
`uvicorn reconciler.api:app --reload` and open `frontend/index.html` before
recording; do one full dry run first so the browser/API are warm and you know
what numbers will show up (they're deterministic at a fixed seed, e.g. 42, if
you want a rehearsed run to match a rehearsed narration).

## 0:00–0:20 — The problem, shown not told

Open the console fresh (empty state: "no batch yet -- generate one to
begin"). Click **"new batch"**. Pause on the status line the instant it
updates:

> `batch <id> -- seed 42 -- 207 cases (X payments, Y settlement lines, Z invoices)`

This is a real, honest "before" shot — data exists, nothing has been checked
against anything yet. Say one sentence over it: *"Someone has to check every
one of these payments against what actually got settled and invoiced — today
that's done by hand."* Don't click "run the loop" yet.

## 0:20–0:50 — The design rule

Cut to narration over the still-unreconciled screen, or a simple slide:
*"Plain rules decide every match. AI only ever explains a decision — it can
never make one. And big amounts always go to a person, no matter how clean
the match looks."* (This is literally true of `engine.py` — say it because
it's real, not as a slogan.)

## 0:50–2:30 — The live run

Click **"run the loop."** Let the metric cards populate on screen: overall
accuracy, the **false auto-close rate card** (call this one out by name on
camera — it's colored green when zero, and zero is the number that should be
on screen), throughput, records processed. Then scroll to the **"Engine
trace — per pass"** panel and let it sit on screen for a couple of seconds —
this is the single best "it's actually running, not a mockup" shot: real
per-pass timings, real hit counts, e.g. `disputed 8 decided · 0.184ms`.

## 2:30–3:30 — The trust moment

Scroll to **"Exceptions — escalated, with the actual reason"**. Pick 2-3
real cards to read on camera, in this order:

1. A **`multi_payment_ambiguous`** case — read its `reason_detail` text
   aloud (it names the actual order and cites the real schema constraint:
   settlement lines carry `order_id` but not `payment_id`).
2. A **`books_duplicate_invoice_collision`** case — the books-side twin of
   the same idea; narrate the parallel explicitly: *"Same principle, second
   place — two open invoices, same customer, same amount. It won't guess
   here either."*
3. A **`high_value_gate`** case — narrate that this one isn't even about
   confidence: *"This match is clean. It's escalated anyway, because of the
   amount — a rule, not a judgment call."*

## 3:30–4:15 — The honest scorecard + the disclosed limitation

Scroll to **"Per-fault-class accuracy"** briefly (real per-class numbers, not
one aggregate). Then hold on the **"Known limitation — disclosed on
purpose"** panel — read it verbatim or close to it: *"International payments
settled in INR after FX conversion aren't modeled. It correctly refuses to
auto-close these — it never mis-closes one — but it can only tell you the
amount doesn't match, not why."* Say this plainly, don't compare it to any
other submission — it should stand on its own.

## 4:15–4:45 — Why it's real

One line, ideally over the **"Ask the ledger"** panel: click the **"what's
the biggest exception?"** chip live and read the real answer that comes
back (data-grounded, not scripted — e.g. it names a real order id and a
real ₹ amount). Then state plainly: order data can be pulled live from
Razorpay's actual test API (`orders_source.py`, `mode="live"` — mention that
real Razorpay-issued orders were created and verified during development);
payment and settlement data is synthesized but built field-for-field to
match Razorpay's own documented schema, including the real `order_id`-only
linkage quirk that makes the multi-payment case genuinely ambiguous, not an
invented difficulty.

## 4:45–5:00 — Close

One line tying back to the internship pitch: this is the judgment — knowing
when *not* to act — that the role is actually asking to see.

## Practical notes for recording

- Everything above is now real and clickable, not a plan — re-verify once
  with a fresh browser + freshly started `uvicorn` immediately before
  recording, the same way it was verified during the build (see
  `docs/STATUS.md`).
- If a real LLM key gets added before recording, the `notes.py`/`qa.py`
  output text will change slightly (currently template-only, see
  `docs/STATUS.md`'s "Where things stand") — do one fresh dry run after
  adding a key and re-read the exact exception text before narrating over
  it, since the script above quotes today's template phrasing.
- If deployed by recording time, decide whether to record against the
  deployed URL or `localhost` — `localhost` avoids any deployed-host
  cold-start risk entirely during the recording itself, which is the
  lowest-risk choice regardless of what's live for judges afterward.
