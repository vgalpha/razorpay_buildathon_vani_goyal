# Pitch video — literal step-by-step (Mac)

**What you're making**: a ~4:45 video made of 6 small video files, played
back to back. 5 of them are just a picture with you talking over it. 1 of
them is you actually using the website with your voice recorded live.
Every step below tells you exactly what to click and exactly what to say —
follow them in order, top to bottom.

**Files you already have**: 5 picture files, sent to you separately and
also saved in this project's `video_cards/` folder:
- `card1_problem_1.jpg`
- `card2_problem_2.jpg`
- `card3_tieout_intro.jpg`
- `card4_failure_recovery.jpg`
- `card5_close.jpg`

Put all 5 into one new folder somewhere easy to find, e.g. a folder on
your Desktop called **TieOut Video**. Everything you record below also
gets saved into that same folder.

---

## Part 0 — Before you start recording

**Confirm the demo data is turned on.** Someone should have already run
this:
```
VERCEL_TOKEN=$(grep '^VERCEL_TOKEN=' .env | cut -d= -f2-)
echo "42" | npx --yes vercel env add DEMO_FIXED_SEED production --token "$VERCEL_TOKEN"
npx --yes vercel deploy --prod --token "$VERCEL_TOKEN" --yes
```
If you're not sure whether it's on, ask before recording — Part 2 below
depends on it giving you the same numbers every time.

**Practice reading each line out loud once before you record it.** You
don't need to memorize anything, just don't read it cold on the first take.

---

## Part 1 — Record the 5 picture-cards (do this 5 times, once per card)

Each card is: a picture full-screen on your monitor, with you reading one
line out loud, recorded as a small video. Repeat these exact steps for
each of the 5 cards before moving to Part 2.

1. **Open the picture.** Double-click the card's `.jpg` file. It opens in
   the Preview app.
2. **Make it fill the screen.** Press **Control + Command + F**. The
   picture now fills your whole monitor with nothing else visible.
3. **Open QuickTime Player.** Press **Command + Space**, type
   `QuickTime Player`, press **Enter**.
4. **Start a new screen recording.** In the menu bar at the very top of
   your screen, click **File**, then **New Screen Recording**.
5. **Turn on your microphone.** A small floating control bar appears with
   a red record button. Click the small **˅** arrow right next to the red
   button. Under "Microphone," click your Mac's built-in microphone (it's
   usually already selected).
6. **Start recording.** Click the red record button. Your cursor changes.
   Click anywhere on the screen with the picture on it — a message appears
   asking to record the whole screen or a selection; choose **Record
   Entire Screen**.
7. **Wait one full second of silence**, then **read the line out loud**
   (the exact words for this card are in the table below).
8. **Wait one more second of silence** after you finish speaking.
9. **Stop recording.** Look at the very top-right of your screen (the menu
   bar) — click the small dark **stop button** (a square inside a circle).
10. QuickTime opens the recording automatically. Go to **File → Save**
    (or press **Command + S**). Name the file exactly as shown in the
    table below, and save it into your **TieOut Video** folder.
11. Switch back to Preview (**Command + Tab**), press **Esc** to leave
    full-screen, then open the next card's picture and repeat from step 2.

| Card file | Save the recording as | Read this out loud |
|---|---|---|
| `card1_problem_1.jpg` | `card1.mov` | *"A customer pays. The gateway settles it. The books record it. Three numbers — that are supposed to be the same number."* |
| `card2_problem_2.jpg` | `card2.mov` | *"Most companies still check that by hand. One missed mismatch is real money, quietly gone."* |
| `card3_tieout_intro.jpg` | `card3.mov` | *"Presenting TieOut. It checks your payments against what settled, and what the books say — closes what it's sure about, automatically, and asks a human about everything else. Let's see it in action."* |
| `card4_failure_recovery.jpg` | `card4.mov` | *"What broke — and how we found out. Here's a real one. The History page felt slow, even with almost no history in it. The obvious guess was a heavy database query — so we read the actual query and checked the fetch pattern, and that guess was wrong: the query was already lean, no missing pagination, nothing pulling more data than it needed. The real cause was upstream of the query entirely — every server cold start was silently re-running a full schema-migration check before answering anything at all, every single time. Fixed by checking once instead of blindly retrying it, and wrote a test that proves it still repairs a genuinely broken database when one actually shows up. That's the habit this project runs on — check before you guess, then fix the thing that's actually wrong, not the thing that looked wrong."* |
| `card5_close.jpg` | `card5.mov` | *"Order data can be pulled live from Razorpay's actual test-mode API; payment and settlement data is synthesized but built field-for-field to match Razorpay's documented schema, including the real order_id-only linkage on payment-type settlement lines that makes the multi-payment case genuinely ambiguous. This is the judgment — knowing when not to act — that the role is asking to see."* |

Card 4's line is long — it's fine to read it a little slower, or pause
briefly in the middle. Don't rush it.

At the end of Part 1, you should have 5 files in your TieOut Video folder:
`card1.mov`, `card2.mov`, `card3.mov`, `card4.mov`, `card5.mov`.

---

## Part 2 — Record the live demo (one single recording)

This is one continuous screen recording of you using the actual website,
talking as you go. Same recording method as Part 1, but instead of a
still picture, it's the live Chrome window.

1. **Open Chrome** and go to **https://tieout-lemon.vercel.app/**
2. **Open QuickTime Player**, click **File → New Screen Recording**, and
   turn the microphone on (same as Part 1, steps 4-5).
3. **Click the red record button**, then click anywhere on the Chrome
   window and choose **Record Entire Screen** (or select just the Chrome
   window if you're offered that choice — either is fine).
4. Now do each of the following numbered actions **in order**. Where it
   says **Say:**, read that line out loud while or right after you do the
   click.

**1.** Click **"Generate sample data."** Wait for it to finish loading —
don't say anything, just wait.

**2.** Click **"Customize this batch (optional)"** to open it. Click into
the box labeled **total-transactions** and type **150**. Leave every
other box empty. Click **"Generate sample data"** again and wait for it to
finish.
**Say:** *"Every one of 16 fault types is named and countable — not a
black box."*

**3.** Click **"Discard & start over."** Then click **"Generate sample
data"** one more time (don't touch the customize box this time) and wait
for it to finish. This is the batch the rest of the video uses.

**4.** Click **"Reconcile now."** Wait for the four number-cards to appear
on screen.
**Say:** *"A couple of milliseconds."* Then point at (or just look toward)
the sentence under the four cards and say: *"Measured against this
batch's known-correct answers — a validation score for the engine, not a
live production guarantee. It's a validation run against a known-correct
answer key — exactly what the track brief asks for. In production this
same loop runs once offline to earn a fixed accuracy figure, then the live
engine runs on real transactions with no answer key left to grade
against."*

**5.** Click the **"Expected outcomes"** tab (it's inside the "What's in
this batch" section).

**6.** Click **"Compare against expected outcomes ▸."** Click the checkbox
**"Show mismatches only"** once to turn it off.
**Say:** *"No mismatches — every case matched its expected outcome. If
anything had disagreed with the answer key, this is exactly where you'd
see which case, and why."*

**7.** Scroll down to the section titled **"What needs a human"**, then
**"Flagged items — with the actual reason."** You'll see a list of cards.
Find one card from each of these 4 categories (the category name is shown
on each card — the exact ID number will be different every time you
generate, that's normal, just use whichever real card you find):

   - A card labeled **multi_payment_ambiguous**.
     **Say:** *"Order has multiple payments; recon payment-lines carry
     order_id only, no payment_id, so a settlement line cannot be
     attributed to one specific payment."*
   - A card labeled **books_duplicate_invoice_collision**.
     **Say:** *"Two open invoices match this customer and amount; books
     alone cannot say which one this payment settles — abstaining. Same
     principle as the last one, books side."*
   - A card labeled **high_value_gate**.
     **Say:** *"Amount exceeds the auto-close ceiling. Not a confidence
     judgment — a rule."*
   - A card labeled **disputed**.
     **Say:** *"Dispute ID present; never auto-closed regardless of
     amount."*

**8.** Scroll further down to **"Per-fault-class accuracy"** and pause on
it briefly.
**Say:** *"International payments settled in INR after conversion aren't
modeled. The engine correctly refuses to auto-close these — it never
mis-closes one — but it can only say the amount doesn't match, not why."*

**9.** Click the **"Ask a question"** button (either the small round one
in the bottom-right corner, or the "Ask a question about this run" button
near the top). Click the chip that says **"what's the biggest exception?"**
**Wait quietly — don't talk — for about 10-15 seconds** while it answers
(you'll trim this waiting time out later, in Part 3, step 8).

**10.** Type a question it won't recognize, for example:
**"what's your favorite color?"** and press Enter or click "Ask."
**Wait quietly again — this one can take 20-25 seconds.** Once the answer
appears, then **say:** *"Plain math decides every match. AI only ever
explains a decision — it can never make one. There's a pluggable LLM layer
under this — Anthropic, OpenAI, Gemini, or any OpenAI-compatible host —
and even when one's configured, it only ever phrases an already-computed
fact, or answers strictly from this run's aggregate numbers, labeled as
AI-generated when it does."*

**11. Stop recording** (same square stop button in the top menu bar as
Part 1, step 9). **File → Save**, name it **`demo.mov`**, save it into
your TieOut Video folder.

You should now have 6 files total in that folder: `card1.mov` through
`card5.mov`, plus `demo.mov`.

**Immediately after this, turn the demo data back off** so the live
website goes back to normal for anyone else who visits it:
```
npx --yes vercel env rm DEMO_FIXED_SEED production --token "$VERCEL_TOKEN" --yes
npx --yes vercel deploy --prod --token "$VERCEL_TOKEN" --yes
```

---

## Part 3 — Put it together in Adobe Premiere Pro

1. **Open Adobe Premiere Pro.**
2. Click **New Project** (or **File → New → Project**). Give it any name,
   e.g. "TieOut Pitch Video," and confirm.
3. **Import your 6 files.** Click **File → Import...**, navigate to your
   TieOut Video folder, select all 6 `.mov` files (click the first one,
   then Shift-click the last one to select all of them at once), and
   click **Import**. They now appear in the **Project panel**
   (usually the panel on the left side of the screen).
4. **Start the timeline.** Drag `card1.mov` from the Project panel down
   onto the **Timeline panel** (the panel along the bottom of the screen).
   Premiere will ask to match the sequence settings to this clip — click
   **Yes** or **Keep Existing Settings**, either is fine here.
5. **Add the rest, in this exact order.** One at a time, drag each of the
   following onto the Timeline, snapping it right up against the end of
   the previous clip (Premiere shows a small vertical line when clips are
   about to snap together — drop it there so there's no gap and no
   overlap):
   1. `card1.mov` *(already placed in step 4)*
   2. `card2.mov`
   3. `card3.mov`
   4. `demo.mov`
   5. `card4.mov`
   6. `card5.mov`
6. **Watch it back.** Click once on the Timeline to select it, press
   **Home** to jump to the very start, then press the **Space bar** to
   play. Press **Space bar** again to pause. Check the order is right and
   you can hear yourself clearly on every clip.
7. **(Recommended) Cut the two waiting gaps inside `demo.mov`** — the two
   quiet stretches from Part 2, steps 9 and 10, where you were told to
   wait quietly:
   - Move the blue vertical playhead line to right where a quiet gap
     starts (click on the ruler above the clips at that point).
   - Press **C** to switch to the Razor tool (your cursor becomes a
     blade). Click on `demo.mov` exactly at the playhead to slice it.
   - Move the playhead to where the gap ends, and click again with the
     Razor tool to slice a second time.
   - Press **V** to switch back to the normal Selection tool. Click once
     on the small middle piece you just cut out (the silent gap) to
     select it, then press **Delete**.
   - This leaves a gap in the timeline. Right-click the empty gap and
     choose **Ripple Delete** (or drag the clips on either side together
     manually) to close it up.
   - Repeat once more for the second waiting gap.
8. **Export the final video.** Click **File → Export → Media.** In the
   window that opens, leave the format as **H.264** (the default). Click
   **Export** at the bottom. Choose a folder and a filename, e.g.
   `TieOut_Pitch_Final.mp4`. Wait for the progress bar to finish.

That exported `.mp4` file is your finished video.

---

## Submission requirements

Confirmed on razorpay.com/buildathon: three things —
1. "a repo that actually runs"
2. "a 5-minute video of it working"
3. "what broke at 2 AM, and how you got out"

Format: unconfirmed against the real form (secondary sources suggest an
unlisted YouTube link) — check the actual Google Form yourself once you
reach its later pages, and follow whatever it says instead if it differs.

---

## Notes and known quirks

- **Your exact numbers will differ slightly from this doc.** The specific
  case IDs and total count you see when you generate will not exactly
  match any numbers written elsewhere in this project's docs — that's
  expected, not a bug. Read whatever's actually on your screen.
- **A live AI (Gemini) is configured right now**, which is why steps 9
  and 10 in Part 2 take 10-25 seconds instead of being instant, and why
  step 10's answer is a real generated sentence rather than a canned "I
  don't know" message.
- For the full reasoning behind every choice in this script (why these
  specific numbers, why cards instead of just narration, why the failure
  story is what it is), see `docs/STATUS.md` — this doc is intentionally
  action-only.
