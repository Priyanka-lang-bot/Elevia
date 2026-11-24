# ELEVIA: PRASUNEX Innovathon 2026, Round 3 submission

**Verify before you teach.**

ELEVIA is a working web prototype that finds the misconception behind a student's wrong answers. Before teaching anything, it **checks that misconception with new questions**. Then it teaches the missing step, starting from the earliest prerequisite that's actually missing, and a day later retests on questions the student hasn't seen. Four rule-based roles (Diagnoser, Checker, Planner, Tutor) work through each case, and a teacher decides the cases ELEVIA isn't sure about. It covers 26 playable topics in 5 subjects, with real accounts for students, parents, teachers and school admins. A fictional Class 9 with six months of history shows what the product looks like in use.

| | |
|---|---|
| **Live prototype** | https://frontend-pmvi.vercel.app (checked on 24 Nov 2026: opens without a login, demo ready) |
| **GitHub repository** | https://github.com/Priyanka-lang-bot/Elevia |
| **Demonstration video** | https://github.com/Priyanka-lang-bot/Elevia/blob/main/docs/round3-submission/video/elevia-demo.mp4 (6 min 57 s, silent with on-screen captions; see the note below) · 3-minute version: https://github.com/Priyanka-lang-bot/Elevia/blob/main/docs/round3-submission/video/elevia-demo-3min.mp4 (2 min 48 s) |
| **Team / contact** | As given in the PRASUNEX submission form |

> The teacher demo opens with an access code that the team gives judges privately; it is not in this repository.
>
> **About the video:** it was recorded on 24 Nov 2026 by driving the real application in a browser (`scripts/record_demo.py`), from a local run of the same code that serves the live site, with the same six-month demo data. It has captions instead of a voice-over, and nothing in it is mocked up.

## Problem

A mark tells a teacher *that* a student is wrong, not *why*. Students often follow a rule that looks right to them (1/2 + 1/3 = 2/5 means "add tops, add bottoms"), and the real gap is often an earlier skill. Re-teaching the chapter, or guessing from one mistake, either misses the gap or wastes time on what the student already knows. A teacher with 40 students can't diagnose each one.

## Solution

1. **Check-in.** 5 questions; the Diagnoser matches wrong answers to 86 named misconceptions and proposes a *suspected* gap.
2. **Double-check.** The Checker asks 2 new questions. The gap is **confirmed**, **rejected** (probably a slip) or **inconclusive** (sent to a teacher).
3. **Learn.** For confirmed gaps only, the Planner picks the starting skill from a 58-skill map. The Tutor's lesson quotes the student's own answer and adds worked examples and practice.
4. **Retest.** 24 hours later, 3 unseen questions. Two right marks the skill mastered; otherwise, a new plan.

## Core features

- **Learning workflow:** the four-role workflow with every decision logged and explained (verified by tests and browser runs).
- **Content:** 5 subjects (Maths 11 topics, Science 3, English 4, Social Science 2, Computer Science 6) and 1,019 validated questions; maths answers computed exactly; student code never executed.
- **Student dashboard:** next step, six-month timeline, progress by subject, skill map and full learning history.
- **Teacher portal:** class overview and insights, review queue with evidence, decisions with required reasons, intervention history.
- **Privacy:** parent consent, class codes with teacher approval, scoped sharing, access log.
- **Demo:** one-click student demo; teacher demo with a judges' access code; a resettable six-month Class 9 dataset.

## Target users

Students (Grades 3–12 and adult learners), teachers, parents and school admins.

## Technology stack

Python 3.13 · FastAPI · Pydantic · SQLite (local) / Turso (hosted SQLite) · vanilla JavaScript, HTML and CSS · Vercel (serverless + CDN) · pytest · Playwright.

## Documents in this package

| Document | Contents |
|---|---|
| [ROUND3_TECHNICAL_DOCUMENTATION.md](ROUND3_TECHNICAL_DOCUMENTATION.md) | Architecture, database, the four roles, workflow, security, testing, deployment |
| [ROUND3_FEATURE_MATRIX.md](ROUND3_FEATURE_MATRIX.md) | Every feature with its verified status, evidence and limitations |
| [ROUND3_DEMO_SCRIPT.md](ROUND3_DEMO_SCRIPT.md) | The demonstration video script, scene by scene, plus a recording checklist |
| [JUDGES_QUICK_START.md](JUDGES_QUICK_START.md) | Exploring ELEVIA in 3–5 minutes |
| [ROUND3_FUTURE_ROADMAP.md](ROUND3_FUTURE_ROADMAP.md) | Short-, medium- and long-term plans |
| [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) | Each official requirement mapped to its deliverable and evidence |
| [../TEST_RESULTS.md](../TEST_RESULTS.md) | Test results in detail |

## Testing (run 24 Nov 2026)

205 automated tests passed on SQLite and 205 on the Turso connector · 26 of 26 browser checks passed with no console errors · build-time validation of all 1,019 questions · the live site checked by hand: the demo, Riya's history, Dev's full journey including a failed retest, permissions, and the landing page on desktop and phone.

## Limitations (summary)

- **Not yet tested in classrooms**, so no learning-outcome claims.
- **Rules, not AI:** the roles are deterministic rules, not autonomous AI agents. The optional AI wording is off and untested with a real model.
- **Partial syllabus:** 26 topics; other Class 9 chapters are "coming soon".
- **Answer formats:** no essay marking; Computer Science is predict-the-output only.
- **Synthetic demo data:** the six-month history is synthetic and labelled as such.
- **Hosting:** free-tier hosting; not load-tested for many simultaneous users. The demo accounts are shared by everyone using the demo.

Full list: [ROUND3_FEATURE_MATRIX.md](ROUND3_FEATURE_MATRIX.md) and section 19 of the technical documentation.

## Future roadmap (summary)

A classroom pilot with baseline measures; the coming-soon topics; retest reminders; a validated mastery model; Hindi and Marathi; institutional onboarding with verifiable parental consent. See [ROUND3_FUTURE_ROADMAP.md](ROUND3_FUTURE_ROADMAP.md).

## AI-assisted development

ELEVIA was built with substantial help from an AI coding assistant, Anthropic's Claude (via Claude Code), working under the team's direction.

- **Written with the assistant:** most of the application code (backend, the four roles, accounts and privacy, front end), the curriculum generation scripts and question banks, the automated and browser tests, the six-month demo generator, the deployment configuration and these documents. In the final round it also merged the pull requests, deployed production and ran the live checks described in the technical documentation.
- **The team's part:** as described by the team in the PRASUNEX submission form.
- **Traceability:** commits the assistant contributed to carry a `Co-Authored-By: Claude` trailer, and the Git history has not been rewritten.
