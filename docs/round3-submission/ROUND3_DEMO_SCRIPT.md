# ELEVIA: Demonstration video script (about 6 minutes 50 seconds)

Every action below was performed in a real browser against a freshly seeded demo: the automated browser run and a manual check of the scene changes on 23 Nov 2026, and the same journeys on the live site on 24 Nov 2026. Exact answers are given wherever the presenter types something.

**Where to record.** On the live site, **https://frontend-pmvi.vercel.app**, which was verified on 24 Nov 2026. Before recording:
1. Make sure the teacher access code is set in Vercel (`ELEVIA_DEMO_TEACHER_CODE`), or the teacher card will say the teacher demo isn't switched on.
2. Redeploy production (Vercel → Deployments → the latest production deployment → ⋯ → Redeploy). The build resets the demo, so Riya's case is back in the queue, Dev has no history and "upcoming" retests are relative to that day.

**Fallback: record on a laptop.**

```powershell
git checkout main
$env:ELEVIA_DB_PATH = "demo-video.db"
$env:ELEVIA_DEMO_PASSWORD = "<private>"
python scripts\demo.py reset
$env:ELEVIA_DEMO_MODE = "1"
$env:ELEVIA_DEMO_TEACHER_CODE = "<private, 8+ characters>"
python -m uvicorn app:app
```

Then open `http://localhost:8000`.

---

## Scene 1. Introduction and problem (25 s)

- **Screen:** landing page, top of the page.
- **Action:** pause on the hero for 3 seconds, then scroll slowly to "A wrong answer is a symptom, not a diagnosis" and keep scrolling until all three red-pen notes have appeared.
- **What viewers see:** a student's fractions check-in. Red-pen notes appear one by one: "2 / 4 …but why?", "same rule, twice", and a sticky note reading "earlier skill: common denominators".
- **Narration:** "A mark tells a teacher *that* a student is wrong, not *why*. This student wrote one-half plus one-third equals two-fifths, twice. That's not carelessness; it's a rule. And the real gap is earlier: common denominators. Re-teaching the whole chapter misses it."

## Scene 2. ELEVIA's solution and architecture (40 s)

- **Screen:** landing page, "How ELEVIA works" (the stack of books).
- **Action:** scroll steadily. Each book slides out and opens in turn: Diagnoser, Checker, Planner, Tutor, Retest.
- **What viewers see:** an open two-page spread for each role. (Further down, "What's built" works the same way: scrolling opens its nine folders one after another, and "For students" steps through the Dashboard, Double-check, Lesson and Result screens.)
- **Narration:** "ELEVIA has four roles. The Diagnoser suggests a *possible* gap. The Checker tests it with two new questions before anything is taught. The Planner walks the skill map to find where the lesson should start. The Tutor teaches the missing step, and a retest a day later checks it stuck. These are deterministic, testable rules, not an AI guessing, so the same answers always lead to the same decision."

## Scene 3. Student dashboard with six months of history (55 s)

- **Screen:** click **Try demo** in the top bar, then **Open as Riya** on Riya Sharma's card.
- **Action:**
  1. Point at the *Demonstration account* banner.
  2. Point at **What to do next** (her Data types lesson).
  3. Scroll to **Your last six months**; click **Show as a table**.
  4. Scroll to **Progress by subject** and the **Skill map**.
- **What viewers see:**
  - the banner: "Student ID DEMO-09-001 · Class 9 A, ELEVIA Demonstration School, 2026-27";
  - 7 monthly bars (late May to November) and a table that adds up to 141 answers;
  - five subjects, including Social Science;
  - mastered skills marked ✓.
- **Narration:** "This is Riya, a fictional Class 9 student, with six months of history. Every record was produced by running ELEVIA's real rules on simulated answers. She has one clear next step. Over six months: 16 check-ins, 9 gaps confirmed, 3 rejected as slips, and 8 skills mastered. A skill only counts as mastered after a retest on new questions. The table and the totals come from the same records."

## Scene 4. Diagnoser and Checker live (70 s)

- **Screen:** click **Log out** (top right). On the login page, under the demo cards, click **Open as Dev** (Dev Kapoor, new learner).
- **Action:**
  1. In the Mathematics tab, choose grade **9** in the box, then **Start the check-in** on *Fractions*.
  2. Answer the five questions in the order shown:

     | Question | Type |
     |---|---|
     | 1/5 + 2/5 | **3/5** |
     | 1/2 = ?/8 | **4** |
     | 1/2 + 1/3 | **2/5** (the misconception) |
     | 6/8 simplest | **3/4** |
     | 1/4 + 2/3 | **3/7** (the misconception) |

  3. On the double-check screen, answer **2/9** for 1/3 + 1/6, and **10** for the lowest common denominator of 1/4 and 1/6.
- **What viewers see:** after the check-in, a box saying *Possible gap … not confirmed yet*, with two new questions. After the double-check: *Gap confirmed*.
- **Narration:** "Dev is new. He adds tops and bottoms twice. The Diagnoser flags a *possible* gap, but nothing is taught yet. The Checker asks two new questions. Dev makes the same mistake again, so the gap is confirmed. If he'd got them right, ELEVIA would have called it a slip and moved on. A different kind of mistake would go to his teacher."

## Scene 5. Planner and Tutor (50 s)

- **Screen:** the lesson that appears after confirmation ("Finding common denominators").
- **Action:**
  1. Scroll through the note quoting Dev's answer, the steps and a worked example.
  2. Click **Show a hint** on the first practice question.
  3. Answer **10** (lowest common denominator of 1/2 and 1/5), then **8** (2/3 = ?/12).
  4. Click **I'm done practising**.
- **What viewers see:** a lesson that starts from his own wrong answer, and instant feedback on practice. Then a retest screen: *Unlocks* in 24 hours.
- **Narration:** "The Planner chose common denominators, the prerequisite that's actually missing. The Tutor's lesson starts from Dev's own answer. Practice gives feedback but never counts towards progress. When he's done, the Checker books a retest for 24 hours later, on questions he hasn't seen."

## Scene 6. Retest and mastery (40 s)

- **Screen:** the retest-booked screen.
- **Action:** click **Start now (demo shortcut)**. Answer **11/12** (1/6 + 3/4), **13/15** (2/3 + 1/5) and **13/24** (7/8 − 1/3).
- **What viewers see:** *Gap closed*, with the skill now mastered.
- **Narration:** "For the demo we skip the 24-hour wait. The shortcut is recorded in the log, and the server enforces the delay otherwise. Three unseen questions; two out of three closes the gap. Fail, and the Planner makes a new plan. If questions run out, the case goes to a teacher."

## Scene 7. Teacher portal and intervention (70 s)

- **Screen:** click **Log out**, then go back to the landing page (the ELEVIA logo, or the address bar). Click **Try demo**. On Ananya Mehta's teacher card, type the access code and click **Open the teacher view**.
- **Action:**
  1. Point at **Class overview · Class 9 A** and **Class insights** (Arjun under *Repeated unsuccessful retests*).
  2. In **Review queue**, click **Review** on *Riya Sharma · Past tense verbs*.
  3. Scroll to the **Past tense verbs** panel and point at *Diagnoser*, *Check-in answers*, *Double-check answers* and *Checker's verdict*.
  4. Click **Confirm gap and teach** with no reason; point at the message asking for one.
  5. Type the reason: *Riya wrote 'thinked' in her diary entry in class today*. Click **Confirm gap and teach**.
  6. Scroll up to **Learning history**, then click **Back to overview** and point at **Intervention history**.
- **What viewers see:**
  - 5 students and who needs attention, with reasons;
  - the double-check answers: one right, one "a different mistake", so *Mixed evidence … sent to a teacher*;
  - after confirming: the case moves to *In the learning room*, the reason appears in the audit, Riya's history shows *Teacher confirmed the gap*, and the intervention history lists it first.
- **Narration:** "The teacher sees only her own class. The overview is worked out from saved answers, verdicts and retests. Here the Checker couldn't decide: one right answer and one *different* mistake. So it's waiting for Ms Mehta, with the evidence. She confirms it, and ELEVIA insists on a reason. The decision is saved, audited, and Riya's lesson is ready."

## Scene 8. Technical implementation and evidence (25 s)

- **Screen:** the GitHub repository (or `docs/round3-submission/ROUND3_TECHNICAL_DOCUMENTATION.md`), then `docs/TEST_RESULTS.md`.
- **Action:** scroll the architecture diagram, then the test summary.
- **What viewers see:** the architecture diagram; "205 passed" on two databases; "26 of 26 browser checks".
- **Narration:** "One FastAPI service on Vercel with a Turso database, and a plain JavaScript front end. 205 automated tests pass on both databases, including tests that every number on these dashboards is backed by records. 26 browser checks walk the student, teacher and history journeys."

## Scene 9. Limitations and future development (25 s)

- **Screen:** `docs/round3-submission/ROUND3_FUTURE_ROADMAP.md`, or the landing page's coming-soon topics.
- **Action:** point at the "Coming soon" titles in the subject index.
- **Narration:** "What it isn't, yet: it hasn't been tested in classrooms, so we make no claims about learning outcomes. 26 topics are playable; more are marked coming soon. Next: a pilot with teachers, more topics, a validated mastery model, and Hindi and Marathi."

## Scene 10. Closing (10 s)

- **Screen:** the landing page's last section, "Find the missing understanding."
- **Narration:** "ELEVIA: don't just find the wrong answer. Find the missing understanding."

**Total: about 6 minutes 50 seconds.** If you need to save time, shorten Scene 2 to three books (about 25 s).

---

## Recording checklist

**Browser preparation**
- [ ] Use Chrome or Edge in a fresh profile or guest window, with no extensions, bookmarks bar or saved passwords visible.
- [ ] Set zoom to 100%, use a full-screen window, and close other tabs.
- [ ] Do one full rehearsal, then **reset the demo** (redeploy production, or `python scripts\demo.py reset` locally) so Riya's past-tense case is back in the queue and Dev has no history.

**Demo account preparation**
- [ ] Reset on the recording day (a production redeploy does it). "Upcoming" retests are relative to the reset date.
- [ ] Demo mode is on: the Try demo section shows 3 student cards and a teacher card.
- [ ] Have the teacher access code ready to paste. Never show it full-screen or say it aloud; the field masks it.
- [ ] Don't show the terminal window that printed the demo password.

**Screen resolution**
- [ ] Record at 1920×1080 (or 1440×900), at 30 fps or more.
- [ ] Use OS display scaling of 100–125% so text is readable when the video is compressed.

**Audio**
- [ ] Use an external or headset microphone in a quiet room, and record a 10-second level test first.
- [ ] Read the narration at a calm pace. It's written for roughly 150 words a minute.

**Cursor movement**
- [ ] Move the cursor slowly and deliberately; pause on the thing you're describing.
- [ ] Turn on cursor highlighting in the recorder if it has one. Don't circle the cursor or scroll quickly.

**Removing notifications**
- [ ] Turn on Do Not Disturb / Focus Assist, and close chat apps, email and calendar pop-ups.
- [ ] Hide desktop icons and the taskbar clock if possible.

**Checking the recording**
- [ ] Watch it end to end. Every typed answer should be readable, and the access code and password must not be visible.
- [ ] Check the audio is in sync, clear, and has no clipping.
- [ ] Check that every claim spoken matches what is on screen.

**Exporting the final video**
- [ ] Export as MP4 (H.264, AAC), 1080p, under the competition's size limit.
- [ ] Optionally add captions (the narration above can become the subtitle file).
- [ ] Upload as **Unlisted** (or as instructed), test the link in a private window, and paste it into `ROUND3_SUBMISSION_README.md`.
