import json

import httpx
import pytest

from backend import llm
from backend.agents import checker, diagnoser, planner, tutor


def resp(qid, correct, pattern=None, skill="add_sub_unlike", gap=("common_denominators",), prompt="1/2 + 1/3 = ?",
         answer="2/5", expected="5/6"):
    return {"question_id": qid, "skill_id": skill, "gap_targets": list(gap), "prompt": prompt, "answer": answer,
            "is_correct": correct, "pattern": pattern, "expected": expected}


DEMO = [resp("DA1", True, skill="add_sub_like", gap=()), resp("DA2", True, skill="equivalent_fractions", gap=("equivalent_fractions",)),
        resp("DA3", False, "ADD_ACROSS"), resp("DA4", True, skill="simplifying_fractions", gap=("simplifying_fractions",)),
        resp("DA5", False, "ADD_ACROSS", answer="3/7")]


# ---------------- Diagnoser

def test_diagnoser_suspects_common_denominators_with_high_confidence():
    out = diagnoser.run({"student": {"grade": 5}, "responses": DEMO})
    assert out["has_gap"] and out["status"] == "suspected"
    assert out["primary"]["skill_id"] == "common_denominators"
    assert out["primary"]["confidence_label"] == "high"
    assert out["score"] == {"correct": 3, "total": 5}
    assert out["mode"] == "rules" and "no AI model" in out["llm_note"]


def test_diagnoser_no_gap_when_all_correct():
    out = diagnoser.run({"student": {}, "responses": [resp("x", True)]})
    assert not out["has_gap"]


def test_diagnoser_low_confidence_for_unclassified_error_and_slip_alternative():
    out = diagnoser.run({"student": {}, "responses": [resp("x", False, None), resp("y", True)]})
    assert out["primary"]["confidence_label"] == "low"
    assert any(a["skill_name"] == "Careless slip" for a in out["alternatives"])


# ---------------- Checker

GAP = {"skill_id": "common_denominators", "misconception": "ADD_ACROSS"}


def test_checker_selects_new_and_similar_concept_questions():
    sel = checker.select_verification("common_denominators", {"DA3"})
    assert sel["ok"] and len(sel["question_ids"]) == 2
    roles = {r["role"] for r in sel["rationale"]}
    assert roles == {"same_type", "similar_concept"}


def test_checker_excludes_seen_questions():
    sel = checker.select_verification("common_denominators", {"CD-V1", "CD-V2", "CD-V3", "CD-V4"})
    assert not sel["ok"]


def test_checker_confirmed_rejected_inconclusive():
    assert checker.evaluate_verification(GAP, [resp("a", False, "ADD_ACROSS"), resp("b", False, "ADD_ACROSS")])["verdict"] == "confirmed"
    assert checker.evaluate_verification(GAP, [resp("a", True), resp("b", True)])["verdict"] == "rejected"
    assert checker.evaluate_verification(GAP, [resp("a", False, None), resp("b", True)])["verdict"] == "inconclusive"


def test_checker_retest_threshold():
    assert checker.evaluate_retest(GAP, [resp("a", True), resp("b", True), resp("c", False)], 0.0)["passed"]
    out = checker.evaluate_retest(GAP, [resp("a", True), resp("b", False), resp("c", False)], 0.0)
    assert not out["passed"] and out["new_gap_status"] == "still_present"


def test_only_retest_can_mark_mastered():
    ups = checker.mastery_updates([resp("a", True)], "diagnostic")
    assert ups["add_sub_unlike"]["status"] == "developing"
    ups = checker.mastery_updates([resp("a", True)], "retest", gap_skill="common_denominators", retest_passed=True)
    assert ups["common_denominators"]["status"] == "mastered"


# ---------------- Planner

def test_planner_refuses_unverified_gap():
    for status in ("suspected", "inconclusive", "rejected"):
        with pytest.raises(planner.UnverifiedGapError):
            planner.run({"gap": {"skill_id": "common_denominators", "status": status, "verified_by": None}})


def test_planner_selects_common_denominators():
    out = planner.run({"gap": {"skill_id": "common_denominators", "status": "confirmed", "verified_by": "Checker"},
                       "mastery": {"equivalent_fractions": "developing"}, "failed_skills": ["add_sub_unlike"]})
    assert out["focus_skill"] == "common_denominators"
    assert [p["skill_id"] for p in out["path"]] == ["common_denominators", "add_sub_unlike"]


def test_planner_starts_with_weak_prerequisite():
    out = planner.run({"gap": {"skill_id": "common_denominators", "status": "confirmed", "verified_by": "Checker"},
                       "mastery": {"equivalent_fractions": "needs_practice"}})
    assert out["focus_skill"] == "equivalent_fractions"


def test_planner_teacher_forced_focus():
    out = planner.run({"gap": {"skill_id": "common_denominators", "status": "confirmed", "verified_by": "teacher:Ms R"},
                       "forced_focus": "simplifying_fractions"})
    assert out["focus_skill"] == "simplifying_fractions" and "Teacher" in out["rationale"]


# ---------------- Tutor

TUTOR_IN = {"focus_skill": "common_denominators", "student": {"grade": 5},
            "gap": {"skill_id": "common_denominators", "misconception": "ADD_ACROSS",
                    "evidence": {"diagnosis": [{"prompt": "1/2 + 1/3 = ?", "answer": "2/5"}]}}}


def test_tutor_template_lesson():
    out = tutor.run(TUTOR_IN)
    assert out["source"] == "template"
    assert "2/5" in out["personal_note"]
    assert out["worked_examples"][0]["answer"] == "5/6"
    assert len(out["practice"]) >= 4 and all("expected" not in p for p in out["practice"])


def test_tutor_arithmetic_checker():
    assert tutor.arithmetic_errors("so 1/2 + 1/3 = 5/6 and 3/4 - 1/4 = 1/2") == []
    assert tutor.arithmetic_errors("so 1/2 + 1/3 = 2/5") == ["1/2 + 1/3 = 2/5"]


# ---------------- LLM integration (fake HTTP transport; no real network)

def _fake(content: str, status=200):
    def handler(request: httpx.Request):
        body = {"content": [{"type": "text", "text": content}]}
        return httpx.Response(status, json=body)
    return httpx.MockTransport(handler)


@pytest.fixture
def anthropic_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-SECRET")


def test_missing_key_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    st = llm.status()
    assert st["mode"] == "mock" and "LLM_API_KEY" in st["reason"]


def test_valid_llm_output_is_used(anthropic_env):
    good = {"personal_note": "You added the tops and the bottoms. Let's make the pieces the same size first.",
            "steps": ["Check the denominators.", "Find the LCD.", "Rewrite both fractions.", "Add the numerators."]}
    llm.set_transport(_fake(json.dumps(good)))
    out = tutor.run(TUTOR_IN)
    assert out["source"] == "llm" and out["steps"] == good["steps"]


def test_llm_output_with_wrong_maths_is_rejected(anthropic_env):
    bad = {"personal_note": "Remember that 1/2 + 1/3 = 2/6, easy!",
           "steps": ["Check the denominators.", "Find the LCD.", "Rewrite both fractions."]}
    llm.set_transport(_fake(json.dumps(bad)))
    out = tutor.run(TUTOR_IN)
    assert out["source"] == "template" and "arithmetic check failed" in out["llm_note"]


def test_llm_invalid_json_and_http_error_fall_back(anthropic_env):
    llm.set_transport(_fake("sorry, I can't do that"))
    assert diagnoser.run({"student": {}, "responses": DEMO})["mode"] == "rules"
    llm.set_transport(_fake("{}", status=500))
    out = diagnoser.run({"student": {}, "responses": DEMO})
    assert out["mode"] == "rules" and "HTTP 500" in out["llm_note"]
    assert "SECRET" not in out["llm_note"]


def test_llm_cannot_claim_certainty(anthropic_env):
    llm.set_transport(_fake(json.dumps({"hypothesis": "The gap is confirmed: this student definitely cannot add.",
                                        "student_message": "Let's check a few more questions together."})))
    out = diagnoser.run({"student": {}, "responses": DEMO})
    assert out["mode"] == "rules"  # rejected by validator
    assert out["primary"]["skill_id"] == "common_denominators"


def test_llm_wording_used_but_cannot_change_skill_or_confidence(anthropic_env):
    llm.set_transport(_fake(json.dumps({
        "hypothesis": "The student may be treating numerators and denominators as separate whole numbers.",
        "student_message": "ELEVIA will check this with a couple of new questions."})))
    out = diagnoser.run({"student": {}, "responses": DEMO})
    assert out["mode"] == "rules+llm" and out["status"] == "suspected"
    assert out["primary"]["confidence"] == 0.8
