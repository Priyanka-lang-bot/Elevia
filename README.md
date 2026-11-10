# ELEVIA: Closing Learning Gaps with Agentic AI

ELEVIA is a personalised maths learning MVP. Four agents work through one shared student record:

| Agent | Job | How it decides |
|---|---|---|
| **Diagnoser** | Looks at wrong answers, suggests the *possible* underlying gap and a confidence level | Exact-arithmetic mistake patterns (e.g. `1/2 + 1/3 = 2/5` → "adds numerators and denominators"). Optional AI model rewrites the explanation only. Output is always **suspected**. |
| **Checker** | Picks new verification questions, decides confirmed / rejected / inconclusive, updates mastery, schedules and marks the later retest | Rule-based and auditable. The only agent allowed to change mastery. |
| **Planner** | Turns a **verified** gap into a learning path using the skill map | Walks prerequisites in `data/skill_map.json`. **Refuses to run on an unverified gap.** |
| **Tutor** | Small-step lesson, worked examples, hints and practice | Lesson content plus exactly computed worked examples. Optional AI model personalises wording; its maths is re-checked. **Does not grade its own teaching.** |

Teachers can confirm or reject gaps and change the learning focus. Every override is logged with a name and a reason.

> ELEVIA identifies possible academic knowledge gaps from a student's answers. It is not a clinical or psychological assessment and does not diagnose learning difficulties.

---

## Accounts and access (in progress)

The backend now has real accounts for five roles, built to the architecture document: individual students (locked until a parent verifies and consents), school students (referral code + teacher approval), independent learners (email verification + optional, revocable sharing), parents, teachers and school admins. Passwords are hashed with scrypt; sessions, consent records with timestamps, referral codes, sharing grants and an access log are stored in SQLite. Every route checks role **and** relationship before showing anyone's data. The website in `public/` covers all three pathways, parent consent, and simple home screens for each role.

- Add a subscribed school and get its admin's invitation link:
  `python scripts/create_school.py --name "Sunrise Public School" --admin-email head@school.in --state Maharashtra --district Pune`
- Emails: with `EMAIL_MODE=outbox` (default) nothing is sent; emails are saved in the database. Locally, set `ELEVIA_DEV_OUTBOX=1` and open http://localhost:8000/dev/outbox to see them and their links. Set `EMAIL_MODE=smtp` and the `SMTP_*` values to really send.
- Parent verification is currently email ownership + a declaration. That is **not** DPDP Rule 10-grade verification; see the architecture document.

## Run the website locally (Windows)

The website (in `public/`) and the API (`backend/`, served at `/api`) run together:

```powershell
cd C:\Users\DELL\Desktop\Prausnex\elevia
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install --only-binary=:all: -r requirements.txt
copy .env.example .env
python -m uvicorn app:app --reload
```
Open **http://localhost:8000**. (The website needs only FastAPI, so it avoids the pandas/pyarrow files your laptop's security policy blocks.)

To test without an email service, set `ELEVIA_DEMO_EMAIL_LINKS=1` in `.env`: the links ELEVIA would email appear in a yellow "Demo mode" box on screen. **Demo only** — with it on, anyone could approve their own consent.

Add a subscribed school (prints the admin's invitation link):
```powershell
python scripts/create_school.py --name "Sunrise Public School" --admin-email head@school.in --state Maharashtra --district Pune
```

Run the tests: `python -m pip install -r requirements-dev.txt` then `python -m pytest -q` (add `set ELEVIA_TEST_TURSO=1` first to run them through the Turso connector).

## Deploy on Vercel (with a Turso database)

Vercel runs `app.py` as one serverless function and serves `public/` from its CDN. Vercel's disk is temporary, so data lives in **Turso** (hosted SQLite).

**1. Create the database (Turso, free tier)**
1. Sign up at https://turso.tech (Continue with GitHub).
2. Create a database; pick the region closest to your users (e.g. Mumbai).
3. Copy its **URL** (`libsql://<name>-<org>.turso.io`) and create a **token** with read-write access.

**2. Create the Vercel project**
1. Sign in at https://vercel.com with GitHub → **Add New… → Project** → import `Priyanka-lang-bot/Elevia`.
2. Framework preset: **FastAPI** (detected automatically). Leave build settings empty.
3. **Environment Variables**:
   | Name | Value |
   |---|---|
   | `TURSO_DATABASE_URL` | your `libsql://…` URL |
   | `TURSO_AUTH_TOKEN` | your token |
   | `ELEVIA_DEMO_EMAIL_LINKS` | `1` for a judges' demo without email (remove for real use) |
   | `EMAIL_MODE`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` | only when you set up real email |
4. **Deploy**. Then Project → Settings → Functions → set the region near your Turso database (e.g. Mumbai, `bom1`).

**3. Add a school to the live site** (from your laptop, pointed at Turso): put `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` and `APP_BASE_URL=https://<your-project>.vercel.app` in `.env`, then run the `create_school.py` command above. Open the printed link to set up the school admin.

Notes: the older fractions learning screens (Streamlit, in `frontend/`) are not part of the Vercel site yet; their unauthenticated API routes are switched off on Vercel and will return with proper accounts in the learning phase. Sessions use HttpOnly cookies; security headers are set in `vercel.json`.

## Older Streamlit version (fractions learning engine)

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

## 6. Implemented and tested

- 51 automated tests passing (`python -m pytest -q`), covering: correct, equivalent, incorrect and invalid fraction answers; all 8 mistake patterns; diagnosis and confidence; verification question selection; confirmed / rejected / inconclusive verdicts; the Planner refusing unverified gaps; prerequisite-first planning; Tutor lessons; retest pass and fail (fail re-plans); mastery only via retest; SQLite persistence; teacher PIN, confirm, reject and change-focus; override blocked mid-verification; input validation; early-retest lock; missing AI configuration; AI output that is invalid JSON, an HTTP error, wrong maths, or claims certainty (all fall back, and the key is never leaked).
- Full click-through of the website in a real browser (Chrome, desktop and 390 px mobile): demo flow, input validation messages, wrong teacher PIN, teacher confirm. No console errors.

## 7. Known limitations and not yet built

- **AI model path was tested only against simulated API responses**: no real provider call was made during development. Test once with your key before the demo; any failure falls back to templates automatically and is shown in the agent log.
- The Diagnoser's gap choice and confidence are rule-based heuristics over 8 known mistake patterns. The confidence formula is reasoned, not statistically calibrated.
- Fractions only: 8 skills, 65 questions, lessons for 5 skills (equivalent, simplifying, comparing, common denominators, multiplying). Gaps in skills without a lesson go to the teacher.
- Verification and retest pools are small. A second failed retest can run out of new questions, which sends the case to teacher review.
- Students have no login (sample/student picker). Teachers share one PIN. This is fine for a demo, not for real student data.
- The retest delay uses server time. There are no reminders or notifications.
- Hint usage is recorded but not yet used in decisions.
- Free hosting doesn't keep the database (see Deployment).
