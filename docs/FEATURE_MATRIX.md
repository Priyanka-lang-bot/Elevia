# Feature implementation matrix

Status words: **BUILT** (code exists) · **TESTED** (automated tests and/or the browser run cover it) · **DEPLOYED** (in a successful Vercel build; see note) · **SIMULATED** (only exercised against fakes) · **PARTIAL** · **PLANNED** (not built).

Deployment note: the `round3` branch builds successfully as a Vercel **preview** on the `frontend-pmvi` project. On 22 Nov 2026 I opened the preview in a browser:
- pages, `/api/health` and the catalogue work;
- the project has no Turso variables, so data is temporary (per instance);
- demo mode is off there.

See TEST_RESULTS.md.

| Area | Feature | Status |
|---|---|---|
| Landing | Hero, problem, how it works, features, subjects (live catalogue), student/teacher sections with real screenshots, why ELEVIA, CTA, footer | BUILT · TESTED (browser) · DEPLOYED (preview, checked) |
| Demo | One-click demo login for 6 fictional accounts (env-gated, registry-only, rate-limited, normal sessions, guarded actions) | BUILT · TESTED (API + browser) |
| Demo | Seed and reset of the demo school through the real routes; reset deletes only registry rows | BUILT · TESTED (incl. real user survives reset) |
| Landing | Responsive (desktop/phone), mobile menu, no horizontal overflow, smooth in-page nav, no dead links | BUILT · TESTED (browser) |
| Landing | SEO title/description, static crawlable HTML | BUILT |
| Accounts | Three sign-up pathways, parent consent, school codes + teacher approval, email verification, password reset | BUILT · TESTED (existing suite) |
| Accounts | Teachers/admins by invitation; sharing grants with scopes and expiry; access log | BUILT · TESTED |
| Security | scrypt, cookie sessions, CSRF, rate limits/lockout, CSP, self-hosted fonts | BUILT · TESTED (unit); CSP from `vercel.json` only applies on Vercel |
| Curriculum | Subject → topic → skill → misconception → questions → lessons, cross-topic prerequisites, build-time validation | BUILT · TESTED |
| Mathematics | Fractions, decimals, percentages, integers, linear equations, order of operations, factors and multiples, ratio and proportion, perimeter and area, averages, angles: full journey | BUILT · TESTED (every topic end to end) |
| Science | Forces and motion, states of matter, scientific reasoning (fair tests): full journey | BUILT · TESTED |
| English | Past tense verbs, subject–verb agreement, parts of speech, apostrophes: full journey | BUILT · TESTED |
| Computer Science | Variables, loops, data types, conditionals, logical reasoning, algorithms: predict-the-output, answers verified by execution at build time, student input never executed | BUILT · TESTED |
| Other topics | Probability, area of circles, volume, graphs, heat, light, electric circuits, photosynthesis, reading comprehension, sentence construction, vocabulary, functions, lists, sorting | PLANNED (shown as "coming soon" in the app) |
| Diagnoser | Pattern-based suspected gap, careless-slip alternative, unclassified mistakes | BUILT · TESTED |
| Checker | 2 new questions; confirmed / rejected / inconclusive; retest 2 of 3; mastery | BUILT · TESTED |
| Planner | Verified gaps only; prerequisite chain walk; teacher-forced focus | BUILT · TESTED |
| Tutor | Template lessons, worked examples, hints, practice, solutions | BUILT · TESTED |
| Tutor/Diagnoser | Optional AI wording with validation and fallback | BUILT · SIMULATED (no real provider call made) |
| Retest | Delay (`RETEST_DELAY_HOURS`, default 24), demo shortcut (`ALLOW_EARLY_RETEST`), new questions only | BUILT · TESTED |
| Replanning | Failed retest → gap stays open → new plan, lesson, practice, new retest | BUILT · TESTED (fractions and loops) |
| Student dashboard | "What to do next" card, stats, continue learning, upcoming retests, open gaps, subjects/topics with progress, planned topics, history | BUILT · TESTED (API + browser) |
| Persistence | Progress saved per answer; resumes after reload / new login; duplicate submissions recorded once | BUILT · TESTED |
| Error handling | Crash during processing keeps answers → teacher review; friendly errors; loading/empty states | BUILT · TESTED |
| Teacher portal | Own classes only; review queue with reasons; intervention history; confirmed-gaps column; class insights; student detail (gaps, evidence, Checker reasons, assessments, mastery); confirm/reject/focus/note with reason; audit trail | BUILT · TESTED (API + browser) |
| Parent view | Plain-language summary card per child, within consent scopes, no controls | BUILT · TESTED |
| Shared view | Adult learner shares chosen scopes with anyone | BUILT · TESTED |
| Teacher escalation | Automatic after 3 failed cycles | PARTIAL: when the question bank for a skill runs out (after the 2nd failed retest) the case goes to teacher review |
| Knowledge tracing | Bayesian Knowledge Tracing / probabilistic mastery | PLANNED |
| Prerequisite planning | General graph search / optimisation | PARTIAL: depth-first prerequisite chain walk + failed-skill filter |
| Notifications | Retest reminders, weekly parent email | PLANNED (parent "weekly email" preference is stored, nothing sends it) |
| Learning outcomes | Evidence that ELEVIA improves learning | NOT CLAIMED: no classroom evaluation yet |
