# Known limitations and future improvements

## Limitations (current version)

- **No classroom evaluation.** ELEVIA hasn't been tested with real students, so there is no evidence yet that it improves learning. We make no such claim.
- **Rule-based, not autonomous agents.** The Diagnoser, Checker, Planner and Tutor are deterministic rules coordinated by an orchestrator. That's intentional (auditable, repeatable), but they don't learn from data.
- **Fixed question banks.** Each skill has 4 double-check, 4 practice (3 in Science) and 6 retest questions. After two failed retests on the same skill, or several rounds of one topic, new questions run out and the case goes to teacher review. There is no automatic question generation.
- **Misconception coverage is limited** to 39 named patterns. Other wrong answers count as unclassified mistakes.
- **Science and English use multiple choice / exact words.** There is no free-text or essay marking; reading comprehension and writing are not built.
- **Computer Science is predict-the-output only.** Students don't write code (nothing student-written is ever executed).
- **Mastery is a simple rule** (retest 2 of 3; skill status from correct counts), not a probabilistic model such as Bayesian Knowledge Tracing.
- **Planning walks the prerequisite chain** of the gap skill and prefers failed earlier skills; it doesn't optimise a full learning path.
- **No automatic escalation after N failed cycles**; escalation happens when questions run out or the Checker is unsure.
- **Optional AI wording was tested only against simulated responses**; no real provider call was made.
- **Retest timing uses server time; no reminders or notifications** are sent.
- **Parent verification is email ownership + declaration**, not DPDP Rule 10-grade verifiable consent.
- **Teacher and parent dashboards show progress, not trends over time** (no charts until there is enough real data to make them meaningful).
- **Hint usage is recorded but not used in decisions.**
- **Live deployment not verified by me** (see TEST_RESULTS.md).

## Future improvements (in order of value)

1. Classroom pilot with 1–2 teachers; measure retest pass rates against a baseline before claiming impact.
2. More topics: geometry, statistics, ratio, reading comprehension, Boolean logic, plants and photosynthesis.
3. Larger and parameterised question banks so retests never run out (maths topics already generate from templates; extend to all).
4. Teacher authoring: let teachers add questions and misconception patterns through the portal.
5. Probabilistic mastery (e.g. BKT) once there is response data to calibrate it.
6. Prerequisite-aware recommendations across topics on the dashboard.
7. Reminders for due retests, and the weekly parent email (the preference is already stored).
8. Escalation rule: after 3 failed cycles on one skill, flag to the teacher automatically.
9. Verifiable parental consent that meets DPDP Rule 10.
10. Accessibility audit with screen-reader users, and Hindi/Marathi interface text.
