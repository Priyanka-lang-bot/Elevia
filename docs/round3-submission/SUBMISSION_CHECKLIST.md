# ELEVIA: Round 3 submission checklist

Deadline: **25 November 2026, 11:00 PM IST**. Status as of 24 Nov 2026.

✅ done and verified · ⚠️ done, needs a team action · ❌ not done yet

## Official requirements

| # | Requirement | Deliverable | Evidence | Status |
|---|---|---|---|---|
| 1 | Working prototype | **https://frontend-pmvi.vercel.app** (production, built from `main`) | Checked on the live site 24 Nov: opens without a login; demo ready; Riya's six-month history; Dev's full journey including a failed retest; permissions; landing page on desktop and phone. 205/205 tests on SQLite and the Turso connector; 26/26 browser checks | ✅ (teacher code set by the team; teacher card live and wrong codes refused) |
| 2 | Live demo or demonstration video | Live demo above; video https://github.com/Priyanka-lang-bot/Elevia/blob/main/docs/round3-submission/video/elevia-demo.mp4 (6 min 57 s, silent with captions); `ROUND3_DEMO_SCRIPT.md` | The video drives the real app (local run of the same code and demo data); frames checked; no console errors during recording | ✅ live demo · ✅ video (captions, no voice-over) |
| 3 | Source code / repository link | https://github.com/Priyanka-lang-bot/Elevia | PRs #3, #2 and #1 merged into `main` on 24 Nov (merge commits; history kept; the old `main` is also on branch `backup-before-round3`) | ✅ |
| 4 | Brief technical documentation | `ROUND3_TECHNICAL_DOCUMENTATION.md`, `JUDGES_QUICK_START.md` | 20 sections, architecture/ER/workflow diagrams, live verification table (section 18) | ✅ |
| 5 | Features and limitations | `ROUND3_FEATURE_MATRIX.md`; section 19 of the technical documentation | Each feature has an evidence path or test name; unverified items are marked as such | ✅ |
| 6 | Future development plans | `ROUND3_FUTURE_ROADMAP.md` | All items labelled as future plans | ✅ |

## Evaluation criteria

| Criterion | Where judges will see it |
|---|---|
| Functionality | Quick start steps 2–4 on the live site; feature matrix |
| Technical execution | Technical documentation (architecture, four roles, Checker rule, security, 205 tests, live checks) |
| User experience | Landing page (scroll-driven sections), student dashboard, teacher portal; demo scenes 2–7 |
| Innovation | "Verify before you teach": the Checker step and the audit log (demo scenes 4 and 8) |
| Practical applicability / scalability | Teacher workflow, privacy and consent, hosted database, roadmap |
| Demonstration quality | Demo script and recording checklist |

## Remaining actions (team)

| # | Action | By |
|---|---|---|
| 1 | Open https://frontend-pmvi.vercel.app → Try demo → type your access code on Ananya Mehta's card → check the teacher view opens (Claude didn't use the code) | 24 Nov |
| 2 | Watch the video once. Optional: record a narrated version on the live site with `ROUND3_DEMO_SCRIPT.md`, or upload the MP4 to YouTube (unlisted) or Drive if the portal wants a streaming link | 25 Nov |
| 3 | Fill in team/contact details and the team's part of the AI-assistance note (`ROUND3_SUBMISSION_README.md` and section 20 of the technical documentation) | 25 Nov |
| 4 | Give judges the teacher access code privately (e.g. the portal's private notes field; never in the repository or the video) | 25 Nov |
| 5 | Redeploy production just before judging, for a fresh demo (Vercel → Deployments → latest production deployment → ⋯ → Redeploy) | 25 Nov |
| 6 | Submit on the competition portal | Before 25 Nov, 11:00 PM IST |

## Placeholders to fill in

- `[TO FILL IN]` team/contact: `ROUND3_SUBMISSION_README.md`
- `[TO FILL IN by the team: …]` the team's part: `ROUND3_SUBMISSION_README.md` and `ROUND3_TECHNICAL_DOCUMENTATION.md`

## Notes

- **Vercel project `frontend`** (separate from `frontend-pmvi`): it builds the old `frontend/` folder, has failed on every commit (23 failures, none ever live) and isn't used by the live site. It's safe to disconnect it from the repository in Vercel when convenient; it was left untouched.
- **Demo resets** touch only records listed in `demo_registry` and are applied in one transaction during production builds (`ELEVIA_DEMO_RESET_ON_DEPLOY=1`). To stop resets on deploy, delete that variable.
