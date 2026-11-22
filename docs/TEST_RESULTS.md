# Test results

Every number below comes from runs I actually executed on the `round3` branch (20–22 Nov 2026). The latest run was on commit `cb4c41b`.

## Automated tests (pytest)

| | Result |
|---|---|
| Baseline before round 3 work (commit `bcb020a`) | **81 passed** |
| End of round 2 | **150 passed** |
| Now, local SQLite: `python -m pytest -q` | **185 passed, 0 failed** |
| Now, through the Turso connector fake: `ELEVIA_TEST_TURSO=1 python -m pytest -q` | **185 passed, 0 failed** |

| File | Tests | Covers |
|---|---|---|
| `test_accounts.py` | 28 | Sign-up pathways, password hashing, lockout, sessions, consent, school codes, teacher approval, sharing, access requests |
| `test_agents.py` | 20 | Diagnoser, Checker, Planner and Tutor rules; AI fallback paths (simulated) |
| `test_fractions.py` | 20 | Exact fraction parsing and checking, mistake patterns |
| `test_learning_journey.py` | 35 | Correct answers, suspected misconception, careless slip, confirmed, rejected, inconclusive, retest pass/fail, replanning, persistence, errors and duplicates, exact maths |
| `test_subjects.py` | 55 | **Full journey and a rejected-gap journey on each of the 23 non-fraction topics** (parametrised), plus replanning on a new subject, two topics side by side, dashboard, unknown topic, curriculum completeness for all 24 topics, exact numeric/percent/negative/text/MCQ checking, code never executed, public catalogue |
| `test_demo.py` | 9 | Demo mode is off by default; one-click login per role (HttpOnly, SameSite=Lax cookie, no token in the body); demo login never reaches a real account; rate limit (60 per 10 min, then 429); guarded actions are refused for demo users; **reset restores the demo state and leaves real users untouched**; student, teacher and parent dashboards agree; next step, review queue and intervention history |
| `test_progress.py` | 5 | Teacher sees and resolves an inconclusive gap (reason required, audited), reject and notes, other teacher/admin/stranger/student blocked, parent permission scopes, learner sharing |
| `test_workflow_api.py` | 11 | Older engine API |
| `test_web_entry.py` | 2 | Website entry point |

## Build-time content checks (`python scripts/build_curriculum.py`)

- **24 topics, 54 skills, 82 misconception patterns, 943 questions, 51 lessons**, all validated by the build. It checks ids, answers present, distractors mapped to misconceptions and roles filled.
- Every Computer Science answer (questions and lesson examples) is confirmed by running the snippet with restricted built-ins.
- Every maths answer and every misconception answer is computed, never typed by hand.

## Browser end-to-end (`python scripts/e2e_browser.py`, headless Chromium)

**17 of 17 checks passed, 0 console errors**, on a fresh local database seeded with `scripts/demo.py seed` and with demo mode on:

1. Landing: hero, every link checked, live catalogue (24 topics), 6 demo cards, no broken images
2. "Get started" opens the account-type chooser
3. One-click demo login (Ananya, new student) lands on the dashboard
4. Grade is asked once, then the fractions check-in starts
5. Diagnoser: suspected gap shown as not confirmed; double-check asked
6. Checker confirms → Planner and Tutor build the lesson
7. Practice → delayed retest (demo shortcut) → 3/3 → gap closed
8. Code question: program shown, typed output checked
9. Reload keeps progress (resumes at question 3 of 5)
10. Dashboard: continue learning, mastered skill, history
11. Password login (Riya) works; dashboard with "What to do next" fits a 390 px phone screen
12. Riya via the login-page demo strip: her next step opens the lesson in progress
13. Teacher: review queue → Arjun's case with evidence and review form
14. Teacher confirms with a reason; lesson created; override logged
15. Parent (Sunita) sees only Riya, in plain language, with no review controls
16. Student sees the teacher's decision on their journey
17. Landing on a phone: menu opens, no horizontal overflow

## Deployment checks (22 Nov 2026)

- **Build:** the Vercel `frontend-pmvi` project builds every pushed `round3` commit successfully (GitHub commit status from Vercel). The latest is `cb4c41b`.
- **Runtime, before the fix:** I opened the preview in a browser. Every `/api/*` call returned `500 FUNCTION_INVOCATION_FAILED`. The `main` branch alias failed the same way.
  - Vercel's runtime logs showed `sqlite3.OperationalError: unable to open database file`.
  - The project has **no environment variables** (no `TURSO_DATABASE_URL`), so the app tried to create `elevia.db` in the read-only code directory.
- **Fix:** commit `cb4c41b`. On Vercel without Turso, the app now uses `/tmp/elevia.db`.
- **Runtime, after the fix** (`frontend-pmvi-git-round3-…vercel.app`):
  - `/api/health` → 200.
  - `/api/learn/catalog` → 200, with 4 subjects, 24 topics and 943 questions.
  - `/api/demo/accounts` → 200 with `enabled: false`, as expected, because `ELEVIA_DEMO_MODE` isn't set.
  - The landing page and login page render.
- **Not verified on the live site:**
  - Persistent data. `/tmp` is per instance, so data can disappear when Vercel recycles an instance.
  - The demo accounts, because they need Turso plus `ELEVIA_DEMO_MODE=1` and a seed.
  - Email sign-up, because there is no mail provider.
- **Vercel `frontend` project:** fails on every commit, including ones that build fine on `frontend-pmvi`. It's likely a duplicate project with different settings, and I didn't change or delete it.
