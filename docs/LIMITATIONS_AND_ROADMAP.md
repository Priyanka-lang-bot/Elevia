# Known limitations and future improvements

## Limitations (current version)

- **No classroom evaluation.** ELEVIA hasn't been tested with real students, so there is no evidence yet that it improves learning. We make no such claim.
- **Rule-based, not autonomous agents.** The Diagnoser, Checker, Planner and Tutor are deterministic rules coordinated by an orchestrator. That's intentional (auditable, repeatable), but they don't learn from data.
- **Fixed question banks.** Each teachable skill has 3–4 double-check, 3–5 practice and 6 retest questions. After two failed retests on the same skill, or several rounds of one topic, new questions run out and the case goes to teacher review. There is no automatic question generation.
- **Misconception coverage is limited** to 86 named patterns across 26 topics. Other wrong answers count as unclassified mistakes.
- **Science and English use multiple choice / exact words.** There is no free-text or essay marking; reading comprehension and writing are not built. Science covers 3 topics; electricity, light and heat are not built. Social Science covers 2 geography topics (latitude and longitude; time zones and IST); history, civics and economics are not built.
- **Computer Science is predict-the-output only.** Students don't write code (nothing student-written is ever executed).
- **Mastery is a simple rule** (retest 2 of 3; skill status from correct counts), not a probabilistic model such as Bayesian Knowledge Tracing.
- **Planning walks the prerequisite chain** of the gap skill and prefers failed earlier skills; it doesn't optimise a full learning path.
- **No automatic escalation after N failed cycles**; escalation happens when questions run out or the Checker is unsure.
- **Optional AI wording was tested only against simulated responses**; no real provider call was made.
- **Retest timing uses server time; no reminders or notifications** are sent.
- **Parent verification is email ownership + declaration**, not DPDP Rule 10-grade verifiable consent.
- **The six-month history in the demo is synthetic.** It was produced by running the real rules on simulated answers with a simulated calendar. It shows what the product does with six months of records; it is not evidence about real students.
- **Not a full Class 9 syllabus.** The demo student works on the 26 playable topics, several of which are foundation topics below Grade 9 (closing earlier gaps is the point). Chapters not built are listed as coming soon and have no records.
- **Hint usage is recorded but not used in decisions.**
- **The live deployment has no persistent database yet.** The Vercel project has no Turso variables, so the site runs on a temporary per-instance SQLite file. Demo mode is off there until `ELEVIA_DEMO_MODE=1` is set and the demo is seeded on Turso (see TEST_RESULTS.md).
- **The demo accounts are shared and writable.** Anyone who opens Riya, Dev or Arjun (or the teacher, with the code) can change what the next judge sees, e.g. by reviewing Riya's waiting case. The historical records stay intact, but the current state moves on. Run `python scripts/demo.py reset` before each judged session. It is a command-line reset that needs database credentials; there is no reset button on the site, because a public reset would let anyone wipe a judge's session.
- **"Upcoming" depends on the reference date.** The history ends on the date the demo was seeded, so seed on the morning of judging, or a retest booked for "tomorrow" will already be due.
- **Email sign-up needs a mail provider** on the live site (or `ELEVIA_DEMO_EMAIL_LINKS=1` for a demo).

## Future improvements (in order of value)

1. Classroom pilot with 1–2 teachers; measure retest pass rates against a baseline before claiming impact.
2. More topics: reading comprehension, electric circuits, light, heat, probability, volume, functions and lists (each already listed as "coming soon").
3. Larger and parameterised question banks so retests never run out (maths topics already generate from templates; extend to all).
4. Teacher authoring: let teachers add questions and misconception patterns through the portal.
5. Probabilistic mastery (e.g. BKT) once there is response data to calibrate it.
6. Prerequisite-aware recommendations across topics on the dashboard.
7. Reminders for due retests, and the weekly parent email (the preference is already stored).
8. Escalation rule: after 3 failed cycles on one skill, flag to the teacher automatically.
9. Verifiable parental consent that meets DPDP Rule 10.
10. Accessibility audit with screen-reader users, and Hindi/Marathi interface text.
