# Judge demo script (5–7 minutes)

## Before the session

1. **Seed the demo** on the database the site uses (Turso when `TURSO_DATABASE_URL` is in `.env`). Do it on the morning of judging so "upcoming" retests are still upcoming:
   ```powershell
   $env:ELEVIA_DEMO_PASSWORD = "<choose one; keep it private>"
   python scripts\demo.py reset          # or 'seed' the first time
   ```
   The six-month history ends on the reference date: today by default, or `--reference-date 2026-11-23` to fix it.
2. **On the server**, set:
   - `ELEVIA_DEMO_MODE=1` (one-click student demo);
   - `ELEVIA_DEMO_TEACHER_CODE=<a code of 8+ characters>` (opens the teacher demo).

   Give the code to the judges privately. It is not in the repository or the page.
3. Open the landing page and click **Try demo**. You should see three student cards and a teacher card with an access-code box.
4. **After a rehearsal**, run `python scripts\demo.py reset` again. It deletes only demo rows and recreates the same history.

All demo people are fictional. Riya Sharma is student ID DEMO-09-001 in Class 9 A, ELEVIA Demonstration School, 2026-27. Her teacher is Ananya Mehta.

## 1. The problem (landing page, 40 s)

- Hero: *"Don't just find the wrong answer. Find the missing understanding."*
- Scroll the marked-up worksheet: marks say what, not why; one mistake can be a slip; the real gap is often earlier.
- **What's built**: open a folder or two. Each one says what it does, how it works and what is built.
- *"Rule: verify before you teach. A suspected misconception is a hypothesis until new questions confirm it."*

## 2. Six months of a real learner (Try demo → Riya Sharma, 2 min)

1. Click **Open as Riya**. Point at the **Demonstration account** banner (student ID, class, history dates).
2. **What to do next**: her Data types lesson. Continue learning shows a retest booked for tomorrow and a case waiting for her teacher.
3. **Your last six months**: 141 answers, 9 gaps confirmed, 3 rejected as slips, 8 of 11 retests passed. Open **Show as a table**: the months add up to the totals.
4. **Progress by subject**: all five subjects, including Social Science. Then the **skill map**: mastered skills are exactly the ones with a passed retest.
5. **Learning history**: filter to *Social Science*. Show the inconclusive double-check, the teacher's confirmation with her reason, the lesson, the retest booked, then *Retest passed 3/3: skill mastered*.
6. *"Every record here was written by the real Diagnoser, Checker, Planner and Tutor rules. Only the answers were simulated, and the dates spread over six months."*

## 3. One topic live (Try demo → Dev Kapoor, 1.5 min)

1. Back on the landing page, click **Open as Dev**. Choose grade 9, then **Mathematics → Fractions → Start the check-in**.
2. Check-in: answer **2/5** for 1/2 + 1/3 and **3/7** for 1/4 + 2/3, and the rest correctly (1/5 + 2/5 = 3/5, 1/2 = 4/8, 6/8 = 3/4).
3. **Double-check**: "Possible gap: not confirmed yet". Answer **2/9** for 1/3 + 1/6, and **10** for the lowest common denominator of 1/4 and 1/6.
4. **Gap confirmed → lesson** quoting his own answer. Show a hint, answer a practice question, click **I'm done practising**.
5. **Retest** is booked for 24 hours later. Click **Start now (demo shortcut)**; the shortcut is logged. Answer 3/3 → **Gap closed**.

## 4. The teacher (teacher card + access code, 1.5 min)

1. Enter the access code on the teacher card. The **class overview** shows 5 students, confirmed gaps open, upcoming retests and who needs attention.
2. **Class insights**: topics causing difficulty, the most frequent misconceptions, Arjun's repeated failed integers retests, and the most improved skills (passed after a failed retest).
3. In the **review queue**, open **Riya Sharma · Past tense verbs**. Her six-month timeline and skill map are at the top. In the Past tense verbs panel, show:
   - the Diagnoser's hypothesis;
   - her check-in answers;
   - the double-check answers (one right, one a different mistake);
   - the Checker's verdict: *Mixed evidence… sent to a teacher*.
4. Click **Confirm gap and teach** without a reason: it asks for one. Type a reason and confirm. The case moves to learning, the reason appears in the case audit, Riya's history shows *Teacher confirmed the gap*, and **Intervention history** lists it first.

## 5. Close (30 s)

- **Honest scope:**
  - the roles are deterministic rules, not autonomous AI agents;
  - 26 topics in 5 subjects are playable; many more are marked "coming soon";
  - no classroom trials yet, so no claims about learning outcomes;
  - the demo data is synthetic and labelled as such.
- **Evidence** (`docs/TEST_RESULTS.md`):
  - 202 automated tests, run on both database backends, including tests that every dashboard figure is backed by records;
  - 26 browser checks covering the student, teacher and history journeys.

## If something goes wrong

- **"The live demo isn't switched on"**: `ELEVIA_DEMO_MODE` isn't set on the server, or the demo isn't seeded.
- **The teacher card says it isn't switched on**: `ELEVIA_DEMO_TEACHER_CODE` is missing or shorter than 8 characters.
- **Riya's case isn't in the queue, or her retest is already due**: someone used the demo, or it was seeded on an earlier day. Run `python scripts\demo.py reset`.
- **Dev gets "Waiting for your teacher"**: the double-check answers were mixed. Use the teacher view to confirm, or reset.
- **Lost connection**: progress is saved after every answer, so just reload.
