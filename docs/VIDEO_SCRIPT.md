# Pitch video — literal step-by-step (Windows)

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
this (it's run from a Mac/dev machine, not from your Windows PC — you
don't need to run it yourself, just confirm with whoever's doing it that
it's live):
```
VERCEL_TOKEN=$(grep '^VERCEL_TOKEN=' .env | cut -d= -f2-)
echo "42" | npx --yes vercel env add DEMO_FIXED_SEED production --token "$VERCEL_TOKEN"
npx --yes vercel deploy --prod --token "$VERCEL_TOKEN" --yes
```
If you're not sure whether it's on, ask before recording — Part 2 below
depends on it giving you the same numbers every time.

**One-time setup check: turn on Xbox Game Bar's microphone recording.**
1. Press the **Windows key**, type `Xbox Game Bar settings`, press
   **Enter**.
2. Make sure the toggle at the top ("Open Xbox Game Bar using this
   button") is **On**.
3. Click **Captures** in the left sidebar. Make sure **"Record audio when
   I record a game"** (or similarly worded) is turned **On** — this is
   what makes your microphone get included in the recording.

**Practice reading each line out loud once before you record it.** You
don't need to memorize anything, just don't read it cold on the first take.

---

## Part 1 — Record the 5 picture-cards (do this 5 times, once per card)

Each card is: a picture full-screen on your monitor, with you reading one
line out loud, recorded as a small video. Repeat these exact steps for
each of the 5 cards before moving to Part 2.

1. **Open Chrome.** Press **Ctrl + O** — a file-picker window opens.
   Navigate to the card's `.jpg` file, select it, click **Open**. It opens
   full-size in a new Chrome tab.
2. **Make Chrome fill the screen.** Press **F11**. All of Chrome's
   toolbars/tabs disappear — just the picture fills your monitor.
3. **Open the recording overlay.** Press **Windows key + G**. If Windows
   asks "Do you want to open Game Bar?", click **Yes, this is a game** (or
   similar) — it works the same regardless of what it's called.
4. **Turn the microphone on.** In the small **Capture** panel that
   appears, find the microphone icon and click it so it's turned **on**
   (it should look highlighted/solid, not crossed out).
5. **Start recording.** Click the round **Record** button in the Capture
   panel (or press **Windows key + Alt + R**). A small timer appears
   showing recording has started.
6. **Wait one full second of silence**, then **read the line out loud**
   (the exact words for this card are in the table below).
7. **Wait one more second of silence** after you finish speaking.
8. **Stop recording.** Press **Windows key + Alt + R** again (or click the
   stop square on the small recording toolbar). Windows shows a
   notification like "Game clip recorded" in the bottom-right corner.
9. **Find the file.** Open **File Explorer** (Windows key + E), go to
   **This PC → Videos → Captures**. Your new recording is the most recent
   file there (named something like "Chrome 2026-09-05 14-23-10.mp4").
   **Rename it** to match the table below (right-click → Rename), then
   **cut and paste it** into your **TieOut Video** folder.
10. Press **F11** again in Chrome to leave full-screen, close that tab,
    and repeat from step 1 for the next card.

| Card file | Save the recording as | Read this out loud |
|---|---|---|
| `card1_problem_1.jpg` | `card1.mp4` | *"A customer pays. The gateway settles it. The books record it. Three numbers — that are supposed to be the same number."* |
| `card2_problem_2.jpg` | `card2.mp4` | *"Most companies still check that by hand. One missed mismatch is real money, quietly gone."* |
| `card3_tieout_intro.jpg` | `card3.mp4` | *"Presenting TieOut. It checks your payments against what settled, and what the books say — closes what it's sure about, automatically, and asks a human about everything else. Let's see it in action."* |
| `card4_failure_recovery.jpg` | `card4.mp4` | *"What broke — and how we found out. Here's a real one. The History page felt slow, even with almost no history in it. The obvious guess was a heavy database query — so we read the actual query and checked the fetch pattern, and that guess was wrong: the query was already lean, no missing pagination, nothing pulling more data than it needed. The real cause was upstream of the query entirely — every server cold start was silently re-running a full schema-migration check before answering anything at all, every single time. Fixed by checking once instead of blindly retrying it, and wrote a test that proves it still repairs a genuinely broken database when one actually shows up. That's the habit this project runs on — check before you guess, then fix the thing that's actually wrong, not the thing that looked wrong."* |
| `card5_close.jpg` | `card5.mp4` | *"Order data can be pulled live from Razorpay's actual test-mode API; payment and settlement data is synthesized but built field-for-field to match Razorpay's documented schema, including the real order_id-only linkage on payment-type settlement lines that makes the multi-payment case genuinely ambiguous. This is the judgment — knowing when not to act — that the role is asking to see."* |

Card 4's line is long — it's fine to read it a little slower, or pause
briefly in the middle. Don't rush it.

At the end of Part 1, you should have 5 files in your TieOut Video folder:
`card1.mp4`, `card2.mp4`, `card3.mp4`, `card4.mp4`, `card5.mp4`.

**If Windows key + G doesn't open anything** (Game Bar can be disabled on
some PCs, e.g. work laptops): install the free program **OBS Studio**
instead (obsproject.com), which does the same job but needs a one-time
setup — ask if you get to this point and need those steps instead.

---

## Part 2 — Record the live demo (one single recording)

This is one continuous screen recording of you using the actual website,
talking as you go. Same recording method as Part 1, but instead of a
still picture, it's the live Chrome window.

1. **Open Chrome** and go to **https://tieout-lemon.vercel.app/**. Make
   sure this Chrome window is the one currently active/on top (click on
   it once) — Game Bar records whichever app you clicked into last.
2. **Press Windows key + G**, make sure the microphone icon is turned on
   (same check as Part 1, step 4).
3. **Click the round Record button** (or press **Windows key + Alt + R**)
   to start recording.
4. Now do each of the following numbered actions **in order**. Where it
   says **Say:**, read that line out loud while or right after you do the
   click.

**1.** Click **"Customize this batch (optional)"** to open it — it's the
small link right under the "Generate sample data" button. Click into the
box labeled **total-transactions** and type **150**. Leave every other box
empty. Click **"Generate sample data."** Wait for it to finish loading.
**Say:** *"Every one of 16 fault types is named and countable — not a
black box."* This one click both proves the customize option is real and
produces the actual batch the rest of this video uses — no need to
generate twice or start over.

**2.** Click **"Reconcile now."** Wait for the four number-cards to appear
on screen.
**Say:** *"100% accuracy. Zero incorrect approvals. A couple of
milliseconds to check every one of these records against each other."*
Pause on that for a second — let it land — then: *"And this isn't a number
we're just asserting. Every one of these cases was checked against a
known-correct answer, and you can see exactly which ones — right here."*
(Then move straight into step 3, below, which shows it.)

**3.** Click the **"Expected outcomes"** tab (it's inside the "What's in
this batch" section).

**4.** Click **"Compare against expected outcomes ▸."** Click the checkbox
**"Show mismatches only"** once to turn it off.
**Say:** *"No mismatches — every case matched its expected outcome. If
anything had disagreed with the answer key, this is exactly where you'd
see which case, and why."*

**5.** Scroll down to the section titled **"What needs a human"**, then
**"Flagged items — with the actual reason."** You'll see a list of cards.
Find one card from each of these 4 categories (the category name is shown
on each card — the exact ID number will be different every time you
generate, that's normal, just use whichever real card you find):

   - A card labeled **multi_payment_ambiguous** (example seen when this
     was tested: `order_uQ2hU5tGtQAuzS`).
     **Say:** *"Order has multiple payments; recon payment-lines carry
     order_id only, no payment_id, so a settlement line cannot be
     attributed to one specific payment."*
   - A card labeled **books_duplicate_invoice_collision** (example seen:
     `order_xQ8VS8IALVUj4A`).
     **Say:** *"Two open invoices match this customer and amount; books
     alone cannot say which one this payment settles — abstaining. Same
     principle as the last one, books side."*
   - A card labeled **high_value_gate** (example seen: `order_rKcWWlEHPC6rlL`).
     **Say:** *"Amount exceeds the auto-close ceiling. Not a confidence
     judgment — a rule."*
   - A card labeled **disputed** (example seen: `order_Ct3LBtKNdN9Vg8`).
     **Say:** *"Dispute ID present; never auto-closed regardless of
     amount."*

**6.** Scroll further down to **"Per-fault-class accuracy"** and pause on
it briefly.
**Say:** *"International payments settled in INR after conversion aren't
modeled. The engine correctly refuses to auto-close these — it never
mis-closes one — but it can only say the amount doesn't match, not why."*

**7.** Click the **"Ask a question"** button (either the small round one
in the bottom-right corner, or the "Ask a question about this run" button
near the top). Click the chip that says **"what's the biggest exception?"**
**Wait quietly — don't talk — for about 10-15 seconds** while it answers
(you'll trim this waiting time out later, in Part 3, step 7).

**8.** Type a question it won't recognize, for example:
**"what's your favorite color?"** and press Enter or click "Ask."
**Wait quietly again — this one can take 20-25 seconds.** Once the answer
appears, then **say:** *"Plain math decides every match. AI only ever
explains a decision — it can never make one. There's a pluggable LLM layer
under this — Anthropic, OpenAI, Gemini, or any OpenAI-compatible host —
and even when one's configured, it only ever phrases an already-computed
fact, or answers strictly from this run's aggregate numbers, labeled as
AI-generated when it does."*

**9. Stop recording** — press **Windows key + Alt + R** again. Open
**File Explorer → This PC → Videos → Captures**, find the newest file,
rename it to **`demo.mp4`**, and cut-paste it into your TieOut Video
folder (same as Part 1, step 9).

You should now have 6 files total in that folder: `card1.mp4` through
`card5.mp4`, plus `demo.mp4`.

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
   TieOut Video folder, select all 6 `.mp4` files (click the first one,
   then Shift-click the last one to select all of them at once), and
   click **Import**. They now appear in the **Project panel**
   (usually the panel on the left side of the screen).
4. **Start the timeline.** Drag `card1.mp4` from the Project panel down
   onto the **Timeline panel** (the panel along the bottom of the screen).
   Premiere will ask to match the sequence settings to this clip — click
   **Yes** or **Keep Existing Settings**, either is fine here.
5. **Add the rest, in this exact order.** One at a time, drag each of the
   following onto the Timeline, snapping it right up against the end of
   the previous clip (Premiere shows a small vertical line when clips are
   about to snap together — drop it there so there's no gap and no
   overlap):
   1. `card1.mp4` *(already placed in step 4)*
   2. `card2.mp4`
   3. `card3.mp4`
   4. `demo.mp4`
   5. `card4.mp4`
   6. `card5.mp4`
6. **Watch it back.** Click once on the Timeline to select it, press
   **Home** to jump to the very start, then press the **Space bar** to
   play. Press **Space bar** again to pause. Check the order is right and
   you can hear yourself clearly on every clip.
7. **(Recommended) Cut the two waiting gaps inside `demo.mp4`** — the two
   quiet stretches from Part 2, steps 7 and 8, where you were told to
   wait quietly:
   - Move the blue vertical playhead line to right where a quiet gap
     starts (click on the ruler above the clips at that point).
   - Press **C** to switch to the Razor tool (your cursor becomes a
     blade). Click on `demo.mp4` exactly at the playhead to slice it.
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

- **Your numbers should match this doc exactly** if you follow Part 2 step
  1 exactly (type 150, nothing else) — this path is fully deterministic,
  not randomized. If they don't match, something upstream changed; read
  whatever's actually on your screen rather than trusting this doc blindly.
- **A live AI (Gemini) is configured right now**, which is why steps 7
  and 8 in Part 2 take 10-25 seconds instead of being instant, and why
  step 8's answer is a real generated sentence rather than a canned "I
  don't know" message.
- For the full reasoning behind every choice in this script (why these
  specific numbers, why cards instead of just narration, why the failure
  story is what it is), see `docs/STATUS.md` — this doc is intentionally
  action-only.
