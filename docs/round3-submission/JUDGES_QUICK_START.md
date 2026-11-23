# ELEVIA: Judges' quick start (3–5 minutes)

**Open:** `[LIVE PROTOTYPE URL, to be filled in by the team]`. The teacher access code is given to you separately by the team; it is not published.

Everything here is fictional demonstration data. Nothing you do affects real students, and the team resets the demo between judging sessions.

## 1. Enter the demo (no sign-up)

1. On the landing page, click **Try demo** (top bar, or the hero button).
2. You'll see four cards:
   - **Riya Sharma**: a Grade 9 student with **six months of history**. Start here.
   - **Dev Kapoor**: a new learner with no history, to try a topic yourself.
   - **Arjun Patel**: a classmate who is finding maths hard.
   - **Ananya Mehta (teacher)**: needs the access code.
3. Click **Open as Riya**.

*If the demo section says "The live demo isn't switched on", demo mode is off on the server; please contact the team.*

## 2. Student mode: Riya's dashboard (1 minute)

- **Demonstration account** banner: student ID DEMO-09-001, Class 9 A, ELEVIA Demonstration School, 2026-27.
- **What to do next**: one recommended action.
- **Your last six months**: monthly activity. Click **Show as a table** to see the exact figures; the months add up to the totals.
- **Progress by subject**: all five subjects. The **skill map** marks mastered skills ✓; a skill only counts as mastered after a retest on new questions.
- **Learning history**: choose a subject in the *Show* box (try *Social Science*) to see each check-in, double-check verdict, lesson, retest and teacher decision.

## 3. Try a supported subject yourself (2 minutes)

1. Click **Log out**. On the login page, under the demo cards, click **Open as Dev**.
2. Choose a grade, pick **Mathematics → Fractions**, and click **Start the check-in**.
3. **Diagnostic:** answer the five questions. To see the verification process, deliberately make the classic mistake on both additions: **1/2 + 1/3 → 2/5** and **1/4 + 2/3 → 3/7**. Answer the rest correctly (3/5, 4, 3/4).
4. **Verification:** ELEVIA says *Possible gap: not confirmed yet* and asks two **new** questions. Answer **2/9** (1/3 + 1/6) and **10** (lowest common denominator of 1/4 and 1/6) to confirm it. Answer them correctly instead and it is rejected as a slip.
5. **Lesson:** the lesson starts from your own wrong answer. Do two practice questions (**10**, then **8**), then click **I'm done practising**.
6. **Retest:** it's booked for 24 hours later. Click **Start now (demo shortcut)**; the shortcut is logged. Answer **11/12**, **13/15**, **13/24** → **Gap closed**.

Other subjects work the same way: the tabs at the top of Dev's dashboard hold all five subjects and 26 playable topics. Topics marked *coming soon* aren't playable.

## 4. Teacher mode (1–2 minutes)

1. Click **Log out**, then open the landing page again and click **Try demo**.
2. On **Ananya Mehta**'s card, type the access code and click **Open the teacher view**.
3. Read the **Class overview** (5 students, who needs attention and why, upcoming retests) and **Class insights** (topics causing difficulty, frequent misconceptions, repeated failed retests, most improved).

### Inspect a student's learning case
1. In **Review queue**, click **Review** on *Riya Sharma · Past tense verbs*.
2. Riya's profile opens with her six-month timeline and skill map. Scroll to the **Past tense verbs** panel:
   - **Diagnoser**: the suspected misconception;
   - **Check-in answers** and **Double-check answers**: one right, one a *different* mistake;
   - **Checker's verdict**: mixed evidence, so it was sent to the teacher.
3. Type a reason (it's required) and click **Confirm gap and teach**, or **Reject**. The decision appears in the case audit, Riya's learning history and the **Intervention history** on the overview.

## 5. Understanding the historical data

- **Real rules, simulated answers.** The six months were produced by running ELEVIA's real rules (the same code you just used) on **simulated answers**, with dates spread over the six months before the demo's reference date.
- **No invented numbers.** Every number on the dashboards is computed from stored records: answers, the Checker's verdicts, lessons, retests and teacher decisions.
- **Backed by records.** A skill marked mastered always has a passed retest behind it; a confirmed gap always has the Checker's verdict or a logged teacher decision. Automated tests check this.
- **Fictional.** These are not real students, and ELEVIA hasn't been tested in classrooms yet.
