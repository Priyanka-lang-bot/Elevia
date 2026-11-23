# ELEVIA: Round 3 submission

**Theme:** Closing learning gaps with agentic AI in personalised education
**Tagline:** Verify before you teach.

> **Final submission package:** [docs/round3-submission/](round3-submission/ROUND3_SUBMISSION_README.md): technical documentation, feature matrix, demo script, judges' quick start, roadmap and submission checklist.

| | |
|---|---|
| GitHub | https://github.com/Priyanka-lang-bot/Elevia (branch `round3`; pull request #1 into `main`) |
| Live preview | https://frontend-pmvi-git-six-month-demo-priyankawanjari52-8602.vercel.app (see "Live link status" below) |
| Demo guide | [docs/DEMO_SCRIPT.md](DEMO_SCRIPT.md), 5–7 minutes |

---

## 1. Problem

A wrong answer tells a teacher *that* a student is stuck, not *why*. Take a student who writes 1/2 + 1/3 = 2/5. They aren't careless: they believe fractions add top-to-top and bottom-to-bottom.

Most practice apps react by marking the answer wrong and serving more of the same questions, or by guessing at a weakness from one mistake. In one case the real misconception is never found. In the other, students are taught things they already know.

Teachers with 40 students can't run a diagnostic conversation with each one, and parents rarely see more than a score.

## 2. Solution

ELEVIA treats every suspected misconception as a **hypothesis to be checked before any teaching happens**:

1. **Check-in.** Five questions. The Diagnoser matches wrong answers against named misconception patterns and proposes a *suspected* gap. A single mistake is treated as a possible slip.
2. **Double-check.** The Checker asks **two new questions** designed to expose the same misconception. The gap is then confirmed, rejected ("probably a slip"), or inconclusive (sent to the teacher).
3. **Learn.** Only for a *confirmed* gap, the Planner walks the skill map's prerequisites and picks the focus. The Tutor gives a lesson that quotes the student's own wrong answer, plus worked examples, hints and practice.
4. **Retest.** After a delay (24 h by default), three **unseen** questions. Two of three marks the skill mastered. Otherwise the gap stays open and ELEVIA re-plans.

Teachers resolve unclear cases and can redirect the focus, always with a logged reason.

## 3. Users

| User | What they get |
|---|---|
| Student (school, individual with parent consent, or independent learner 18+) | A "What to do next" card, topic journeys across five subjects, a six-month timeline, progress by subject, a skill map, retests and a full learning history |
| Teacher | Students in their own classes only: a class overview and class insights, a review queue with reasons, each student's six-month record and evidence, confirm/reject/redirect with a reason, and an intervention history |
| Parent | A plain-language summary of their own child, limited to what the consent allows |
| School admin | Classes, teacher invitations and enrolments, but not learning data |

## 4. Platform overview

- **Landing page:** a notebook-style story: a marked-up worksheet for the problem, a stack of books for the four roles, a drawer of folders for what's built, a curriculum index, real screenshots, and **Try demo** in the navigation.
- **Accounts:** three sign-up pathways, parent consent, class codes with teacher approval, email verification, password reset, and sharing grants with scopes.
- **Student dashboard** (`#/learn`) and **topic journeys** (`#/learn/<topic>`) with a step tracker.
- **Teacher portal** and **parent view** (home pages for those roles).
- **Demo mode:** a fictional Class 9 A at "ELEVIA Demonstration School" (2026-27).
  - **The history:** six months of records produced by running the real workflow on simulated answers and a simulated calendar.
  - **Riya Sharma** (DEMO-09-001): five subjects, 16 check-ins, 8 skills mastered, retests failed then passed, teacher decisions.
  - **The class:** four classmates with different patterns, and teacher Ananya Mehta.
  - **Access:** students open with one click from **Try demo**; the teacher view needs the judges' access code.
  - **Reset:** a command-line reset recreates the same history and deletes only demo rows.

## 5. Key features

- **Verification before teaching.** The Planner refuses to act on an unverified gap, and this is enforced in code and tests.
- **Fresh questions at every stage.** Students never see a check-in question again in the double-check or retest.
- **Exact checking.** Maths uses exact fraction arithmetic. Each misconception's wrong answer is *computed*, so the answer key can't contain typos. CS answers are verified by running each snippet at build time, and **student input is compared as text and never executed**.
- **Explainable decisions.** Every stage says why, in plain language: "Possible gap: not confirmed yet", "Double-check was mixed…".
- **Teacher in the loop.** A review queue, a reason required for every override, and a visible intervention history.
- **Privacy by role.** Teachers see only their own classes, and parents see only consented scopes. Every view is written to an access log.
- **Persistence.** Progress is saved per answer and resumes after a reload or a new login.

## 6. Architecture

One FastAPI app runs as a single Vercel serverless function. The frontend is a static vanilla-JS site in `public/`. The database is SQLite locally and Turso (hosted SQLite) in production.

```
Browser (public/) ──cookie session──▶ /api/* FastAPI (app.py)
   accounts · learning · progress · demo routers
        └─ orchestrator ─▶ Diagnoser · Checker · Planner · Tutor (rule-based)
        └─ engine ─▶ fractions_engine (exact) · generic_engine (mcq / numeric / text / code output)
        └─ curriculum: data/curriculum.json + data/topics/*.json (built from scripts/curriculum/*.py)
        └─ db: SQLite / Turso
```

Details are in [ARCHITECTURE.md](ARCHITECTURE.md).

**About "agentic".** The four roles are deterministic, rule-based components coordinated by an orchestrator, each with one clear responsibility and hand-offs between them. They are **not autonomous LLM agents**, and no AI model makes any decision. We chose this deliberately so every decision is repeatable and auditable. An optional module can reword explanations with an LLM, with validation and fallback, but it is off by default and has only been tested against simulated responses.

## 7. Workflow

```
check-in ─▶ Diagnoser ─▶ suspected gap? ─no─▶ "no gap found"
                              │ yes
                              ▼
                   Checker: 2 new questions
          rejected ◀──────────┼──────────▶ inconclusive ─▶ teacher review
                              ▼ confirmed
                Planner (prerequisites) ─▶ Tutor (lesson, practice)
                              ▼
                 delayed retest: 3 new questions
          ≥2/3 ─▶ mastered          <2/3 ─▶ gap stays open ─▶ re-plan
```

## 8. Multi-subject coverage

All 26 topics have objectives, two diagnostic sets, misconception patterns, double-check questions, lessons, practice, retests and skill-map updates. Each one is tested end to end, including a rejected-gap path.

| Subject | Playable topics |
|---|---|
| Mathematics (11) | Fractions, Decimals, Percentages, Integers, Linear equations, Order of operations, Factors and multiples, Ratio and proportion, Perimeter and area, Averages, Angles |
| Science (3) | Forces and motion, States of matter, Scientific reasoning (fair tests) |
| English (4) | Past tense verbs, Subject–verb agreement, Parts of speech, Apostrophes |
| Social Science (2) | Latitude and longitude, Time zones and Indian Standard Time |
| Computer Science (6) | Variables and assignment, Loops, Data types, Conditionals, Logical reasoning, Algorithms |

**Content totals:** 1,019 questions, 58 skills, 86 named misconception patterns, 55 lessons.

**Coming soon** (shown as such, not playable):
- **Maths:** probability, area of triangles and circles, volume, graphs.
- **Science:** heat and temperature, light, electric circuits, plants and photosynthesis.
- **English:** reading comprehension, sentence construction, other tenses, vocabulary.
- **Social Science:** physical features of India, drainage, climate, what is democracy?, the French Revolution, poverty as a challenge.
- **CS:** functions, lists, sorting.

## 9. Screenshots

These are captured from the running app by `scripts/e2e_browser.py --shots`, using demo data:

| File | Shows |
|---|---|
| `public/img/shot-verify.jpg` | Double-check: suspected gap, "not confirmed yet" |
| `public/img/shot-lesson.jpg` | Lesson quoting the student's own wrong answer |
| `public/img/shot-result.jpg` | Retest passed, gap closed |
| `public/img/shot-dash.jpg` | Student dashboard with "What to do next" (Riya) |
| `public/img/shot-teacher.jpg` | Teacher review queue and class overview |

## 10. Testing evidence

All results come from runs actually executed. Details are in [TEST_RESULTS.md](TEST_RESULTS.md).

- **Automated tests:** 202 passed on local SQLite and 202 passed through the Turso connector fake. They cover:
  - the full and rejected-gap journeys for every topic, including both Social Science topics;
  - the Diagnoser, Checker, Planner and Tutor rules;
  - accounts and consent, and role access (teacher, parent, admin, stranger);
  - demo login, the teacher access code, reset (real users survive it) and determinism;
  - **data consistency:** every dashboard figure is backed by records. Mastered skills ↔ passed retests, confirmed gaps ↔ the Checker's verdict or a logged teacher decision, lessons ↔ stored lessons, monthly figures ↔ totals ↔ the database.
- **Browser end-to-end:** 26 of 26 checks passed with 0 console errors. The run covers:
  - the landing page, including the scroll interactions, at desktop, tablet and phone sizes, without JavaScript and with reduced motion;
  - a full topic live (Dev);
  - Riya's six-month timeline, whose monthly table adds up to the dashboard totals;
  - all five subjects, the skill map and the subject filter;
  - the teacher demo with the access code: class overview, insights, Riya's flagged case with its evidence, a confirmed review saved to the history;
  - the parent's restricted view.
- **Build-time content validation:** every question validated, every maths answer computed, and every CS answer executed.

## 11. Live link status

- **Build:** the preview builds successfully on the Vercel project `frontend-pmvi`.
- **What I checked in a browser on 23 Nov 2026:** the landing page, `/api/health` and the catalogue (5 subjects, 26 topics, 1,019 questions) all work on the preview.
- **Database:** the project now has Turso configured for Production, Preview and Development, so data persists.
- **What is still needed before judging:**
  - Seed the six-month demo into that database from a laptop with the Turso credentials: `python scripts/demo.py reset`.
  - Add `ELEVIA_DEMO_MODE=1` and `ELEVIA_DEMO_TEACHER_CODE` (a private code, 8+ characters) to the Vercel project.
  - Merge to `main` and share the production domain. Preview links can ask visitors to log in to Vercel.

## 12. Limitations and roadmap

These are summarised from [LIMITATIONS_AND_ROADMAP.md](LIMITATIONS_AND_ROADMAP.md).

**Limitations:**
- **No classroom evaluation yet**, so **we make no claims about learning outcomes.**
- Rule-based roles; mastery is a simple 2-of-3 rule rather than a probabilistic model.
- Fixed question banks, which run out after repeated failed retests on one skill. When that happens the case goes to the teacher.
- No free-text or essay marking. CS is predict-the-output only.
- Reading comprehension and electricity are not built yet.
- No reminders or notifications. Parent consent is verified by email ownership plus a declaration.

**Roadmap:**
1. A classroom pilot with 1–2 teachers, measured against a baseline.
2. The "coming soon" topics.
3. Parameterised question banks for every topic.
4. Teacher authoring of questions and misconceptions.
5. Probabilistic mastery once real data exists.
6. Retest reminders and parent emails.
7. Verifiable parental consent (DPDP Rule 10).
8. Hindi and Marathi interface text.

## 13. AI-assisted development disclosure

This project was built with substantial help from an AI coding assistant (Anthropic's Claude, via Claude Code). It wrote much of the code, curriculum authoring scripts, tests and documentation, working under our direction and review.

Commits it contributed to carry a `Co-Authored-By: Claude` trailer (most commits on `round3`; run `git log --grep "Co-Authored-By: Claude"` to list them). The git history has not been rewritten. The product itself makes no AI API calls in its decision-making.
