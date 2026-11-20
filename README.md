# ELEVIA: Verify before you teach

ELEVIA finds the misconception behind a student's wrong answers, **checks it with new questions before teaching**, teaches the missing step, and retests on fresh questions later. It covers **4 subjects and 11 topics** (Maths, Science, English, Computer Science) on one website with real accounts for students, parents, teachers and school admins.

| Role | Job | How it decides |
|---|---|---|
| **Diagnoser** | Suggests the *possible* gap behind wrong answers; a single mistake is flagged as a possible slip | Matches answers to 39 named misconception patterns. Output is always **suspected**. |
| **Checker** | Asks 2 new questions: confirmed / rejected / inconclusive; later runs the 3-question retest | Fixed rules. The only part that can mark a skill mastered (2 of 3 on a delayed retest). |
| **Planner** | Turns a **verified** gap into a learning focus | Walks prerequisites in the skill map. **Refuses unverified gaps.** |
| **Tutor** | Lesson, worked examples, hints, practice | Authored content; maths examples computed exactly. Optional AI rewording is validated, with the template as fallback. |

All four are deterministic, rule-based components coordinated by an orchestrator; they are **not autonomous LLM agents**. Teachers can resolve unclear cases and change the focus; every override is logged with a reason.

> ELEVIA identifies possible academic knowledge gaps from answers. It is not a clinical or psychological assessment. It has not been evaluated in classrooms, so it makes no claims about learning outcomes.

**Docs:** [Architecture](docs/ARCHITECTURE.md) · [Feature matrix](docs/FEATURE_MATRIX.md) · [Demo script](docs/DEMO_SCRIPT.md) · [Test results](docs/TEST_RESULTS.md) · [Limitations and roadmap](docs/LIMITATIONS_AND_ROADMAP.md)

---

## What's in the website

- **Landing page** (`/`): static, crawlable HTML in the same notebook/cut-paper style as the login page, with real screenshots and a live subject catalogue.
- **Accounts**: three pathways (individual student with parent consent, school student with a class code and teacher approval, independent learner 18+), plus parents, teachers and school admins. scrypt passwords, HttpOnly cookie sessions, CSRF protection, rate limits, access log.
- **Student dashboard** (`#/learn`): subjects and topics, continue learning, upcoming retests, gaps being worked on, mastered skills, recent activity.
- **Topic journey** (`#/learn/<topic>`): check-in → double-check → learn & practise → retest → result, with a step tracker and plain-language explanations at every step.
- **Teacher portal**: students in your own classes only, class insights (who needs review, most common verified gaps), per-student evidence, and a review form (confirm/reject, change focus, notes; reason required).
- **Parent view**: progress for children whose consent includes it; no override controls.

### Subjects and topics

| Subject | Topics (all playable end to end) | Answer checking |
|---|---|---|
| Mathematics | Fractions, Decimals, Percentages, Integers, Linear equations | Exact `Fraction` arithmetic; misconception answers computed by rule |
| Science | Forces and motion, States of matter | Multiple choice; each wrong option maps to a named misconception |
| English | Past tense verbs, Subject–verb agreement | Accepted-answer lists / multiple choice |
| Computer Science | Variables and assignment, Loops | Predict-the-output; expected output verified by running the snippet at build time (student input is never executed) |

Planned (listed in the app as "planned", not playable): Geometry, Mensuration, Statistics, Probability, plants and photosynthesis, light and sound, circuits, vocabulary, reading comprehension, writing, Boolean logic, algorithms, data structures.

## Run it locally (Windows PowerShell)

```powershell
cd C:\Users\DELL\Desktop\Prausnex\elevia
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install --only-binary=:all: -r requirements.txt pytest
copy .env.example .env
python scripts\create_demo_accounts.py --with-activity
python -m uvicorn app:app --reload
```
Open **http://localhost:8000**. Demo logins (password `Demo-Pass-2026!` for all, local use only):

| Role | Log in with |
|---|---|
| Independent learner | `demo.learner@example.com` |
| Individual student (12, parent consented) | `riya.demo` |
| School student (Class 5 A) | `arjun.demo` |
| Teacher (Class 5 A) | `demo.teacher@example.com` |
| School admin | `demo.admin@example.com` |
| Parents | `demo.parent@example.com` (Riya), `demo.parent2@example.com` (Arjun) |

`--with-activity` gives Arjun a finished decimals journey and a fractions case waiting for teacher review (scripted answers through the real workflow). To start again, delete `elevia.db` and rerun the script. With `ELEVIA_DEMO_EMAIL_LINKS=1` in `.env`, emailed links appear on screen instead (demo only).

**Tests:** `python -m pytest -q` (150 tests; `set ELEVIA_TEST_TURSO=1` first to run them through the Turso connector). Browser end-to-end: see `scripts/e2e_browser.py`.

**Curriculum:** topic content is generated by `python scripts/build_curriculum.py` from `scripts/curriculum/*.py` (validates everything and runs every code snippet). The original fractions files (`data/skill_map.json`, `questions.json`, `lessons.json`) are unchanged.

## Deploy on Vercel (with a Turso database)

Vercel runs `app.py` as one serverless function and serves `public/` from its CDN; data lives in **Turso** (hosted SQLite). Pushing to `main` deploys production; other branches get preview deployments.

1. Turso: create a database (region near your users), copy its `libsql://…` URL and a read-write token.
2. Vercel project (FastAPI preset, no build settings). Environment variables: `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`; optionally `ELEVIA_DEMO_EMAIL_LINKS=1` for a judges' demo without email; `EMAIL_MODE=smtp` + `SMTP_*` for real email; `RETEST_DELAY_HOURS`, `ALLOW_EARLY_RETEST`.
3. New tables are created automatically on first request (`CREATE TABLE IF NOT EXISTS`); existing data is kept. Round 3 only **adds** tables (`learner_links`, `case_topics`).
4. Demo accounts on the live database (from your laptop): put the Turso values and `APP_BASE_URL=https://<project>.vercel.app` in `.env`, then run `python scripts\create_demo_accounts.py --with-activity`. The password is public in this README, so remove or change these accounts after judging.

Note: do not add a `pyproject.toml` with a `[project]` table; it made Vercel's build fail (the last good build before Round 3 had none).

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
