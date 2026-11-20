# Demo script for PRASUNEX Round 3 (about 8 minutes)

## Before the session (once)

1. Use a fresh database with demo accounts:
   `python scripts\create_demo_accounts.py --with-activity` (locally), or the same command pointed at Turso for the live site (see README → Deploy).
2. Keep `ALLOW_EARLY_RETEST=true` so you can skip the 24-hour wait on stage (the shortcut is recorded in the history).
3. Open three browser windows (or one normal + two private windows), all logged out:
   - A: the landing page
   - B: will log in as the learner `demo.learner@example.com`
   - C: will log in as the teacher `demo.teacher@example.com`
   Password for all demo accounts: `Demo-Pass-2026!`
4. Keep the answer sheet below at hand.

## 1. The problem and the idea (window A, 1 min)

- Hero: "Don't just find the wrong answer. Find the missing understanding."
- Scroll to **"A wrong answer is a symptom"** and **"How ELEVIA works"**: four roles, fixed rules, no AI in decisions.
- Point at **Subjects**: 4 subjects, 11 playable topics; grey chips are planned, not faked.
- Line to say: *"Our core rule is 'verify before you teach'. A suspected misconception is only a hypothesis until new questions confirm it."*

## 2. One complete student journey (window B, 4 min)

1. Log in → the **dashboard**. Choose grade 6, then **Mathematics → Fractions → Start the check-in**.
2. **Check-in** (5 questions). Answer:
   - `1/5 + 2/5` → **3/5** (right)
   - `1/2 = ?/8` → **4**
   - `1/2 + 1/3` → **2/5** ← the classic mistake
   - `Write 6/8 in its simplest form` → **3/4**
   - `1/4 + 2/3` → **3/7** ← same mistake
   *(If a different question shows up, answer it correctly; only the two additions need the mistake.)*
3. **Double-check screen**: point at the yellow box *"Possible gap: not confirmed yet"* and the step tracker. *"ELEVIA hasn't changed anything yet. It asks two NEW questions."*
   - `1/3 + 1/6` → **2/9** (same mistake again)
   - `What is the lowest common denominator of 1/4 and 1/6?` → **10** (adding the denominators: the same misunderstanding)
4. **Gap confirmed → lesson**. Show "Why this lesson", the personal note quoting the student's own answer, step-by-step explanation, and worked examples. Click **Show a hint** on a practice question, answer two practice questions, click **"I'm done practising"**.
5. **Retest scheduled** with a countdown (24 h). Click **Start now (demo shortcut)**. Answer all three correctly → **"Gap closed"**, retest 3/3, skill mastered.
6. Optional, to show replanning: in another topic, deliberately fail a retest (answer 2 of 3 wrong): the gap stays open, "Last retest: 1 out of 3", and a fresh lesson and new practice appear.
7. Back to the **dashboard**: topics started, mastered skills, history.
8. Show another subject quickly: **Computer Science → Loops**, a predict-the-output question with real code.

## 3. The teacher's side (window C, 2 min)

1. Log in as the teacher. **Students' learning** shows Class 5 A, insights ("1 need your review") and Arjun's row marked **needs review**.
2. **Open** Arjun: fractions round is **Inconclusive**, with evidence (his answers), the Checker's reason ("Mixed evidence…") and the review form. The decimals round shows a confirmed and resolved gap, with retest scores.
3. Click **Confirm gap and teach** without a reason → the app asks for one. Type a reason, confirm → stage becomes "In the learning room"; the audit line shows your name and reason.
4. Line to say: *"Teachers only see their own classes. Parents see only what their child's consent allows. Every view is logged."*

## 4. Close (30 s)

- Honest scope: rule-based agents, 11 topics built and tested, more planned; optional AI only rewrites wording; no learning-outcome claims until classroom pilots.
- Numbers you can stand behind: 150 automated tests, 16 browser checks, every topic tested end to end (docs/TEST_RESULTS.md).

## If something goes wrong on stage

- "Waiting for your teacher" appears for the learner: you answered the double-check with mixed results. Use the teacher window to confirm, or start another topic.
- Ran out of new questions on a topic after several rounds: use another topic or reset the demo database.
- Network hiccup: progress is saved after every answer; just reload.
