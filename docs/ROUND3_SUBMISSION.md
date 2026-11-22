# ELEVIA: Round 3 submission

**Theme:** Closing learning gaps with agentic AI in personalised education
**Tagline:** Verify before you teach.

| | |
|---|---|
| GitHub | https://github.com/Priyanka-lang-bot/Elevia (branch `round3`; pull request #1 into `main`) |
| Live preview | https://frontend-pmvi-git-round3-priyankawanjari52-8602.vercel.app (see "Live link status" below) |
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
| Student (school, individual with parent consent, or independent learner 18+) | A "What to do next" card, topic journeys across four subjects, a skill map, retests and history |
| Teacher | Students in their own classes only, a review queue with reasons, per-student evidence, confirm/reject/redirect with a reason, and an intervention history |
| Parent | A plain-language summary of their own child, limited to what the consent allows |
| School admin | Classes, teacher invitations and enrolments, but not learning data |

## 4. Platform overview

- **Landing page:** what the problem is, how ELEVIA works, a live subject catalogue, real screenshots, and one-click demo cards.
- **Accounts:** three sign-up pathways, parent consent, class codes with teacher approval, email verification, password reset, and sharing grants with scopes.
- **Student dashboard** (`#/learn`) and **topic journeys** (`#/learn/<topic>`) with a step tracker.
- **Teacher portal** and **parent view** (home pages for those roles).
- **Demo mode:** six fictional accounts in "Sunrise Demo School", opened with one click. A safe reset deletes only demo rows.

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

All 24 topics have objectives, two diagnostic sets, misconception patterns, double-check questions, lessons, practice, retests and skill-map updates. Each one is tested end to end, including a rejected-gap path.

| Subject | Playable topics |
|---|---|
| Mathematics (11) | Fractions, Decimals, Percentages, Integers, Linear equations, Order of operations, Factors and multiples, Ratio and proportion, Perimeter and area, Averages, Angles |
| Science (3) | Forces and motion, States of matter, Scientific reasoning (fair tests) |
| English (4) | Past tense verbs, Subject–verb agreement, Parts of speech, Apostrophes |
| Computer Science (6) | Variables and assignment, Loops, Data types, Conditionals, Logical reasoning, Algorithms |

**Content totals:** 943 questions, 54 skills, 82 named misconception patterns, 51 lessons.

**Coming soon** (shown as such, not playable):
- **Maths:** probability, area of triangles and circles, volume, graphs.
- **Science:** heat and temperature, light, electric circuits, plants and photosynthesis.
- **English:** reading comprehension, sentence construction, other tenses, vocabulary.
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

- **Automated tests:** 185 passed on local SQLite and 185 passed through the Turso connector fake. They cover:
  - the full and rejected-gap journeys for every topic;
  - the Diagnoser, Checker, Planner and Tutor rules;
  - accounts and consent, and role access (teacher, parent, admin, stranger);
  - demo login and reset (including that real users survive a reset);
  - persistence and error handling.
- **Browser end-to-end:** 17 of 17 checks passed with 0 console errors. The run covers:
  - the landing page;
  - one-click login and a full fractions journey;
  - a code question and reload persistence;
  - a phone-sized dashboard;
  - teacher review with a reason;
  - the parent's restricted view.
- **Build-time content validation:** every question validated, every maths answer computed, and every CS answer executed.

## 11. Live link status

- **Build:** the `round3` branch builds successfully on the Vercel project `frontend-pmvi`.
- **What I checked in a browser on 22 Nov 2026:** the landing page, login page, `/api/health` and the subject catalogue (24 topics) all work on the preview link above.
- **What I fixed:** the API had been crashing on all deployments, including `main`, because no database was configured. That is fixed on `round3`.
- **What is still needed before judging:**
  - Add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` to the Vercel project, so data persists. Until then the site uses a temporary per-instance database.
  - Add `ELEVIA_DEMO_MODE=1`, then run `python scripts/demo.py seed` against that database, so the one-click demo cards appear.
  - Make sure the link judges receive is publicly viewable. Vercel can require a Vercel login for preview links, so either merge to `main` and share the production domain, or turn off preview protection.

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

Commits it contributed to carry a `Co-Authored-By: Claude` trailer (19 of the 25 commits on `round3` at the time of writing). The git history has not been rewritten. The product itself makes no AI API calls in its decision-making.
