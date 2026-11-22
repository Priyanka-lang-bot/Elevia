# Judge demo script (5–7 minutes)

## Before the session (once)

1. **Seed the demo school** on the database the site uses: `python scripts\demo.py seed` (it uses Turso when `TURSO_DATABASE_URL` is in `.env`). Run `python scripts\demo.py status` to confirm.
2. **Turn on demo mode:** set `ELEVIA_DEMO_MODE=1` (a Vercel environment variable, or in your shell locally). Leave `ALLOW_EARLY_RETEST` on (the default) so the 24-hour retest wait can be skipped on stage; the shortcut is recorded.
3. Open the landing page. The **"Explore the live demo"** section with six cards should be visible. If it isn't, demo mode is off.
4. **After a rehearsal**, run `python scripts\demo.py reset` to put every demo account back to its starting state. It deletes only demo rows.

All demo accounts are fictional. Password for normal login, if needed: `Demo-Pass-2026!`.

## 1. The problem (landing page, 45 s)

- Hero: *"Don't just find the wrong answer. Find the missing understanding."*
- Scroll through **"A wrong answer is a symptom"** and **"How ELEVIA works"**: four roles, fixed rules and no AI in decisions.
- **Subjects**: 4 subjects and 24 playable topics. The grey "coming soon" chips are honest gaps, not fakes.
- *"Our rule is 'verify before you teach'. A suspected misconception is only a hypothesis until new questions confirm it."*

## 2. A new student, live (card: Ananya Rao, 2.5 min)

1. Click **Explore as Ananya**. Her empty dashboard says what to do first. Choose grade 6, then **Mathematics → Fractions → Start the check-in**.
2. **Check-in**, 5 questions. Make the classic mistake on the two additions and answer the rest correctly:
   - `1/2 + 1/3` → **2/5**
   - `1/4 + 2/3` → **3/7**
   - others, e.g. `1/5 + 2/5` → **3/5**, `1/2 = ?/8` → **4**, `6/8` simplest → **3/4**
3. **Double-check**: point at *"Possible gap: not confirmed yet"*. *"Nothing has been taught yet. It asks two NEW questions."*
   - `1/3 + 1/6` → **2/9**
   - lowest common denominator of 1/4 and 1/6 → **10**
4. **Gap confirmed → lesson.** Show "Why this lesson" quoting her own answer, the steps and the worked examples. Use **Show a hint**, answer a practice question, then click **I'm done practising**.
5. **Retest scheduled** (24 h). Click **Start now (demo shortcut)** and answer all three correctly → **Gap closed**, and the skill is mastered on her skill map.

## 3. A student with history (card: Riya Sharma, 45 s)

- Her dashboard leads with **"What to do next"**: continue her *Past tense verbs* lesson, which is in progress. A Loops retest is booked under upcoming retests.
- Point out two mastered maths topics (Percentages took a second attempt after a failed retest) and a Science check-in where no gap was found.
- Optional: open **Computer Science → Loops** to show a predict-the-output question. *"Student answers are compared as text; their code is never run."*

## 4. The teacher (card: Meera Iyer, 1.5 min)

1. **Review queue**: Arjun, *Fractions*, "Double-check was mixed: confirm or reject the gap". Open it.
2. Show the evidence (his answers and the Checker's reason). Click **Confirm gap and teach** without a reason, and the app asks for one. Type a reason and confirm. The stage moves to learning, and the decision appears in **Intervention history** with her name and reason.
3. The class table shows each student's confirmed gaps. *"Teachers see only their own classes, and every view is logged."*

## 5. The parent (card: Sunita Sharma, 30 s)

- A plain-language summary of **Riya only**, limited to what Riya's consent allows, with no review controls.

## 6. Close (30 s)

- **Honest scope:**
  - rule-based roles, not autonomous AI;
  - 24 topics built and tested; more marked "coming soon";
  - no classroom evaluation yet, so no learning-outcome claims.
- **Evidence:**
  - 185 automated tests, run on both database backends;
  - 17 browser checks covering this exact journey;
  - every topic tested end to end (see `docs/TEST_RESULTS.md`).

## If something goes wrong on stage

- **Demo cards missing:** demo mode is off, or the demo isn't seeded. A card reporting "needs reset" means someone changed an account: run `python scripts\demo.py reset`.
- **Ananya gets "Waiting for your teacher":** the double-check answers were mixed. Log in as Meera to confirm, or reset.
- **A question differs from the sheet:** answer it correctly. Only the two additions need the mistake.
- **Network hiccup:** progress is saved after every answer, so just reload.
