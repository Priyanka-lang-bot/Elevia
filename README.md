# ELEVIA: Verify before you teach

ELEVIA finds the misconception behind a student's wrong answers. It **checks that misconception with new questions before teaching anything**, teaches the missing step, then retests later on fresh questions.

It covers **5 subjects and 26 topics** (Maths, Science, English, Social Science, Computer Science), with 1,019 questions and 86 named misconception patterns. Everything is on one website, with real accounts for students, parents, teachers and school admins.

| Role | Job | How it decides |
|---|---|---|
| **Diagnoser** | Suggests the *possible* gap behind wrong answers. A single mistake is flagged as a possible slip. | Matches answers to named misconception patterns. Its output is always **suspected**. |
| **Checker** | Asks 2 new questions and marks the gap confirmed, rejected or inconclusive. Later runs the 3-question retest. | Fixed rules. The only part that can mark a skill mastered (2 of 3 on a delayed retest). |
| **Planner** | Turns a **verified** gap into a learning focus. | Walks prerequisites in the skill map. **Refuses unverified gaps.** |
| **Tutor** | Lesson, worked examples, hints and practice. | Authored content; maths answers are computed exactly. |

All four are deterministic, rule-based components coordinated by an orchestrator. They are **not autonomous LLM agents**, and the deployed website makes no AI API calls. Teachers can resolve unclear cases and change the focus, and every override is logged with a reason.

> ELEVIA identifies possible academic knowledge gaps from answers. It is not a clinical or psychological assessment. It has not been evaluated in classrooms, so it makes no claims about learning outcomes.

**Docs:**
- [Round 3 submission](docs/ROUND3_SUBMISSION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Feature matrix](docs/FEATURE_MATRIX.md)
- [Demo script (judges, 5–7 min)](docs/DEMO_SCRIPT.md)
- [Test results](docs/TEST_RESULTS.md)
- [Limitations and roadmap](docs/LIMITATIONS_AND_ROADMAP.md)

---

> **Round 3 submission package:** see [docs/round3-submission/](docs/round3-submission/ROUND3_SUBMISSION_README.md).

## What's on the website

- **Landing page** (`/`) is static, crawlable HTML in the app's notebook style, told through study objects:
  - a red-pen-marked worksheet that explains the problem one idea at a time as you scroll;
  - a stack of books for the four roles plus the retest; each book opens to its page as you scroll, or when you click its spine;
  - a drawer of folders for what's built (hover, tap or arrow keys);
  - a curriculum index of the 26 playable topics, with "coming soon" titles pencilled in and not linked;
  - one closing spread for "verify before you teach", About and the final call to action.

  **Try demo** sits in the top navigation and the hero. Everything is readable without JavaScript, and the page respects reduced-motion settings.
- **Accounts** support three pathways:
  - an individual student, with parent consent;
  - a school student, with a class code and teacher approval;
  - an independent learner aged 18 or over.

  Parents, teachers and school admins have accounts too. Security uses scrypt passwords, HttpOnly cookie sessions, CSRF protection, rate limits and an access log.
- **Student dashboard** (`#/learn`) leads with a **"What to do next"** card, then a **six-month timeline** (monthly chart with a table view), **progress by subject**, a **skill map** and the full **learning history**, all computed from stored records. The rest of the page shows subjects and topics, upcoming retests, gaps being worked on, mastered skills and recent activity.
- **Topic journey** (`#/learn/<topic>`) runs check-in → double-check → learn & practise → retest → result. It has a step tracker and plain-language explanations at every step, and progress persists across reloads.
- **Teacher portal** shows only students in your own classes. It includes a **class overview** (needs attention, upcoming retests, by subject, class trend) and **class insights** (topics causing difficulty, frequent misconceptions, repeated failed retests, most improved), plus:
  - a **review queue** of unclear cases, each with the reason it needs a teacher;
  - per-student evidence;
  - a review form to confirm or reject a gap, change the focus or add a note (a reason is required);
  - an **intervention history**.
- **Parent view** shows a summary card per child whose consent includes progress. It has no override controls.

### Subjects and topics

All 26 topics are playable end to end: diagnostic, misconception check, plan, lesson, practice, retest and skill-map update.

| Subject | Topics | Answer checking |
|---|---|---|
| Mathematics (11) | Fractions, Decimals, Percentages, Integers, Linear equations, Order of operations, Factors and multiples, Ratio and proportion, Perimeter and area, Averages, Angles | Exact `Fraction` arithmetic; misconception answers are computed by rule |
| Science (3) | Forces and motion, States of matter, Scientific reasoning (fair tests) | Multiple choice; each wrong option maps to a named misconception |
| English (4) | Past tense verbs, Subject–verb agreement, Parts of speech, Apostrophes | Accepted-answer lists and multiple choice |
| Social Science (2) | Latitude and longitude, Time zones and Indian Standard Time (Class 9 geography: India's size and location) | Multiple choice generated from coordinate and time tables; every answer computed |
| Computer Science (6) | Variables and assignment, Loops, Data types, Conditionals, Logical reasoning (Boolean logic), Algorithms | Predict the output. The expected output is verified by running the snippet at build time; **student input is compared as text and never executed** |

These topics are listed in the app as "coming soon" and can't be played yet:
- **Maths:** probability, area of triangles and circles, volume, graphs.
- **Science:** heat and temperature, light, electric circuits, plants and photosynthesis.
- **English:** reading comprehension, sentence construction, other tenses, vocabulary.
- **Social Science:** physical features of India, drainage, climate, what is democracy?, the French Revolution, poverty as a challenge.
- **CS:** functions, lists and data structures, sorting.

## Run it locally (Windows PowerShell)

```powershell
cd C:\Users\DELL\Desktop\Prausnex\elevia
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install --only-binary=:all: -r requirements.txt pytest
copy .env.example .env
python scripts\demo.py seed
$env:ELEVIA_DEMO_MODE = "1"
$env:ELEVIA_DEMO_TEACHER_CODE = "choose-a-judges-code"
python -m uvicorn app:app --reload
```

Open **http://localhost:8000** and click **Try demo**. The student cards open with one click. The teacher card needs the judges' access code, set with `$env:ELEVIA_DEMO_TEACHER_CODE = "<8+ characters>"` before starting the server. Everyone else logs in normally with the demo password, which is printed once by `demo.py seed` (or chosen with `$env:ELEVIA_DEMO_PASSWORD` before seeding). No demo password is stored in this repository.

The demo is a fictional **Class 9 A at ELEVIA Demonstration School (2026-27)** with **six months of history**:

| Demo account | Log in with | What it shows |
|---|---|---|
| Riya Sharma, DEMO-09-001, Grade 9 | `riya.demo` (one click) | Six months across 5 subjects: 16 check-ins, 8 skills mastered, two retests failed then passed, a lesson in progress, a retest due, a case waiting for her teacher |
| Arjun Patel, DEMO-09-002 | `arjun.demo` (one click) | Integers retest failed twice (handed to the teacher), a mixed fractions double-check, a teacher's note |
| Kabir Singh, Meera Nair, Zoya Khan (DEMO-09-003 to 005) | `kabir.demo`, `meera.demo`, `zoya.demo` | Classmates with different patterns: strong, steady with one teacher rejection, joined in month 4 |
| Dev Kapoor, new learner (19) | `demo.learner@example.com` (one click) | No history: run a topic live |
| Ananya Mehta, Class 9 teacher | `demo.teacher@example.com` (access code) | Class overview, insights, review queue, intervention history, each student's record |
| Sunita Sharma, parent | `demo.parent@example.com` | Riya only (each classmate has their own parent account) |
| Kavita Menon, school admin | `demo.admin@example.com` | Classes, teachers, enrolments (no learning data) |

**How the history is made.** `scripts/demo.py` runs the real routes on a simulated calendar (`backend/clock.py`, used only by the seed):
- accounts: sign-up, parent consent and teacher approval;
- learning: the Diagnoser → Checker → Planner → Tutor → retest workflow;
- teacher decisions: the review routes, each with a reason.

Only the answers are simulated. Retest delays are honoured, not skipped. The same reference date always gives the same history (`--reference-date YYYY-MM-DD`; the default is today).

**Demo mode safety.** One-click login only works when `ELEVIA_DEMO_MODE=1`. Otherwise `/api/demo/login` returns 404 and the Try demo section says the live demo is off, with Get started and Log in buttons instead. Further safeguards:
- **Students:** one-click works for the student accounts (Riya, Dev, Arjun).
- **Teacher:** opens only with the access code, which is compared in constant time and rate-limited (10 wrong tries per 10 minutes).
- **Parents and admin:** always refused with 403.
- **Real accounts:** never reachable. Demo login only signs in to accounts listed in `demo_registry`.
- **Sessions:** it issues a normal session, and no password or code appears in the page.
- **Locked actions:** demo accounts can't withdraw consent, change permissions or send invitations.

**Reset:** `python scripts\demo.py reset` deletes only the rows listed in `demo_registry` and seeds again. Real users are untouched, and this is tested. `python scripts\demo.py status` shows what exists.

**Tests:**
- `python -m pytest -q` runs 202 tests. Set `$env:ELEVIA_TEST_TURSO = "1"` first to run them through the Turso connector.
- `python scripts\e2e_browser.py` runs the browser end-to-end check (26 checks; needs Playwright and the `ELEVIA_DEMO_PASSWORD` / `ELEVIA_DEMO_TEACHER_CODE` the server uses).

**Curriculum:** topic content is generated by `python scripts\build_curriculum.py` from `scripts/curriculum/*.py`. The build validates every question and runs every code snippet with restricted built-ins. After changing it, run `python scripts\build_landing_index.py` to refresh the static subject index in the landing page (the page also refreshes it live from the API).

## Deploy on Vercel (with a Turso database)

Vercel runs `app.py` as one serverless function and serves `public/` from its CDN. Pushing to `main` deploys production; other branches get preview deployments.

1. **Turso:** create a database and copy its `libsql://…` URL and a read-write token. Use a **separate database for previews** so preview demos never touch production data.
2. **Vercel environment variables** (Project → Settings → Environment Variables):
   - **Required for persistence:** `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`.
   - **Demo (Production):** `ELEVIA_DEMO_MODE=1` (one-click student demo), `ELEVIA_DEMO_RESET_ON_DEPLOY=1` (each production build resets the demo), and a private `ELEVIA_DEMO_TEACHER_CODE` (8+ characters, the judges' teacher access code).
   - **Optional:**
     - `ELEVIA_DEMO_EMAIL_LINKS=1` to show email links on screen;
     - `EMAIL_MODE=smtp` + `SMTP_*` for real email;
     - `RETEST_DELAY_HOURS`;
     - `ALLOW_EARLY_RETEST`.
3. **Without Turso**, the function falls back to a temporary SQLite file in `/tmp`. Pages and the API work, but data is per instance and is lost when the instance is recycled. That's fine for a quick look, not for a judged demo.
4. **Tables** are created on first request (`CREATE TABLE IF NOT EXISTS`). Round 3 only **adds** tables (`learner_links`, `case_topics`, `demo_registry`).
5. **Demo accounts on Turso:** with `ELEVIA_DEMO_RESET_ON_DEPLOY=1`, the build step (`scripts/vercel_build.py`) resets the demo on every production deployment, touching only demo-registered records, in one transaction. From a laptop with the Turso values in `.env`, `python scripts\demo.py reset --fast` does the same. No demo password is stored anywhere: it comes from `ELEVIA_DEMO_PASSWORD` or is generated at random.
6. **Region:** `vercel.json` runs the functions in `bom1` (Mumbai) because the database is in `aws-ap-south-1`. Keep them in the same region, since every query is a network round trip.

Note: don't add a `pyproject.toml` with a `[project]` table; it breaks Vercel's build.

## Older Streamlit version (fractions only, local demo)

Kept for reference. It uses a shared demo teacher PIN, which is **not** secure; its unauthenticated API routes are switched off on Vercel. The website above replaces it.

### Run it locally (Windows)

Needs Python 3.10+.

```powershell
cd C:\Users\DELL\Desktop\Prausnex\elevia
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
python seed.py
```

**Terminal 1: backend**
```powershell
.venv\Scripts\activate
python -m uvicorn backend.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

**Terminal 2: frontend**
```powershell
.venv\Scripts\activate
python -m streamlit run frontend/app.py
```
Website: http://localhost:8501

(macOS/Linux: use `source .venv/bin/activate` and `cp .env.example .env`.)

> **"blocked by your organization's Device Guard policy"?** Windows is blocking the `.exe` launchers in the venv (`pip.exe`, `uvicorn.exe`, `streamlit.exe`). Always run them through Python, as shown above: `python -m pip`, `python -m uvicorn`, `python -m streamlit`.

**Run the tests**
```powershell
python -m pytest -q
```

**Reset the demo data:** `python seed.py --reset`

### Connecting a real AI model (optional)
Edit `.env`:
```
LLM_PROVIDER=anthropic        # or: openai  (any OpenAI-compatible API)
LLM_API_KEY=your-key-here
LLM_MODEL=                    # blank = provider default
LLM_BASE_URL=                 # only for e.g. Groq/OpenRouter: https://api.groq.com/openai/v1
```
Restart the backend. The sidebar shows which model is active. With no key, ELEVIA runs in **demo mode**: the same workflow, with rule-based agents and template wording, and the UI labels it that way (`rule-based`, `template (no AI)`). It never presents template text as AI output.

---

## 2. Demo students (sample data)

`seed.py` creates three **sample** students (labelled "sample" everywhere). Their records were produced by sending scripted answers through the real workflow:

| Student | State | Use it to show |
|---|---|---|
| **Asha** (Grade 5) | No activity | The live demo below |
| **Rohan** (Grade 5) | Full cycle done: gap confirmed → taught → retest passed | Progress page, improvement, agent log |
| **Meera** (Grade 4) | Verification inconclusive → waiting for teacher | Teacher review and override |

Pick a student in the left sidebar. **Teacher PIN:** `2468` (demo default) unless you set `TEACHER_PIN` in `.env`.

---

## 3. Demo script: the four agents in about 5 minutes

1. **Home** → *Start learning*. Make sure **Asha** is selected → *Start check-in*.
2. **Maths Practice**, answer the 5 questions like this:

   | Question | Type | Why |
   |---|---|---|
   | 1/5 + 2/5 | `3/5` | correct |
   | 1/2 = ?/8 | `4` | correct |
   | 1/2 + 1/3 | `2/5` | ✗ adds tops and bottoms |
   | 6/8 simplest | `3/4` | correct |
   | 1/4 + 2/3 | `3/7` | ✗ same mistake |

   → Score 3/5. The page says *ELEVIA is investigating*. The **Diagnoser** has a *suspected* gap (common denominators, high confidence, 0.80) and the **Checker** has picked 2 new questions. No plan exists yet.
3. Answer the Checker's questions: `1/3 + 1/6` → `2/9`, lowest common denominator of 1/4 and 1/6 → `10`.
   → **Confirmed** by the Checker. The **Planner** chooses *Finding common denominators* and the **Tutor** builds the lesson.
4. **Agent Activity**: show each agent's real run, its mode, and (toggle) the exact JSON passed between agents.
5. **Learning Room**: personal note quoting "1/2 + 1/3 with 2/5", steps, worked examples. Use *Show hint*, answer one wrong to show the worked solution, then *finish practice*.
6. **Maths Practice**: the Checker scheduled the retest for **24 h later**. Click *Demo override: start retest now* (this is recorded in the agent log). Answer `11/12`, `13/15`, `13/24`.
   → Gap **resolved**. **Progress** shows verification 0% → retest 100%, from real answers.
7. **Teacher Dashboard** → PIN `2468` → open **Meera** → confirm the gap with a name and reason → the Planner and Tutor run with `created_by = teacher:<name>`. Try *Change the learning focus* too.

Other paths worth showing: answer all 5 check-in questions correctly (no gap, nothing changes), or answer both verification questions correctly (gap **rejected**, plan unchanged).

---

## 4. Architecture

```
Streamlit (frontend/app.py)  --HTTP/JSON-->  FastAPI (backend/main.py)
                                                  |
                                       orchestrator.py  (workflow + agent_runs log)
                                   /        |         |        \
                            Diagnoser   Checker   Planner    Tutor      <- backend/agents/
                                   \        |         |        /
                         fractions_engine.py (exact Fraction checks, patterns, hints)
                         content.py (skill_map.json, questions.json, lessons.json)
                         llm.py (optional hosted LLM, schema-validated, mock fallback)
                         db.py  (SQLite: shared student learning record)
```

**Workflow stages:** `diagnostic → verification → learning → retest_pending → retest → completed`, with side exits `closed` (no gap / gap rejected) and `teacher_review` (inconclusive, or no content to act on).

**Safeguards**
- Correctness is decided only by `fractions.Fraction`. Question answers are *computed* from stored operands, so the answer key can't contain typos.
- The Planner raises `UnverifiedGapError` unless the gap is confirmed by the Checker or a teacher.
- AI output is validated with pydantic, must not claim certainty ("confirmed", "diagnosed", ...), and any `a/b + c/d = e/f` statement in it is re-checked with exact fractions. On any failure ELEVIA falls back to the template and records why.
- The API key is read from the environment only and never appears in errors or logs.
- Teacher endpoints need the PIN header. Student names should be first names or nicknames.

**Database tables:** students, cases, assessments, responses, gaps, plans, lessons, skill_mastery, agent_runs, teacher_overrides.

**Folder layout**
```
elevia/
  backend/  main.py  orchestrator.py  fractions_engine.py  content.py  llm.py  db.py  config.py
            agents/  diagnoser.py  checker.py  planner.py  tutor.py
  data/     skill_map.json  questions.json  lessons.json
  frontend/ app.py  api.py  style.css
  scripts/  build_question_bank.py   (regenerates data/questions.json)
  tests/    test_fractions.py  test_agents.py  test_workflow_api.py
  seed.py  requirements.txt  .env.example  .streamlit/config.toml
```

---

## 5. Deployment (free tiers)

**Option A: backend and frontend separately (matches the proposed stack)**
1. Push the `elevia` folder to a GitHub repo (`.env` and `*.db` are git-ignored).
2. **Backend on Render** (New → Web Service → your repo):
   - Build: `pip install -r requirements.txt && python seed.py`
   - Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Environment: `TEACHER_PIN`, `LLM_PROVIDER`, `LLM_API_KEY`, and `ALLOW_EARLY_RETEST=true` for demos.
3. **Frontend on Streamlit Community Cloud** (New app → repo → main file `frontend/app.py`).
   Secrets: `ELEVIA_API_URL = "https://<your-render-app>.onrender.com"`

**Option B: a single Streamlit Community Cloud app (easiest).** The FastAPI backend runs inside the Streamlit process, and requests still go through the FastAPI routes.
- Main file: `frontend/app.py`. Advanced settings → Python version **3.13** (or 3.12).
- Secrets:
  ```toml
  ELEVIA_EMBEDDED = "1"
  ELEVIA_AUTO_SEED = "1"
  TEACHER_PIN = "pick-a-pin"
  ALLOW_EARLY_RETEST = "true"
  # optional AI model:
  # LLM_PROVIDER = "anthropic"
  # LLM_API_KEY = "..."
  ```
- `ELEVIA_AUTO_SEED` re-creates the sample students whenever the database starts empty.

⚠️ Free tiers have **temporary disks**: the SQLite file resets when the service restarts or redeploys, and Render's free tier sleeps after inactivity (first request is slow). That's fine for a demo. For real use, attach a persistent disk or move to a hosted database.

---

## Current test results and limitations

See [docs/TEST_RESULTS.md](docs/TEST_RESULTS.md) and [docs/LIMITATIONS_AND_ROADMAP.md](docs/LIMITATIONS_AND_ROADMAP.md). They cover the whole product (website, all subjects), not only this older Streamlit version.
