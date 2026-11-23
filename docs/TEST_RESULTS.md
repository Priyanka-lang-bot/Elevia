# Test results

Every number below comes from runs I actually executed. The latest runs were on 23 Nov 2026, on the `six-month-demo` branch (based on `landing-redesign`, which is based on `round3`).

## Automated tests (pytest)

| | Result |
|---|---|
| Baseline before round 3 work (commit `bcb020a`) | **81 passed** |
| End of round 3 (`round3`, `cb4c41b`) | **185 passed** |
| Landing redesign (`landing-redesign`, `7992fac`) | **186 passed** |
| Now, local SQLite: `python -m pytest -q` | **202 passed, 0 failed** |
| Now, through the Turso connector fake: `ELEVIA_TEST_TURSO=1 python -m pytest -q` | **202 passed, 0 failed** |

| File | Tests | Covers |
|---|---|---|
| `test_accounts.py` | 28 | Sign-up pathways, password hashing, lockout, sessions, consent, school codes, teacher approval, sharing, access requests |
| `test_agents.py` | 20 | Diagnoser, Checker, Planner and Tutor rules; AI fallback paths (simulated) |
| `test_clock.py` | 5 | The seed-only simulated clock: real time by default; moves every clock in the block; always restored, even after an error; no request can change it |
| `test_demo.py` | 12 | Demo mode off by default; one-click login for each student (HttpOnly, SameSite=Lax, no token in the body); parent and admin demo accounts never one-click; **teacher demo only with the judges' access code** (the code is never sent to the page; short codes count as off; wrong codes refused and rate-limited); demo login never reaches real accounts; rate limit; guarded actions; **reset restores the same state and leaves a real user untouched**; student, teacher and parent dashboards agree; next step, queue and intervention history |
| `test_demo_history.py` | 5 | **Every dashboard figure is backed by records**. Mastered skills ↔ passed retests (≥ 2/3) recorded by the Checker. Confirmed gaps ↔ the Checker's verdict or a logged teacher decision. Lessons in the history ↔ stored lessons. Teacher actions ↔ saved overrides with reasons. Failed retests ↔ a new plan afterwards. Monthly figures add up to the totals and match the dashboard and the database; all 5 subjects active; upcoming retests have future dates; no early-retest overrides while seeding. Class overview and insights computed from the same records. A teacher review is saved and appears in the history and the intervention list. History endpoints respect permissions. **The same reference date gives an identical history after a reset, with no duplicates** |
| `test_fractions.py` | 20 | Exact fraction parsing and checking, mistake patterns |
| `test_learning_journey.py` | 35 | Correct answers, suspected misconception, careless slip, confirmed, rejected, inconclusive, retest pass/fail, replanning, persistence, errors and duplicates, exact maths |
| `test_progress.py` | 5 | Teacher review with reasons; access rules for teacher, admin, stranger, student, parent scopes, learner sharing |
| `test_subjects.py` | 59 | **Full journey and a rejected-gap journey on each of the 25 non-fraction topics** (parametrised, so the 2 Social Science topics run through the real engine too), plus curriculum completeness for all 26 topics, exact checking, code never executed, public catalogue |
| `test_workflow_api.py` | 11 | Older engine API |
| `test_web_entry.py` | 2 | Website entry point |

## Build-time content checks (`python scripts/build_curriculum.py`)

- **5 subjects, 26 topics, 58 skills, 86 misconception patterns, 1,019 questions, 55 lessons**, all validated by the build. It checks ids, answers present, distractors mapped to misconceptions and roles filled.
- Every Computer Science answer (questions and lesson examples) is confirmed by running the snippet with restricted built-ins.
- Every maths answer and every misconception answer is computed, never typed by hand.

## Seeding the six-month demo

`ELEVIA_DEMO_PASSWORD=… python scripts/demo.py seed --reference-date 2026-11-23` on a fresh SQLite database took **about 9 seconds**. Results from that run:
- **Calendar:** history from 25 May 2026 to 23 Nov 2026.
- **Students:** 5 students with 34 learning cases.
- **Riya Sharma:**
  - 16 check-ins and 141 graded answers;
  - 9 gaps confirmed by the Checker, 3 rejected as slips, 2 inconclusive (sent to the teacher);
  - 14 lessons;
  - retests 8 passed and 3 not passed;
  - 8 skills mastered;
  - 3 teacher actions.
- **Retests:** 0 early-retest overrides.

Every step asserts where the real workflow ended (for example, an "unclear" case must reach `teacher_review`). If a rule changed, the seed would stop instead of writing an inconsistent story.

## Browser end-to-end (`python scripts/e2e_browser.py`, headless Chromium)

**26 of 26 checks passed, 0 console errors.** The run used a fresh database seeded with the six-month demo, demo mode on and a teacher access code set. The browser's own log line for the deliberately wrong access code is the only entry the test discards, and only during that step.

1. Landing: 50 links checked; index of 26 playable topics in 5 subjects (coming-soon titles are not links); 3 student cards + a teacher card that needs the access code; no password or code in the page; no broken images
2. For students: the section slides in once; the Dashboard/Double-check/Lesson/Result tabs work by click and arrow keys (Home/End), with a caption per screen
3. Try demo in the top navigation scrolls to the demo cards
4. Book stack: scrolling opens one book at a time; clicking a spine opens its page
5. Worksheet: annotations appear one idea at a time as you scroll
6. What's built: folders slide in once and all nine fit; click, arrow keys and hover open one panel showing how it works and what's built
7. Get started opens the account-type chooser
8. One-click demo login (Dev, new learner) lands on the dashboard
9. Grade is asked once, then the fractions check-in starts
10. Diagnoser: suspected gap shown as not confirmed; double-check asked
11. Checker confirms → Planner + Tutor lesson
12. Practice → delayed retest (demo shortcut) → 3/3 → gap closed
13. A Social Science topic plays through the same engine
14. Reload keeps progress (resumes at question 3 of 5)
15. **Six-month timeline**: 7 calendar months; the monthly table adds up to the totals (141 answers), which match the dashboard header
16. All five subjects shown; the skill map's mastered skills match the mastered count (8); the history filters by subject and shows retests and teacher decisions
17. Riya's next step opens her lesson in progress; finishing practice books a real delayed retest
18. Password login (Riya) works; the dashboard with timeline and skill map fits a 390 px phone screen
19. **Teacher demo**: a wrong access code is refused; the right one opens the class overview, insights and review queue
20. Riya's profile: six-month timeline, skill map, and the flagged case with the Diagnoser's hypothesis, check-in answers, double-check answers and the Checker's verdict
21. The teacher confirms with a reason. It is saved in the case audit, Riya's history and the intervention history, and the queue updates
22. Parent (Sunita) sees only Riya, with her timeline, and no review controls
23. Student sees the teacher's decision on her journey
24. Phone (390 px) and tablet (768, 1024 px): Try demo always visible, menu opens, tap-to-open folders and books, no horizontal overflow
25. Without JavaScript: every folder sheet, book page, worksheet annotation, the student section and all 26 topics are readable
26. Reduced motion: no reveal animations, content shown straight away

I also reviewed screenshots by eye:
- the landing sections at 390, 1024, 1440 and 1920 px;
- the student dashboard, teacher overview and student detail at 1440 px;
- the "demo is off" state.

## Deployment checks (23 Nov 2026)

- **Build:** the Vercel `frontend-pmvi` project built the `six-month-demo` branch (commit `a80b721`) successfully.
- **Preview, opened in a browser** (`frontend-pmvi-git-six-month-demo-…vercel.app`):
  - `/api/health` → 200.
  - The catalogue serves 5 subjects, 26 topics and 1,019 questions.
  - The landing page renders all 26 topic links, the 4 screenshot tabs, and all nine folders inside the window.
  - `/api/demo/accounts` → `enabled: false`, as expected, because `ELEVIA_DEMO_MODE` is not set.
  - The only console error was Vercel's own preview-toolbar script, blocked by ELEVIA's content security policy. Visitors without a Vercel login don't load it.
- **Environment variables** (names and scopes only; I did not read or change any values):
  - `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` are now set for Production, Preview and Development, with branch-specific database URLs for `round3` and `backup-before-round3`.
  - `ELEVIA_DEMO_MODE` and `ELEVIA_DEMO_TEACHER_CODE` are not set.
- **Not verified on the live site:**
  - The demo accounts and their history. They must be seeded into the Turso database with the owner's credentials (`python scripts/demo.py reset`), and the two demo variables added.
  - Production. `main` has not been changed.
- **The `frontend` Vercel project** still fails on every commit. It looks like a duplicate, and I left it untouched.

### Earlier (22 Nov 2026)

- Every `/api/*` call on the previews and on `main` returned 500, because no database was configured and the code directory is read-only. This was fixed on `round3` (commit `cb4c41b`): without Turso, the app falls back to `/tmp/elevia.db`.
