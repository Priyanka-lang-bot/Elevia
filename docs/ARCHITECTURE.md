# ELEVIA technical architecture

## One deployable app

```
Browser ── public/ (static: index.html landing, app.js, learn.js, progress.js, landing.js, CSS, fonts, img)
   │  same origin, cookie session
   ▼
/api/*  ── app.py (FastAPI, one Vercel serverless function)
            ├─ backend/accounts/*   accounts, consent, schools, sharing, permissions, rate limits
            ├─ backend/learning.py  /learn: student journey + dashboard (login required, except /learn/catalog)
            ├─ backend/progress.py  /progress: teacher / parent / shared views, review queue, intervention history
            ├─ backend/demo.py      /demo: one-click student demo; teacher demo with the access code
            ├─ backend/history.py   six-month timeline, subject progress, skill map, class overview (from records)
            ├─ backend/clock.py     the one place the backend reads the time (seed-only simulated calendar)
            ├─ backend/orchestrator.py  the workflow: diagnostic → verification → learning → retest
            │     └─ backend/agents/  diagnoser · checker · planner · tutor (rule-based)
            ├─ backend/engine.py    answer checking dispatcher
            │     ├─ fractions_engine.py (exact Fraction arithmetic, unchanged)
            │     └─ generic_engine.py   (mcq, exact numeric, accepted text, predict-the-output)
            ├─ backend/content.py   curriculum loader + validation
            └─ backend/db.py / turso.py  SQLite locally, Turso (hosted SQLite) on Vercel
                                         (Vercel without Turso: temporary /tmp/elevia.db)
scripts/demo.py   seed / reset / status of the fictional demo school (run from a laptop)
```

**Decision: keep one FastAPI app and a no-build vanilla-JS frontend.** The existing project already deployed this way, it needs no build step, and it keeps the Content-Security-Policy strict (`script-src 'self'`, no inline scripts, no third-party hosts). A framework rewrite would have added risk without adding capability.

## The learning workflow

```
check-in (5 q) ─▶ Diagnoser ─▶ suspected gap? ──no──▶ "No gap found"
                                   │yes
                                   ▼
                     Checker: 2 NEW questions
           ┌───────────────┼──────────────────┐
       rejected       inconclusive        confirmed
   "it was a slip"  → teacher review   → Planner (prerequisites) → Tutor (lesson + practice)
                     (confirm / reject)                                   │
                                                    retest after delay: 3 NEW questions
                                                ┌──────────────┴──────────────┐
                                           ≥ 2 of 3: gap resolved,     < 2: gap stays open,
                                           skill mastered              replan → new lesson → new retest
```

Guarantees, each covered by tests:
- The Planner raises an error for an unverified gap; no plan or lesson exists before confirmation.
- Verification and retest questions are always unseen by that student; the original check-in is never repeated.
- Only a passed retest can set a skill to "mastered".
- Same answers → same outcome (no randomness, no LLM in decisions).
- An answer is committed before the workflow runs; if the workflow crashes, the answers are kept and the case goes to teacher review.

## Curriculum model

`data/curriculum.json` lists **subjects → topics**. Each topic has a unit, grade range, description, learning objectives, skills, and two diagnostic sets (A/B, alternating between rounds). Topic content lives in `data/topics/<topic>.json`:

- `skills`: id, name, grade, description, **prerequisites** (can cross topics, e.g. percentages → decimal place value)
- `misconceptions`: code → label, explanation, gap skill
- `questions`: pool (`diagnostic:<topic>:A|B`, `verification:<skill>`, `practice:<skill>`, `retest:<skill>`), type, prompt, answer, options/accepted answers/code, `patterns` (wrong answer → misconception), hints, worked solution, difficulty role (`same_type` / `similar_concept`)
- `lessons`: per skill: title, big idea, steps, sense check, worked examples

Content is **authored as code** in `scripts/curriculum/*.py` and compiled by `scripts/build_curriculum.py`, so that:
- maths answers and the answers each misconception would produce are **computed**, not typed;
- every Computer Science answer is checked by running the fixed snippet (restricted builtins) at build time;
- the whole bank is validated by the same loader the app uses (unknown skills, unknown misconception codes, a "misconception answer" equal to the right answer, empty pools… all fail the build).

The original fractions files are loaded unchanged and merged in, so the agents see one skill graph. **Adding a topic** = one authoring module + one entry in `SUBJECTS`; no workflow or UI code changes.

## Data model (additions in rounds 2 and 3)

| Table | Why |
|---|---|
| `learner_links (user_id, student_id)` | Connects a login account to its learning record (`students`), which the agents already use. |
| `case_topics (case_id, topic_id)` | Which topic a case belongs to. A **new table instead of a new column**, so the live Turso database only gains a table (no `ALTER`). Cases without a row are fractions cases, so old data stays valid. |

| `demo_profiles (user_id, student_code, reference_date, period_start)` | Labels for the fictional demo students, shown on their dashboards so a demonstration account is never mistaken for a real one. |
| `demo_registry (kind, ref_id, slug)` | Lists every row the demo seed created (users, school, class). One-click login and reset only ever touch rows listed here. |

Students can have one active case **per topic**, so a 24-hour retest wait in one topic doesn't block learning another.

## Dashboards: what to show next

- **Student "What to do next".** `learning._next_step()` picks one action from the student's own state. The priority order is:
  1. an unlocked retest;
  2. a retest, double-check, lesson or check-in in progress;
  3. waiting for a retest;
  4. a recommended new topic;
  5. nothing.

  The card links straight to that step.
- **Teacher review queue.** `/progress/students` returns every `teacher_review` case in the teacher's classes. Each entry has the topic, skill, suspected misconception and a plain-language reason (e.g. "Double-check was mixed: confirm or reject the gap"). The same call returns the latest 15 `teacher_overrides` as the intervention history.
- **Parent summary.** One card per child, built from the same data and limited by the consent scopes.

## Learning history (backend/history.py)

- **Sources.** Computed on each request from four tables only:
  - `responses` (every answer);
  - `agent_runs` (each role's decision and its time: diagnose, evaluate_verification, teach, schedule_retest, evaluate_retest);
  - `teacher_overrides`;
  - `skill_mastery`.
- **Counting rule.** Practice answers never count towards progress, which is the same rule the dashboard uses, so every figure agrees.
- **Student.** `/learn/history` and `/progress/students/{id}/history` return:
  - monthly figures;
  - an event list;
  - upcoming retests;
  - subject progress;
  - a skill map.

  The second route is permission-checked; misconception names and the Checker's reasons are shown only with the `gaps` scope.
- **Teacher.** `/progress/students` adds a class overview per class:
  - by subject;
  - monthly trend;
  - needs attention;
  - upcoming retests;
  - difficult topics;
  - frequent misconceptions (distinct students);
  - repeated failed retests;
  - most improved (passed after a failed retest).

## The demo's six-month history (scripts/demo.py + backend/clock.py)

- **Real routes, simulated dates.** The seed drives the real HTTP routes. Before each step it sets a simulated clock (`clock.simulated()`), which only the seed calls; no request can change it, and it is always restored. Every record therefore carries a natural past timestamp.
- **Delays honoured.** A retest can only start once it is due, exactly as on the live site.
- **Deterministic.** The calendar ends on the reference date, so the same reference date gives the same history.
- **Checked as it goes.** Each step asserts the stage the workflow reached, so a rule change stops the seed instead of producing an inconsistent story.

## Demo mode

- **Off by default.** `/api/demo/login` returns 404 unless `ELEVIA_DEMO_MODE=1`.
- **Normal sessions.** When on, it creates an ordinary session (same cookie, CSRF and expiry) for a student slug (`riya`, `fresh`, `arjun`), or for `teacher` when the request carries the judges' access code (`ELEVIA_DEMO_TEACHER_CODE`, 8+ characters, compared in constant time, 10 wrong tries per 10 minutes per IP). It only ever does this for a user listed in `demo_registry` who is still active.
- **Parents and admin never.** Their demo accounts exist so the student data has real consent and a real school behind it, but their slugs are refused with 403. They log in with a password like anyone else. Demo passwords are not in the repository (`ELEVIA_DEMO_PASSWORD`, or a random one printed once by the seed).
- **No secrets in the page.** No password or token is sent to the page.
- **Limits.** Logins are rate-limited per IP (60 per 10 minutes).
- **Guarded actions.** Demo users can't withdraw consent, change parent permissions, send invitations or unassign teachers (`refuse_for_demo`).
- **Seeding.** `scripts/demo.py seed` creates the demo school through the real routes: sign-up, consent, teacher approval and answering questions. It refuses if demo rows already exist or an email is already used by a real account.
- **Reset.** `reset` deletes only registry-listed rows, then seeds again. Tests check that a real user created alongside the demo survives a reset.

## Access control

Every progress read goes through `accounts.permissions.access_via()` and is written to `access_log`:
- teacher → students approved into a class the teacher is assigned to (school subscription active);
- parent → linked child, only for the scopes the consent includes (`view_progress`, `view_assessments`, …);
- anyone → an adult learner who shared specific scopes with them;
- school admin → roster only, never learning data.

Teacher actions (`/progress/cases/{id}/decision|focus|note`) require being the student's class teacher and a 5–500 character reason; they reuse the orchestrator's override functions, which log to `teacher_overrides`. The older PIN-protected `/api/teacher/*` routes are blocked on Vercel.

## Optional AI

`backend/llm.py` can rewrite the Diagnoser's explanation and the Tutor's note/steps when an API key is configured. Output must match a schema, may not claim certainty, and lesson arithmetic is re-checked; any failure uses the template text. It is off unless configured and never makes a decision.

## Security summary

scrypt password hashing; HttpOnly session cookies; CSRF check for cookie requests; login lockout and rate limits (stored in the database, so they work across serverless instances); strict CSP and security headers in `vercel.json`; fonts self-hosted (no third-party requests); input length limits on every body; parameterised SQL throughout.
