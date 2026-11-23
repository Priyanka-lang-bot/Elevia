# ELEVIA: Round 3 submission checklist

Deadline: **25 November 2026, 11:00 PM IST**. Status as of 23 Nov 2026.

✅ done and verified · ⚠️ done, needs a team action · ❌ not done yet

## Official requirements

| # | Requirement | Deliverable | Evidence | Status |
|---|---|---|---|---|
| 1 | Working prototype | The ELEVIA web app (branch `six-month-demo`, PRs #1–#3) | 202/202 tests on SQLite and Turso; 26/26 browser checks; manual run of every demo-script scene (23 Nov) | ✅ runs locally · ⚠️ not yet live (see blockers) |
| 2 | Live demo or demonstration video | `ROUND3_DEMO_SCRIPT.md` (about 6 min 50 s, with recording checklist) | Every answer and click in the script was checked against the running app | ❌ video not recorded · ❌ live link not verified |
| 3 | Source code / repository link | https://github.com/Priyanka-lang-bot/Elevia | Branches `main`, `round3`, `landing-redesign`, `six-month-demo`; PRs #1–#3 open | ✅ (merge pending, see blockers) |
| 4 | Brief technical documentation | `ROUND3_TECHNICAL_DOCUMENTATION.md`, `JUDGES_QUICK_START.md` | 20 sections, architecture/ER/workflow diagrams; figures taken from code and test runs | ✅ |
| 5 | Features and limitations | `ROUND3_FEATURE_MATRIX.md`; section 19 of the technical documentation | Each feature has an evidence path or test name; unverified items are marked as such | ✅ |
| 6 | Future development plans | `ROUND3_FUTURE_ROADMAP.md` | All items labelled as future plans | ✅ |

## Evaluation criteria

| Criterion | Where judges will see it |
|---|---|
| Functionality | Quick start steps 2–4; feature matrix |
| Technical execution | Technical documentation (architecture, four roles, Checker rule, security, 202 tests) |
| User experience | Demo scenes 2–7; landing page, student dashboard, teacher portal |
| Innovation | "Verify before you teach": the Checker step and the audit log (demo scenes 4 and 8) |
| Practical applicability / scalability | Teacher workflow, privacy and consent, Turso deployment, roadmap |
| Demonstration quality | Demo script and recording checklist |

## Blockers (must be fixed before the live link is submitted)

1. **Production is broken.** `https://frontend-pmvi.vercel.app` serves the 10 Nov build of `main`; its API returns HTTP 500.
2. **Preview links are private.** Vercel Authentication protects preview deployments, so judges can't open them.
3. **Demo mode is off on Vercel.** `ELEVIA_DEMO_MODE` and `ELEVIA_DEMO_TEACHER_CODE` are not set, and the six-month demo hasn't been seeded into the Turso database.

## Remaining actions

| # | Action | Who | By |
|---|---|---|---|
| 1 | Approve and merge PR #3 → #2 → #1 (or merge `six-month-demo` into `main`), which redeploys production with the Round 3 code | Team | 24 Nov |
| 2 | Seed the demo into Turso: with the Turso variables and `ELEVIA_DEMO_PASSWORD` set locally, run `python scripts/demo.py reset` (touches only demo-registered records) | Team | 24 Nov |
| 3 | In Vercel → Production: set `ELEVIA_DEMO_MODE=1` and a private `ELEVIA_DEMO_TEACHER_CODE` (8+ characters); redeploy | Team | 24 Nov |
| 4 | Verify the production URL: landing page loads, *Open as Riya* works, teacher code works, no console errors. Then fill in the URL in `ROUND3_SUBMISSION_README.md` and `JUDGES_QUICK_START.md` | Team (Claude can help check) | 24 Nov |
| 5 | Record the video (production, or locally if production isn't ready), upload it, and fill in the link | Team | 25 Nov, afternoon |
| 6 | Fill in team/contact details; decide how to give judges the teacher access code | Team | 25 Nov |
| 7 | Reset the demo just before judging: `python scripts/demo.py reset` | Team | 25 Nov |
| 8 | Submit on the competition portal | Team | Before 25 Nov, 11:00 PM IST |

## Placeholders to fill in

- `[TO FILL IN after the production site is fixed and checked…]`: `ROUND3_SUBMISSION_README.md`
- `[TO FILL IN: video link]`: `ROUND3_SUBMISSION_README.md`
- `[TO FILL IN]` team/contact: `ROUND3_SUBMISSION_README.md`
- `[LIVE PROTOTYPE URL, to be filled in by the team]`: `JUDGES_QUICK_START.md`
