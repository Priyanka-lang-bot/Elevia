# Test results

All numbers below come from runs I actually executed on the `round3` branch (20 Nov 2026).

## Automated tests (pytest)

| | Result |
|---|---|
| Baseline before Round 3 work (commit `bcb020a`) | **81 passed** |
| Now, local SQLite: `python -m pytest -q` | **150 passed, 0 failed** |
| Now, through the Turso connector fake: `ELEVIA_TEST_TURSO=1 python -m pytest -q` | **150 passed, 0 failed** |

| File | Tests | Covers |
|---|---|---|
| `test_accounts.py` | 28 | sign-up pathways, password hashing, lockout, sessions, consent, school codes, teacher approval, sharing, access requests |
| `test_agents.py` | 20 | Diagnoser, Checker, Planner, Tutor rules; AI fallback paths (simulated) |
| `test_fractions.py` | 20 | exact fraction parsing and checking, mistake patterns |
| `test_learning_journey.py` | 35 | the 12 required Priority-1 areas: correct answers, suspected misconception, careless slip, confirmed, rejected, inconclusive, retest pass/fail, replanning, persistence, errors and duplicates, exact maths |
| `test_subjects.py` | 29 | **full journey on each of the 10 new topics**, rejected gap on each, replanning on a new subject, two topics side by side, dashboard, unknown topic, curriculum completeness, exact numeric/percent/negative/text/mcq checking, code never executed, public catalogue |
| `test_progress.py` | 5 | teacher sees and resolves an inconclusive gap (reason required, audited), reject + notes, other teacher/admin/stranger/student blocked, parent permission scopes, learner sharing |
| `test_workflow_api.py` | 11 | older engine API |
| `test_web_entry.py` | 2 | website entry point |

Tests changed rather than added (not deleted, each still checks its original intent):
- `test_fractions.py::test_content_loads…`: now loops over fraction questions only (the bank now holds other types) and still requires the original ≥ 60 fraction questions.
- `test_learning_journey.py`: grade bound moved from 12 to 13 (grades 3–12 are now accepted on purpose); over-long answer limit moved from 41 to 201 characters (science options are longer).

## Build-time content checks (`python scripts/build_curriculum.py`)

- 372 new questions + 77 original = **449 questions**, 39 misconception patterns, 28 skills, 25 lessons, all validated.
- Every Computer Science answer (questions and lesson examples) confirmed by running the snippet.
- Every maths answer and every misconception answer computed, never typed.

## Browser end-to-end (`python scripts/e2e_browser.py`, headless Chrome)

**16 of 16 checks passed, 0 console errors**, on a fresh database with demo accounts:
1. Landing: hero, 30 links checked (no dead links), live catalogue (11 topics), smooth in-page navigation
2. "Get started" opens the account-type chooser
3. Learner logs in, lands on the dashboard
4. Grade asked once, fractions check-in starts
5. Diagnoser: suspected gap shown as not confirmed
6. Checker confirms → Planner + Tutor lesson
7. Practice → delayed retest (demo shortcut) → 3/3 → gap closed
8. Code question renders and is checked
9. Reload resumes at the same question
10. Dashboard: continue learning, mastered skills, history
11. Dashboard fits a 390 px phone
12. Teacher: class overview → student detail with evidence and review form
13. Teacher confirms with a reason; lesson created; override logged
14. Parent sees the child's progress, no review controls
15. Student sees the teacher's decision
16. Landing on a phone: menu opens, no horizontal overflow

## Deployment checks

- Vercel `frontend-pmvi` project: the previous `main` commit (`bcb020a`) **failed** to build; the cause was `pyproject.toml` (the build before it, without that file, succeeded). After removing it, every pushed `round3` commit reports **"Deployment has completed"** (GitHub commit status from Vercel).
- Vercel `frontend` project: fails on every commit, including ones that build fine on `frontend-pmvi`, so it's likely a duplicate project with different settings.
- **Not verified:** I couldn't open `*.vercel.app` from my workspace (blocked by its network policy), so I haven't checked the live pages, the live API, or the live Turso database in a browser.
