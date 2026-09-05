# Project context — the why

## The buildathon

Razorpay AI Buildathon 2026: student-only, no resume screening, selection is
based entirely on a public repo + a 5-minute pitch video + an architecture
explanation. Winners get an AI Builder Internship (₹75,000/month, 6 or 12
months, in-person Bangalore). Five tracks; we are on **Track 04: AI Finance
Controller**.

Two official evaluation artifacts were found on the buildathon page (not
just inferred — actually read off track cards):

**Track 04 card:**
> Build an agent that closes one finance-ops loop across a 50+ record batch
> of synthetic data, reporting its match rate and the exceptions it could not
> resolve.
> Why now: verification capacity, not generation speed, is the 2026
> bottleneck. Reconciliation, settlement and forecasting are still done by
> hand.
> Example directions: multi-source reconciliation, settlement Q&A agent,
> forward cash forecaster, tax-line matcher.
> The bar: throughput plus measured accuracy plus an honest exception list.
> One cherry-picked match proves nothing.

**General judging card ("We read the work, not the resume"):**
- Problem taste — did you pick something that actually matters
- Build quality — does it run, is it structured, would you trust it
- AI judgment — the right tool in the right place, and where you chose not
  to use one
- Failure recovery — what broke, and what you did about it

Everything below is designed to answer these four questions directly, not
just to look impressive in the abstract.

**Source, re-verified directly (2026-09-05):** https://razorpay.com/buildathon/
— loaded live in a real browser (not a static fetch; this page is a JS SPA
and a plain HTTP fetch returns an empty shell) and both the Track 04 card
and the judging rubric above were confirmed word-for-word against the
live-rendered text, prompted by a concern that the "AI Finance Controller"
name might mean an LLM is a hard requirement. It doesn't: the "AI judgment"
line is verbatim "the right tool in the right place, and where you chose
not to use one" — an explicit reward for a deliberate no-LLM-in-the-
decision-path design, which is what this project already does (see
"plain math decides, AI only explains" above, and README's "What it
deliberately does and doesn't use AI for"). **Time-sensitive**: the page
states applications close 5 September — confirm this against today's date
before assuming there's runway left.

## Who this is for

Vani Goyal, B.Tech CE (Thapar), working solo. Relevant background: built an
MCP server bridging AI agents to Adobe's RTCDP (a real agent-to-system-bridge
precedent for this project's architecture), a data migration pipeline
(ACC→AJO), a CLI billing/inventory system with role-based access, and an
embedding-based recommendation model (ConverseX). Strong DBMS/SQL. This
project deliberately leans on the MCP-bridge and billing-system experience as
an honest "I've built this shape before" narrative for the pitch video.

## The project

A settlement reconciliation agent: matches a merchant's payments to
Razorpay's settlement recon report (and, once the books leg is added, to
internal invoices), auto-closing what it's certain about and escalating
everything else with a plain-English reason. See ARCHITECTURE.md for the
technical design.

## Why this track, why this project (not re-litigating — recorded so it
doesn't get re-litigated)

- Reconciliation is explicitly named in the track's own "why now" text — not
  an inferred fit, a stated one.
- Vani's background (MCP bridge, billing CLI, ETL pipeline) maps onto it more
  directly than the other tracks.
- Revenue Recovery's natural headline metric (₹ recovered) is a counterfactual
  claim, hard to make honestly without a real holdout; Finance Controller's
  metric (accuracy against authored ground truth) is directly measurable and
  defensible under adversarial reading.
- We considered and rejected Open Track (inventing a problem from scratch is
  the most expensive choice on a time budget) and a full pivot away from
  Finance Controller after finding a strong existing public submission in the
  same track (see "Competitive landscape" below) — decided to differentiate
  within the track rather than flee it.

## Competitive landscape (as of 2026-09-03/04)

A GitHub search turned up ~100+ fresh repos across all five tracks, most
pushed within 24 hours of each other — a real submission crunch, evidence the
deadline is near, not weeks out. No official Razorpay-provided sandbox or
starter kit exists anywhere; every repo found is an independent student
submission using self-generated synthetic data.

The strongest Finance Controller competitor found: **`TAYAB-HUB/RazorpayBuildathon`
("REKON")** — a live Next.js/Postgres app
(https://razorpay-buildathon-gamma.vercel.app/) with:
- 3-way reconciliation (gateway/bank/books), 8 deterministic passes including
  fuzzy-text matching for mangled bank references
- Precision/recall/F1, a "chaos-deck coverage" claim of 86/86 faults
  accounted for, invariant self-checks, per-rule scorecard, engine trace log
- A working settlement Q&A agent (deterministic planner + LLM phrasing)
- A cash-position/7-day-inflow forecast widget (arguably drifts toward the
  separate "Forward Cash Forecaster" track direction)
- Real, observed weakness: its live `/console` hung on "loading console…"
  when fetched during our research — a real symptom of its server+DB
  architecture, not hypothetical risk-aversion on our part.

**Where we have a real, structural (not just execution-quality) edge over
it, verified by actually reading Razorpay's docs and REKON's own README/site:**
- REKON's vocabulary (UTRs, mangled refs, DD/MM dates, T+8 delays) is generic
  bank-statement flavor that would work unchanged for any payment processor.
  Ours is built on Razorpay's actual documented API fields, and the
  `order_id`-only linkage on payment-type settlement recon lines (real,
  verified in their docs) produces a genuine ambiguity class a generic
  generator can't invent.
- REKON shows no sign of using the real Razorpay API at all. We use real
  Orders (see STATUS.md) — a differentiator essentially no surveyed
  competitor has.
- REKON claims total coverage ("86/86, everything accounted for"); our plan
  states one specific, plain limitation instead. Not proven to land better
  with every judge — a defensible stance, not a guaranteed win.
- REKON's cash-position widget arguably answers a different track's brief;
  we stay inside exactly what Track 04 asks for.

**What we deliberately do NOT copy, and why:**
- Fuzzy-text reference matching (trigram/Levenshtein): solves messy raw bank
  CSV ingestion, a problem that doesn't exist in our data model (Razorpay's
  actual API returns clean structured JSON). Building it would be solving a
  problem we don't have, purely for parity.
- The cash-position/forecast widget: different track's example direction,
  would dilute focus.

**Honest bottom line (do not oversell this further without new evidence):**
executed to plan, this project has a defensible case for being stronger
against the track's actual stated rubric (authenticity, fit-to-brief, a
single carried thesis) — not a guaranteed or overwhelming win, and two of the
claimed edges (real API depth, whether disclosed-limitation framing lands
better than "100%" framing) are conditional on execution and on judge
preference, not settled by planning alone.

## Definition of done

1. Non-negotiable core: generator + taxonomy + engine + tests + eval + report
   for the 2-source loop, honestly scored, reaching a genuinely submittable
   state before anything else is added.
2. The three structural edges actually ship: real Orders API usage stated
   precisely, the order_id/duplicate-invoice abstention thesis carried
   through both loops, one plainly disclosed limitation as its own slide.
3. Parity with REKON's instrumentation bar: invariants, per-rule scorecard,
   engine trace, Q&A, a genuinely well-designed UI backed by a real running
   engine (not a static mockup, not a second JS implementation of the logic).
4. What "we read the work" adds: a quarantine pass for malformed input
   (failure recovery), one-command runnability (build quality), the build's
   own real obstacle (PAN/API uncertainty, resolved by checking, not
   guessing) narrated honestly.
5. Execution discipline: shippable-state checkpoints in the build order
   (see STATUS.md), one source of truth for the matching logic, real time
   reserved for video rehearsal.

## Pitch video storyboard (fixed — script against what's actually built)

1. 0:00–0:20 — the problem, shown not told: two raw record lists side by
   side, one row visibly unmatched.
2. 0:20–0:50 — the design rule in one sentence: plain math decides, AI only
   explains, big amounts always go to a human.
3. 0:50–2:30 — live run over the full batch, tally building, timed.
4. 2:30–3:30 — the trust moment: 2-3 real escalations on screen with their
   actual generated explanations, especially the order_id/multi-payment case.
5. 3:30–4:15 — the honest scorecard, and the one disclosed limitation as its
   own slide, stated plainly, no comparison to any other submission in frame.
6. 4:15–4:45 — why it's real: built on Razorpay's actual documented schema,
   Orders pulled from their live test API.
7. 4:45–5:00 — close, tie back to the internship pitch.

**Superseded by a full rewrite, 2026-09-05**: this 7-beat outline is still
the correct shape, but `docs/VIDEO_SCRIPT.md` now has the actual finalized
shot-by-shot script mapped to today's live product (ground-truth
transparency, the discoverable chat, the pluggable LLM layer all shipped
today), with real numbers/case-IDs from a fixed `seed=42` run rather than
placeholders, click-by-click instructions, and a production plan. Read
that file directly rather than this outline when actually recording.

## Video/submission requirements — re-verified directly, 2026-09-05

Re-checked razorpay.com/buildathon live in a real browser (screenshots, not
text-fetch — same JS-SPA caveat as before) specifically for anything about
the pitch video beyond "5 minutes," which was all that had been confirmed
previously. Found one new thing, word-for-word off the page's own "THE
PROOF" section (what they read instead of a resume):

> a repo that actually runs
> a 5-minute video of it working
> what broke at 2 AM, and how you got out

That third line is the video-and-repo-facing version of the general judging
card's "Failure recovery — what broke, and what you did about it" — it's
not just an interview-stage question, Razorpay's own site lists it as one
of exactly three things they read. This project already has the real
material for it (the Definition of done section above already names it:
"the build's own real obstacle (PAN/API uncertainty, resolved by checking,
not guessing) narrated honestly") — `docs/VIDEO_SCRIPT.md`'s beat 6 is
where it goes on camera.

Also confirmed while re-checking: there are genuinely five tracks (Growth &
Agentic Commerce, Risk Manager, Revenue Recovery, Finance Controller, Open
Track) — the "Five tracks" claim earlier in this doc is accurate, not
approximate. Track 04's card text was re-confirmed word-for-word identical
to what's already quoted above.

**What was not verified, and why**: "Apply now" leads to a real Google Form
(a live one, pre-filled with the account's own email — this is the actual
application, not a mockup) whose first page only asks eligibility questions
(email, name, college, graduation year, in-person availability) before a
"Next" button gates the rest, which almost certainly contains the actual
video-submission field (upload vs. link, format). Advancing past that first
page requires entering personal data and clicking through a real
application form — outside what this session was authorized to do
unattended. **Vani needs to open the form herself** to see the exact video
submission mechanics (see "Only Vani can do" in VIDEO_SCRIPT.md).

Secondary sources (student-hackathon aggregator blogs, not Razorpay's own
page) claim the form's field is literally named "5-Minute Pitch Video URL
(Unlisted)" and includes a dedicated "what broke and how it was resolved"
text field — plausible and consistent with the primary-source "THE PROOF"
text above, but **unconfirmed against the actual form**, so treat it as a
reasonable default (upload to YouTube as unlisted) rather than a settled
fact. Two independently-fetched aggregator articles agreed with each other
and with the primary site on "5 minutes" and the September 5 deadline date
(no time-of-day given anywhere, including the primary site's own "You have
from today till 5 September" copy) but did not agree with each other on
the unlisted-YouTube-link claim strongly enough to treat it as verified.

One decorative element worth flagging so it isn't mistaken for something
real: the buildathon page has a small clock-style counter bottom-right
(e.g. "00:12", climbing to "02:13" while scrolling). This is NOT a real
countdown to the deadline — it ticks up, not down, and tracks time spent on
page (or scroll position), not a deadline. The actual deadline information
on the page is the plain-text "You have from today till 5 September. The
clock is already running." — a date, not a time-of-day.

## Competitor pitch videos — searched, none found (expected)

Searched for other Razorpay AI Buildathon 2026 submission/pitch videos (for
tone/pacing reference) and found none — only promotional/explainer content
about the program itself made by career-content YouTube channels, not
actual student submissions. This is the expected result, not a research
gap: submission videos are very likely unlisted/private links submitted
directly to Razorpay, not publicly indexed, and the buildathon is
currently live (applications closing today), so no public archive of past
submissions would exist yet either. `docs/VIDEO_SCRIPT.md`'s production
guidance is grounded instead in general hackathon-pitch-video best
practices (Devpost's own judging and demo-video guides, cross-checked
against similar sources), which is the right substitute given no
buildathon-specific examples exist to draw from.
