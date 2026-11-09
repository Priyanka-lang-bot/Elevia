"""Generates data/questions.json.

Questions store their operands, not a typed answer key. The correct answer is
computed with Python's exact Fraction arithmetic in backend/fractions_engine.py,
so a typo in an answer key is impossible.

Run:  python scripts/build_question_bank.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "questions.json"

questions = []


def q(qid, pool, skill, qtype, gap_targets, **kw):
    item = {"id": qid, "pool": pool, "skill_id": skill, "type": qtype, "gap_targets": gap_targets}
    item.update(kw)
    questions.append(item)


CD = ["common_denominators"]
EQ = ["equivalent_fractions"]
SI = ["simplifying_fractions"]
CO = ["comparing_fractions"]
MU = ["multiply_fractions"]

# ---------------- Diagnostic sets (5 questions each) ----------------
# Set A is the main demo set.
q("DA1", "diagnostic:A", "add_sub_like", "add", [], a="1/5", b="2/5")
q("DA2", "diagnostic:A", "equivalent_fractions", "equivalent", EQ, a="1/2", target=8)
q("DA3", "diagnostic:A", "add_sub_unlike", "add", CD, a="1/2", b="1/3")
q("DA4", "diagnostic:A", "simplifying_fractions", "simplify", SI, a="6/8")
q("DA5", "diagnostic:A", "add_sub_unlike", "add", CD, a="1/4", b="2/3")

# Set B is used for a student's second (or later) learning cycle.
q("DB1", "diagnostic:B", "comparing_fractions", "compare", CO, a="1/3", b="1/8")
q("DB2", "diagnostic:B", "add_sub_like", "sub", [], a="5/7", b="2/7")
q("DB3", "diagnostic:B", "multiply_fractions", "multiply", MU, a="2/3", b="3/5")
q("DB4", "diagnostic:B", "add_sub_unlike", "sub", CD, a="4/5", b="1/2")
q("DB5", "diagnostic:B", "simplifying_fractions", "simplify", SI, a="10/15")

# ---------------- Per-gap pools ----------------
# verification = Checker's confirmation questions (new items, some similar-concept)
# practice     = Tutor's practice items (recorded, never used for mastery)
# retest       = Checker's later retest items
pools = {
    "common_denominators": {
        "verification": [
            ("add", "add_sub_unlike", {"a": "1/3", "b": "1/6"}, "same_type"),
            ("add", "add_sub_unlike", {"a": "2/5", "b": "1/4"}, "same_type"),
            ("lcd", "common_denominators", {"a": "1/4", "b": "1/6"}, "similar_concept"),
            ("sub", "add_sub_unlike", {"a": "3/4", "b": "1/3"}, "similar_concept"),
        ],
        "practice": [
            ("lcd", "common_denominators", {"a": "1/2", "b": "1/5"}),
            ("equivalent", "common_denominators", {"a": "2/3", "target": 12}),
            ("add", "add_sub_unlike", {"a": "1/2", "b": "1/4"}),
            ("add", "add_sub_unlike", {"a": "1/3", "b": "2/5"}),
            ("sub", "add_sub_unlike", {"a": "5/6", "b": "1/4"}),
        ],
        "retest": [
            ("add", "add_sub_unlike", {"a": "1/6", "b": "3/4"}),
            ("add", "add_sub_unlike", {"a": "2/3", "b": "1/5"}),
            ("sub", "add_sub_unlike", {"a": "7/8", "b": "1/3"}),
            ("add", "add_sub_unlike", {"a": "3/8", "b": "1/6"}),
            ("add", "add_sub_unlike", {"a": "2/7", "b": "1/2"}),
            ("sub", "add_sub_unlike", {"a": "9/10", "b": "2/5"}),
        ],
    },
    "equivalent_fractions": {
        "verification": [
            ("equivalent", "equivalent_fractions", {"a": "2/3", "target": 9}, "same_type"),
            ("equivalent", "equivalent_fractions", {"a": "3/4", "target": 20}, "same_type"),
            ("simplify", "simplifying_fractions", {"a": "4/12"}, "similar_concept"),
        ],
        "practice": [
            ("equivalent", "equivalent_fractions", {"a": "1/3", "target": 6}),
            ("equivalent", "equivalent_fractions", {"a": "2/5", "target": 15}),
            ("equivalent", "equivalent_fractions", {"a": "5/6", "target": 18}),
            ("equivalent", "equivalent_fractions", {"a": "3/8", "target": 24}),
        ],
        "retest": [
            ("equivalent", "equivalent_fractions", {"a": "4/5", "target": 25}),
            ("equivalent", "equivalent_fractions", {"a": "1/6", "target": 30}),
            ("equivalent", "equivalent_fractions", {"a": "3/7", "target": 21}),
        ],
    },
    "simplifying_fractions": {
        "verification": [
            ("simplify", "simplifying_fractions", {"a": "8/12"}, "same_type"),
            ("simplify", "simplifying_fractions", {"a": "15/25"}, "same_type"),
            ("simplify", "simplifying_fractions", {"a": "18/24"}, "similar_concept"),
        ],
        "practice": [
            ("simplify", "simplifying_fractions", {"a": "4/6"}),
            ("simplify", "simplifying_fractions", {"a": "9/12"}),
            ("simplify", "simplifying_fractions", {"a": "12/16"}),
            ("simplify", "simplifying_fractions", {"a": "14/21"}),
        ],
        "retest": [
            ("simplify", "simplifying_fractions", {"a": "16/20"}),
            ("simplify", "simplifying_fractions", {"a": "21/28"}),
            ("simplify", "simplifying_fractions", {"a": "24/36"}),
        ],
    },
    "comparing_fractions": {
        "verification": [
            ("compare", "comparing_fractions", {"a": "1/4", "b": "1/6"}, "same_type"),
            ("compare", "comparing_fractions", {"a": "2/9", "b": "2/5"}, "same_type"),
            ("compare", "comparing_fractions", {"a": "3/4", "b": "5/8"}, "similar_concept"),
        ],
        "practice": [
            ("compare", "comparing_fractions", {"a": "1/2", "b": "1/10"}),
            ("compare", "comparing_fractions", {"a": "3/7", "b": "3/4"}),
            ("compare", "comparing_fractions", {"a": "2/3", "b": "3/5"}),
            ("compare", "comparing_fractions", {"a": "1/5", "b": "1/12"}),
        ],
        "retest": [
            ("compare", "comparing_fractions", {"a": "1/9", "b": "1/2"}),
            ("compare", "comparing_fractions", {"a": "4/5", "b": "4/9"}),
            ("compare", "comparing_fractions", {"a": "5/6", "b": "7/9"}),
        ],
    },
    "multiply_fractions": {
        "verification": [
            ("multiply", "multiply_fractions", {"a": "1/2", "b": "3/4"}, "same_type"),
            ("multiply", "multiply_fractions", {"a": "2/5", "b": "1/3"}, "same_type"),
            ("multiply", "multiply_fractions", {"a": "3/4", "b": "2/3"}, "similar_concept"),
        ],
        "practice": [
            ("multiply", "multiply_fractions", {"a": "1/3", "b": "1/4"}),
            ("multiply", "multiply_fractions", {"a": "2/3", "b": "4/5"}),
            ("multiply", "multiply_fractions", {"a": "3/8", "b": "2/3"}),
            ("multiply", "multiply_fractions", {"a": "5/6", "b": "3/10"}),
        ],
        "retest": [
            ("multiply", "multiply_fractions", {"a": "3/5", "b": "1/2"}),
            ("multiply", "multiply_fractions", {"a": "4/7", "b": "2/3"}),
            ("multiply", "multiply_fractions", {"a": "5/9", "b": "3/5"}),
        ],
    },
}

prefix = {
    "common_denominators": "CD",
    "equivalent_fractions": "EQ",
    "simplifying_fractions": "SI",
    "comparing_fractions": "CO",
    "multiply_fractions": "MU",
}
pool_letter = {"verification": "V", "practice": "P", "retest": "R"}

for gap, by_pool in pools.items():
    for pool, items in by_pool.items():
        for i, item in enumerate(items, 1):
            qtype, skill, operands = item[0], item[1], item[2]
            extra = {}
            if pool == "verification":
                extra["check_role"] = item[3]
            q(f"{prefix[gap]}-{pool_letter[pool]}{i}", f"{pool}:{gap}", skill, qtype, [gap], **operands, **extra)

OUT.write_text(json.dumps({"version": 1, "questions": questions}, indent=2))
print(f"Wrote {len(questions)} questions to {OUT}")
