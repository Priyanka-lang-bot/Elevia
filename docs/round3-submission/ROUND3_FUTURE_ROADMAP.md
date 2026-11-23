# ELEVIA: Future development roadmap

**Everything on this page is a future plan. None of it is implemented today** unless a line says "builds on" an existing feature. What exists now is listed in `ROUND3_FEATURE_MATRIX.md`.

## Short term (next 1–3 months)

| Improvement | Why it matters for ELEVIA | Builds on |
|---|---|---|
| **Classroom pilot with 1–2 teachers** | The most important step. We currently make no learning-outcome claims. The pilot would compare against a baseline: retest pass rates and time-to-mastery against a matched class or the students' own earlier results, and teacher time per case | The existing teacher portal and history, which already record everything a pilot needs |
| **The "coming soon" topics** | Wider Class 9 coverage: reading comprehension, electric circuits, light, democracy, the French Revolution, probability, functions | The curriculum authoring and validation pipeline (`scripts/curriculum/`, build-time checks) |
| **Parameterised question banks** | Banks run out after repeated failed retests on one skill; generated variants would remove that limit | Maths and Social Science banks are already generated from rules and tables |
| **Retest reminders** | Students forget delayed retests; a reminder makes the delay useful | The retest schedule already stored per case |
| **Teacher authoring of questions and misconceptions** | Teachers know the mistakes their class makes; letting them add patterns improves diagnosis locally | The question format and validator |
| **Continuous integration** | Run the 202 tests and the browser checks on every pull request | The existing test suites |

## Medium term (3–9 months)

| Improvement | Why it matters | Notes |
|---|---|---|
| **A validated mastery model** (e.g. Bayesian Knowledge Tracing) | The 2-of-3 retest rule is transparent but coarse | Only once pilot data exists to fit and validate parameters; the rule stays as an explainable baseline |
| **Better prerequisite-aware learning paths** | Plans follow one prerequisite chain today | Plan across several weak skills and order them, still explaining each choice |
| **Richer misconception diagnosis** | Unlisted wrong answers are "unclassified" | Mine anonymised pilot answers for new recurring patterns, reviewed by teachers before use. An LLM could *suggest* candidate patterns, but rules stay the decision-makers |
| **Teacher analytics** | Classes over a term: which interventions led to passes | Extends the class overview and insights already computed from records |
| **Parent engagement** | Parents see progress but get no updates | Opt-in weekly summaries within existing consent scopes |
| **Hindi and Marathi interface** | Reach students who are more comfortable in their own language | Interface text first; curriculum translation needs subject-expert review |
| **Accessibility audit** | Keyboard, focus, reduced motion and no-JS are handled; a formal WCAG 2.2 AA audit with screen-reader users hasn't been done | Include students with learning differences in testing |

## Long term (9+ months)

| Improvement | Why it matters | Notes |
|---|---|---|
| **Secure institutional onboarding** | Schools need bulk class import, single sign-on and data agreements | Verifiable parental consent to DPDP Rule 10 standard (today: email ownership plus declaration) |
| **Scalability and performance** | Insights are computed per request, fine for a class but not for a whole district | Pre-computed summaries; read replicas; load testing on Turso |
| **Integrations** | Teachers already use school systems | Export to school information systems; LTI for learning platforms; Google Classroom rosters |
| **Offline-friendly student app** | Unreliable connectivity in many schools | The server already saves after every answer; a sync queue would extend this |
| **Free-response and spoken answers** | Multiple choice limits what can be diagnosed in English and Science | Requires careful validation; any AI marking would be checked by rules and teachers |

## What will not change

- **Verify before you teach.** No lesson for an unverified gap.
- **Explainable decisions.** Every decision is written to the log with its reason. Teachers can override, with a reason.
- **Honest claims.** Nothing will be claimed about learning outcomes until it is measured.
