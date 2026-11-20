"""Build the multi-subject curriculum: data/topics/<topic>.json and data/curriculum.json.

    python scripts/build_curriculum.py

Sources are the authoring modules in scripts/curriculum/. Safety and correctness checks done here:
  * every code_output answer (and lesson example) is checked by RUNNING the fixed, author-written snippet
    with no builtins except print/range, and comparing the printed output;
  * every misconception answer must differ from the correct answer;
  * the whole bank is then loaded through backend.content.validate_all(), exactly as the app does.
The original fractions files (skill_map.json, questions.json, lessons.json) are not touched.
"""
import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.curriculum import cs_topics, english_topics, math_topics, science_topics  # noqa: E402

DATA = ROOT / "data"
OUT = DATA / "topics"


def run_snippet(code: str) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(code, {"__builtins__": {"print": print, "range": range}}, {})  # author-written snippets only
    return " ".join(buf.getvalue().split())


def check_code(item: dict, where: str) -> None:
    got = run_snippet(item["code"])
    if got != item["answer"]:
        raise SystemExit(f"{where}: snippet prints {got!r} but the answer says {item['answer']!r}")
    for wrong in item.get("patterns", {}):
        if wrong == got:
            raise SystemExit(f"{where}: misconception answer equals the real output")


SUBJECTS = [
    {"id": "mathematics", "name": "Mathematics", "icon": "∑", "color": "#2f4a8a",
     "description": "Number, ratio and algebra, checked with exact arithmetic.",
     "topics": ["fractions", "decimals", "percentages", "integers", "linear_equations"],
     "planned": ["Geometry", "Mensuration", "Statistics", "Probability"]},
    {"id": "science", "name": "Science", "icon": "⚛", "color": "#2e7d5b",
     "description": "Concept questions that separate real misconceptions from slips.",
     "topics": ["forces_motion", "states_of_matter"],
     "planned": ["Biology: plants and photosynthesis", "Light and sound", "Electric circuits"]},
    {"id": "english", "name": "English", "icon": "Aa", "color": "#a0522d",
     "description": "Grammar and sentence construction with exact answer checking.",
     "topics": ["past_tense", "subject_verb_agreement"],
     "planned": ["Vocabulary", "Reading comprehension", "Writing fundamentals"]},
    {"id": "computer_science", "name": "Computer Science", "icon": "</>", "color": "#6b3fa0",
     "description": "Predict what short programs print. Answers are verified by running the code.",
     "topics": ["variables", "loops"],
     "planned": ["Conditions and Boolean logic", "Algorithms", "Data structures"]},
]

FRACTIONS = {"id": "fractions", "subject": "mathematics", "name": "Fractions", "unit": "Number",
             "grade_min": 3, "grade_max": 6,
             "description": "Equivalent fractions, simplifying, comparing, common denominators, adding and multiplying.",
             "objectives": ["Find equivalent fractions and simplify", "Compare fractions",
                            "Add and subtract fractions with unlike denominators", "Multiply fractions"],
             "skills": ["fraction_basics", "equivalent_fractions", "simplifying_fractions", "comparing_fractions",
                        "common_denominators", "add_sub_like", "add_sub_unlike", "multiply_fractions"],
             "diagnostic_pools": {"A": "diagnostic:A", "B": "diagnostic:B"}, "original": True}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    topics = {"fractions": FRACTIONS}
    n_q = 0
    for mod in (math_topics, science_topics, english_topics, cs_topics):
        for build in mod.ALL:
            t = build()
            tid = t["topic"]["id"]
            for q in t["questions"]:
                if q["type"] == "code_output":
                    check_code(q, q["id"])
            for sid, lesson in t["lessons"].items():
                for i, ex in enumerate(lesson["worked_examples"]):
                    if ex.get("code"):
                        check_code(ex, f"lesson {sid} example {i + 1}")
            topics[tid] = {**t["topic"], "diagnostic_pools": {"A": f"diagnostic:{tid}:A", "B": f"diagnostic:{tid}:B"}}
            body = {"skills": t["skills"], "misconceptions": t["misconceptions"], "questions": t["questions"],
                    "lessons": t["lessons"]}
            (OUT / f"{tid}.json").write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            n_q += len(t["questions"])
    # keep the fractions skill list honest: only skills that really exist in skill_map.json
    fm = json.loads((DATA / "skill_map.json").read_text(encoding="utf-8"))
    topics["fractions"]["skills"] = [s["id"] for s in fm["skills"]]
    (DATA / "curriculum.json").write_text(json.dumps({"subjects": SUBJECTS, "topics": topics}, indent=1,
                                                     ensure_ascii=False) + "\n", encoding="utf-8")
    from backend.content import validate_all
    print(f"Wrote {len(topics) - 1} topic files ({n_q} questions).", validate_all())


if __name__ == "__main__":
    main()
