# Feature implementation matrix

Status words: **BUILT** (code exists) · **TESTED** (automated tests and/or the browser run cover it) · **DEPLOYED** (in a successful Vercel build; see note) · **SIMULATED** (only exercised against fakes) · **PARTIAL** · **PLANNED** (not built).

Deployment note: the `round3` branch builds successfully as a Vercel **preview** on the `frontend-pmvi` project (GitHub commit status "Deployment has completed"). I could not open `*.vercel.app` from my workspace, so the live pages themselves have **not** been verified in a browser. See TEST_RESULTS.md.

| Area | Feature | Status |
|---|---|---|
| Landing | Hero, problem, how it works, features, subjects (live catalogue), student/teacher sections with real screenshots, why ELEVIA, CTA, footer | BUILT · TESTED (browser) |
| Landing | Responsive (desktop/phone), mobile menu, no horizontal overflow, smooth in-page nav, no dead links | BUILT · TESTED (browser) |
| Landing | SEO title/description, static crawlable HTML | BUILT |
| Accounts | Three sign-up pathways, parent consent, school codes + teacher approval, email verification, password reset | BUILT · TESTED (existing suite) |
| Accounts | Teachers/admins by invitation; sharing grants with scopes and expiry; access log | BUILT · TESTED |
| Security | scrypt, cookie sessions, CSRF, rate limits/lockout, CSP, self-hosted fonts | BUILT · TESTED (unit); CSP from `vercel.json` only applies on Vercel |
| Curriculum | Subject → topic → skill → misconception → questions → lessons, cross-topic prerequisites, build-time validation | BUILT · TESTED |
| Mathematics | Fractions, decimals, percentages, integers, linear equations: full journey | BUILT · TESTED (every topic end to end) |
| Science | Forces and motion, states of matter: full journey | BUILT · TESTED |
| English | Past tense verbs, subject–verb agreement: full journey | BUILT · TESTED |
| Computer Science | Variables, loops: predict-the-output, answers verified by execution at build time | BUILT · TESTED |
| Other topics | Geometry, statistics, reading comprehension, Boolean logic, … | PLANNED (shown as "planned" in the app) |
| Diagnoser | Pattern-based suspected gap, careless-slip alternative, unclassified mistakes | BUILT · TESTED |
| Checker | 2 new questions; confirmed / rejected / inconclusive; retest 2 of 3; mastery | BUILT · TESTED |
| Planner | Verified gaps only; prerequisite chain walk; teacher-forced focus | BUILT · TESTED |
| Tutor | Template lessons, worked examples, hints, practice, solutions | BUILT · TESTED |
| Tutor/Diagnoser | Optional AI wording with validation and fallback | BUILT · SIMULATED (no real provider call made) |
| Retest | Delay (`RETEST_DELAY_HOURS`, default 24), demo shortcut (`ALLOW_EARLY_RETEST`), new questions only | BUILT · TESTED |
| Replanning | Failed retest → gap stays open → new plan, lesson, practice, new retest | BUILT · TESTED (fractions and loops) |
| Student dashboard | Stats, continue learning, upcoming retests, open gaps, subjects/topics with progress, planned topics, history | BUILT · TESTED (API + browser) |
| Persistence | Progress saved per answer; resumes after reload / new login; duplicate submissions recorded once | BUILT · TESTED |
| Error handling | Crash during processing keeps answers → teacher review; friendly errors; loading/empty states | BUILT · TESTED |
| Teacher portal | Own classes only; class insights; student detail (gaps, evidence, Checker reasons, assessments, mastery); confirm/reject/focus/note with reason; audit trail | BUILT · TESTED (API + browser) |
| Parent view | Children's progress within consent scopes, no controls | BUILT · TESTED |
| Shared view | Adult learner shares chosen scopes with anyone | BUILT · TESTED |
| Teacher escalation | Automatic after 3 failed cycles | PARTIAL: when the question bank for a skill runs out (after the 2nd failed retest) the case goes to teacher review |
| Knowledge tracing | Bayesian Knowledge Tracing / probabilistic mastery | PLANNED |
| Prerequisite planning | General graph search / optimisation | PARTIAL: depth-first prerequisite chain walk + failed-skill filter |
| Notifications | Retest reminders, weekly parent email | PLANNED (parent "weekly email" preference is stored, nothing sends it) |
| Learning outcomes | Evidence that ELEVIA improves learning | NOT CLAIMED: no classroom evaluation yet |
