"""Multi-subject curriculum: every topic runs the full Diagnoser -> Checker -> Planner -> Tutor -> retest
journey through the real /learn routes, plus the deterministic answer checking for each question type."""
import pytest

from backend import db
from backend.content import curriculum, misconceptions, questions, topics, validate_all
from backend.engine import check_answer, correct_answer_text
from backend.generic_engine import parse_number
from tests.test_accounts import H, db_one, make_learner

NEW_TOPICS = [t for t in topics() if t != "fractions"]


@pytest.fixture
def me(client):
    token, _ = make_learner(client)
    return H(token)


def post(client, h, path, body):
    r = client.post(path, json=body, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def wrong_answer(q):
    """A valid answer that is wrong but matches no misconception."""
    if q["type"] == "mcq":
        bad = [o for o in q["options"] if o != q["answer"] and o not in q.get("patterns", {})]
        return bad[0] if bad else next(o for o in q["options"] if o != q["answer"])
    if q["type"] == "numeric":
        return "987654"
    return "zzzz"


def pattern_for(q, gap_skill):
    mis = misconceptions()
    for ans, code in q.get("patterns", {}).items():
        if mis[code]["gap_skill"] == gap_skill:
            return ans
    return None


def answer_all(client, h, st, choose):
    out = None
    for item in st["assessment"]["questions"]:
        if item["answered"]:
            continue
        q = questions()[item["id"]]
        out = post(client, h, "/learn/answer", {"assessment_id": st["assessment"]["id"], "question_id": q["id"],
                                                "answer": choose(q)})
        assert out["accepted"], out
    return out["state"]


def diagnose(client, h, topic_id):
    st = post(client, h, "/learn/start", {"grade": 7, "topic_id": topic_id})
    assert st["phase"] == "checkin" and st["topic"]["id"] == topic_id and st["assessment"]["total"] == 5
    first = next(questions()[x["id"]] for x in st["assessment"]["questions"] if questions()[x["id"]].get("patterns"))
    target = misconceptions()[next(iter(first["patterns"].values()))]["gap_skill"]
    st = answer_all(client, h, st, lambda q: pattern_for(q, target) or correct_answer_text(q))
    assert st["phase"] == "verify", st["headline"]
    return st, target


@pytest.mark.parametrize("topic_id", NEW_TOPICS)
def test_full_journey_on_every_topic(client, me, topic_id):
    st, target = diagnose(client, me, topic_id)
    assert st["gap"]["state"] == "checking"
    gap_skill = db_one("SELECT skill_id FROM gaps")[0]
    # double-check: repeat the same kind of mistake -> confirmed
    st = answer_all(client, me, st, lambda q: pattern_for(q, gap_skill) or wrong_answer(q))
    assert st["phase"] == "learn" and st["gap"]["state"] == "verified", st.get("why")
    assert db_one("SELECT status FROM gaps")[0] == "confirmed"
    lesson = st["lesson"]
    assert lesson["steps"] and lesson["worked_examples"] and all(e["steps"] for e in lesson["worked_examples"])
    assert st["assessment"]["kind"] == "practice" and st["assessment"]["total"] >= 3
    focus = db_one("SELECT focus_skill FROM plans WHERE status='active'")[0]
    # practice (right answers) -> retest -> pass
    st = answer_all(client, me, st, correct_answer_text)
    if st["phase"] == "learn":
        st = post(client, me, "/learn/practice/finish", {"assessment_id": st["assessment"]["id"]})
    assert st["phase"] == "retest_wait"
    st = post(client, me, "/learn/retest/start", {"early": True, "topic_id": topic_id})
    assert st["phase"] == "retest" and st["assessment"]["total"] == 3
    with db.transaction() as c:
        seen = {r[0] for r in c.execute("SELECT question_id FROM responses r JOIN assessments a "
                                        "ON a.id=r.assessment_id WHERE a.kind!='retest'").fetchall()}
    assert not seen & {q["id"] for q in st["assessment"]["questions"]}       # new questions only
    st = answer_all(client, me, st, correct_answer_text)
    assert st["phase"] == "done" and st["outcome"]["title"] == "Gap closed"
    assert db_one("SELECT status FROM skill_mastery WHERE skill_id=?", gap_skill)[0] == "mastered"
    assert focus  # the planner chose a teachable focus


@pytest.mark.parametrize("topic_id", NEW_TOPICS)
def test_rejected_gap_on_every_topic(client, me, topic_id):
    st, _ = diagnose(client, me, topic_id)
    st = answer_all(client, me, st, correct_answer_text)        # double-check all right -> it was a slip
    assert st["phase"] == "done" and st["outcome"]["title"] == "It was a slip, not a gap"
    assert db_one("SELECT COUNT(*) FROM plans")[0] == 0 and db_one("SELECT COUNT(*) FROM lessons")[0] == 0


def test_failed_retest_replans_on_a_new_subject(client, me):
    st, _ = diagnose(client, me, "loops")
    gap_skill = db_one("SELECT skill_id FROM gaps")[0]
    st = answer_all(client, me, st, lambda q: pattern_for(q, gap_skill) or wrong_answer(q))
    st = answer_all(client, me, st, correct_answer_text)
    if st["phase"] == "learn":
        st = post(client, me, "/learn/practice/finish", {"assessment_id": st["assessment"]["id"]})
    st = post(client, me, "/learn/retest/start", {"early": True, "topic_id": "loops"})
    st = answer_all(client, me, st, wrong_answer)
    assert st["phase"] == "learn" and st["gap"]["state"] == "still_present" and st["round"] == 2
    assert db_one("SELECT COUNT(*) FROM lessons")[0] == 2


def test_two_topics_run_side_by_side_and_dashboard_tracks_both(client, me):
    d = client.get("/learn/dashboard", headers=me).json()
    assert d["phase"] == "welcome" and d["needs_grade"] and d["answers"]["total"] == 0
    assert [s["id"] for s in d["subjects"]] == ["mathematics", "science", "english", "computer_science"]
    a = post(client, me, "/learn/start", {"grade": 6, "topic_id": "decimals"})
    b = post(client, me, "/learn/start", {"topic_id": "past_tense"})
    assert a["case_id"] != b["case_id"]
    again = post(client, me, "/learn/start", {"topic_id": "decimals"})
    assert again["case_id"] == a["case_id"]                     # one active round per topic
    # answering one topic doesn't touch the other
    post(client, me, "/learn/answer", {"assessment_id": a["assessment"]["id"],
                                       "question_id": a["assessment"]["questions"][0]["id"], "answer": "0.5"})
    pt = client.get("/learn/state", params={"topic": "past_tense"}, headers=me).json()
    assert pt["assessment"]["answered"] == 0
    d = client.get("/learn/dashboard", headers=me).json()
    assert d["phase"] == "dashboard" and d["student"]["grade"] == 6
    assert {c["topic_id"] for c in d["continue_learning"]} == {"decimals", "past_tense"}
    assert d["totals"]["topics_started"] == 2 and d["answers"]["total"] == 1
    dec = next(t for s in d["subjects"] for t in s["topics"] if t["id"] == "decimals")
    assert dec["phase"] == "checkin" and dec["recommended"] is True
    loops = next(t for s in d["subjects"] for t in s["topics"] if t["id"] == "loops")
    assert loops["recommended"] is False                        # grade 6 is below the loops range (7-10)
    assert all(s["planned"] for s in d["subjects"])             # planned topics are listed honestly, not playable


def test_unknown_topic_is_refused(client, me):
    assert client.post("/learn/start", json={"grade": 6, "topic_id": "astrology"}, headers=me).status_code == 404
    assert client.get("/learn/state", params={"topic": "nope"}, headers=me).status_code == 404


def test_curriculum_structure_is_complete():
    counts = validate_all()
    assert counts["subjects"] == 4 and counts["topics"] == 11
    cur = curriculum()
    for tid, t in cur["topics"].items():
        assert t["objectives"] and t["skills"] and t["unit"]
        for sk in t["skills"]:
            pools = {q["pool"] for q in questions().values() if q["skill_id"] == sk or sk in q["gap_targets"]}
            if tid != "fractions":
                assert f"verification:{sk}" in pools and f"practice:{sk}" in pools and f"retest:{sk}" in pools, sk


# ---------------------------------------------------------------- deterministic checking per question type

def q_of(qid):
    return questions()[qid]


def test_numeric_answers_are_exact():
    q = q_of("DEC-DA3")                         # 2.5 + 1.25
    for ok in ("3.75", "3.750", " 3.75 ", "15/4"):
        assert check_answer(q, ok).correct, ok
    r = check_answer(q, "1.5")
    assert not r.correct and r.pattern == "DEC_RIGHT_ALIGN"
    assert not check_answer(q, "abc").valid and not check_answer(q, "1/0").valid
    assert parse_number("0.1") + parse_number("0.2") == parse_number("0.3")     # no float error


def test_percent_and_negative_numbers():
    q = q_of("PCT-DA2")                         # 0.4 as a percentage
    assert check_answer(q, "40").correct and check_answer(q, "40%").correct
    assert check_answer(q, "4").pattern == "PCT_DECIMAL_SHIFT"
    q = q_of("INT-DA1")                         # −3 + (−4)
    assert check_answer(q, "-7").correct and check_answer(q, "−7").correct
    assert check_answer(q, "7").pattern == "INT_TWO_NEG_POS"


def test_text_and_multiple_choice():
    past = next(q for q in questions().values() if q["pool"].startswith("diagnostic:past_tense") and q["answer"] == "went")
    assert check_answer(past, "Went.").correct and check_answer(past, "  went ").correct
    assert check_answer(past, "goed").pattern == "ENG_OVERREGULARISE"
    sva = q_of("SVA-DA2")
    assert check_answer(sva, "not an option").valid is False
    wrong = next(iter(sva["patterns"]))
    assert check_answer(sva, wrong).pattern in ("ENG_NEAREST_NOUN", "ENG_EACH_PLURAL")


def test_code_answers_are_never_executed():
    q = q_of("VAR-DA1")
    r = check_answer(q, "print(__import__('os').getcwd())")
    assert r.valid is False or r.correct is False                # just text, compared, never run
    assert check_answer(q, q["answer"]).correct
    assert check_answer(q, "3").pattern == "CS_KEEPS_FIRST"
