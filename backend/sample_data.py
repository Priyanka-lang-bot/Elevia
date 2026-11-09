"""SAMPLE students for demonstration, produced by running scripted answers through the real
workflow. Flagged is_sample=1 and labelled "sample" in the UI."""
from __future__ import annotations

from . import db, orchestrator as o
from .content import questions
from .fractions_engine import correct_answer_text


def _answer_all(case: dict, answers: dict[str, str] | None = None) -> dict:
    a = case["open_assessment"]
    r = None
    for q in a["questions"]:
        if q["answered"]:
            continue
        ans = (answers or {}).get(q["id"], correct_answer_text(questions()[q["id"]]))
        r = o.submit_answer(a["id"], q["id"], ans)
    return r["case"] if r else case


def seed() -> None:
    db.init_db()
    existing = {s["display_name"] for s in o.list_students()}

    # 1. Fresh student for the live demo: no activity yet.
    if "Asha" not in existing:
        o.create_student("Asha", 5, is_sample=True)

    # 2. A student who has been through a full cycle (gap confirmed -> taught -> retest passed).
    if "Rohan" not in existing:
        s = o.create_student("Rohan", 5, is_sample=True)
        c = o.start_case(s["id"])
        c = _answer_all(c, {"DA3": "2/5", "DA5": "3/7"})            # ADD_ACROSS twice
        c = _answer_all(c, {"CD-V1": "2/9", "CD-V3": "10"})          # same mistake again -> confirmed
        a = c["open_assessment"]                                     # practice
        for q in a["questions"][:3]:
            o.submit_answer(a["id"], q["id"], correct_answer_text(questions()[q["id"]]))
        c = o.finish_practice(a["id"])
        c = o.start_retest(c["id"], early=True)                      # logged as a demo override
        _answer_all(c, {c["open_assessment"]["questions"][2]["id"]: "8/11"})  # 2/3 correct -> passes

    # 3. A student whose verification was inconclusive: waiting for teacher review.
    if "Meera" not in existing:
        s = o.create_student("Meera", 4, is_sample=True)
        c = o.start_case(s["id"])
        c = _answer_all(c, {"DA3": "2/5"})                           # one ADD_ACROSS
        _answer_all(c, {"CD-V1": "3/4"})                             # wrong, no known pattern; other correct

    print("Sample students:", ", ".join(s["display_name"] for s in o.list_students() if s["is_sample"]))
