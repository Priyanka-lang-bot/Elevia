"""Demo environment for judges: a fictional Class 9 with six months of learning history.

    python scripts/demo.py seed  [--reference-date YYYY-MM-DD]   create the demo (refuses if it already exists)
    python scripts/demo.py reset [--reference-date YYYY-MM-DD]   delete ONLY demo rows (demo_registry), then seed
    python scripts/demo.py status                                show which demo accounts exist

Uses the database configured in .env (local SQLite, or Turso when TURSO_DATABASE_URL is set).

How the history is made
-----------------------
Every record comes from the REAL product: accounts through sign-up, parent consent, invitations and teacher
approval; learning through the real /learn routes (Diagnoser -> Checker -> Planner -> Tutor -> retest); teacher
decisions through the real /progress review routes, each with a reason. Only the *answers* are simulated.

To spread that over six months the script runs the workflow on a simulated calendar (backend/clock.py): the
clock is set to each visit's date before the student answers, so timestamps are natural and the 24-hour retest
delay is honoured, never skipped. The calendar ends on the reference date (default: today, UTC midnight), so
the same reference date always produces the same history.

Passwords
---------
Demo passwords are NOT in the repository. Set ELEVIA_DEMO_PASSWORD before seeding to choose one, otherwise a
random one is generated and printed once at the end. Judges normally don't need it: student demo accounts open
with one click (ELEVIA_DEMO_MODE=1) and the teacher demo opens with the access code in ELEVIA_DEMO_TEACHER_CODE.

Safety
------
Reset deletes only users and schools recorded in `demo_registry` when this script created them, and the learning
records linked to those users. If a demo username/email is already used by an account that is NOT in the
registry (e.g. a real user), seeding stops and nothing is deleted.
"""
import os
import re
import secrets
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from backend import clock, db  # noqa: E402
from backend.accounts import schools  # noqa: E402
from backend.content import misconceptions, questions  # noqa: E402
from backend.db import now_iso  # noqa: E402
from backend.engine import correct_answer_text  # noqa: E402
from backend.main import app  # noqa: E402

SCHOOL_NAME = "ELEVIA Demonstration School"
ACADEMIC_YEAR = "2026-27"
HISTORY_DAYS = 182                                   # six months before the reference date
ADMIN, TEACHER, LEARNER = "demo.admin@example.com", "demo.teacher@example.com", "demo.learner@example.com"
# (slug, username, name, student code, age, parent name, parent email, parent permissions)
STUDENTS = [
    ("riya", "riya.demo", "Riya Sharma", "DEMO-09-001", 14, "Sunita Sharma", "demo.parent@example.com",
     ["view_progress", "view_assessments", "view_activity"]),
    ("arjun", "arjun.demo", "Arjun Patel", "DEMO-09-002", 14, "Raj Patel", "demo.parent2@example.com", ["view_progress"]),
    ("kabir", "kabir.demo", "Kabir Singh", "DEMO-09-003", 14, "Harpreet Singh", "demo.parent3@example.com", ["view_progress"]),
    ("meera", "meera.demo", "Meera Nair", "DEMO-09-004", 15, "Lakshmi Nair", "demo.parent4@example.com", ["view_progress"]),
    ("zoya", "zoya.demo", "Zoya Khan", "DEMO-09-005", 14, "Farah Khan", "demo.parent5@example.com", ["view_progress"]),
]
PARENT_SLUG = {"riya": "parent", "arjun": "parent2", "kabir": "parent3", "meera": "parent4", "zoya": "parent5"}
DEMO_EMAILS = [ADMIN, TEACHER, LEARNER] + [s[6] for s in STUDENTS]
DEMO_USERNAMES = [s[1] for s in STUDENTS]
# kept for older imports
RIYA, ARJUN = "riya.demo", "arjun.demo"
PARENT_RIYA, PARENT_ARJUN = "demo.parent@example.com", "demo.parent2@example.com"


# ---------------------------------------------------------------- helpers

def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def ok(r, what):
    if r.status_code >= 300:
        raise SystemExit(f"FAILED at {what}: {r.status_code} {r.text}")
    return r.json()


def years_ago(n):
    t = datetime.now(timezone.utc).date()
    return t.replace(year=t.year - n, day=min(t.day, 28)).isoformat()


def token_from_outbox(to_email):
    with db.transaction() as c:
        row = c.execute("SELECT body FROM email_outbox WHERE to_email=? ORDER BY id DESC LIMIT 1", (to_email,)).fetchone()
    return re.search(r"token=([A-Za-z0-9_\-]+)", row["body"]).group(1)


def _pattern(q, gap_skill):
    mis = misconceptions()
    for ans, code in q.get("patterns", {}).items():
        if mis[code]["gap_skill"] == gap_skill:
            return ans
    return None


def _plain_wrong(q):
    """A believable mistake that is NOT the misconception being checked (so it doesn't count as supporting it):
    a different option, an off-by-one number, or a verb left unchanged."""
    from fractions import Fraction
    taken = {str(q["answer"]).strip().lower(), *[str(a).strip().lower() for a in q.get("accept", [])],
             *[str(p).strip().lower() for p in q.get("patterns", {})]}
    if q["type"] == "mcq":
        bad = [o for o in q["options"] if o != q["answer"] and o not in q.get("patterns", {})]
        return bad[0] if bad else next(o for o in q["options"] if o != q["answer"])
    cands = []
    m = re.search(r'"([A-Za-z]+)"', q["prompt"])
    if m:
        cands.append(m.group(1))                               # left the word as it was
    try:
        v = Fraction(str(q["answer"]).strip())
        cands += [str(v + k) if v.denominator == 1 else f"{v.numerator + k}/{v.denominator}" for k in (1, 2, -1)]
    except (ValueError, ZeroDivisionError):
        pass
    # another real answer from the same set of questions (e.g. a different program output), then a plural slip
    pool = q.get("pool", "")
    cands += [str(o["answer"]) for o in questions().values() if o.get("pool") == pool and o["id"] != q["id"]]
    cands.append(str(q["answer"]).strip() + "s")
    return next(c for c in cands if c.strip().lower() not in taken)


def reference_instant(ref: date | None) -> datetime:
    """The moment the six-month history ends: UTC midnight at the start of the reference date."""
    ref = ref or datetime.now(timezone.utc).date()
    return datetime.combine(ref, time(0, 0), tzinfo=timezone.utc)


class Calendar:
    """Day numbers -> simulated time. Day 0 is the first day of the six-month window."""

    def __init__(self, clk: clock.SimClock, ref: datetime):
        self.clk, self.ref = clk, ref
        self.t0 = ref - timedelta(days=HISTORY_DAYS)

    def at(self, day: float, hour: int = 11, minute: int = 30) -> None:     # 11:30 UTC = 17:00 IST, after school
        when = self.t0 + timedelta(days=day, hours=hour, minutes=minute)
        if when >= self.ref:
            raise SystemExit(f"day {day} is not before the reference date")
        self.clk.set(when)

    def before_ref(self, hours: float) -> None:
        self.clk.set(self.ref - timedelta(hours=hours))


class Student:
    """Drives one student's learning through the real /learn routes. Answers are the only simulated part."""

    def __init__(self, c, cal, ident, pw):
        self.c, self.cal, self.ident, self.pw, self.h = c, cal, ident, pw, None

    def visit(self, day, hour=11, minute=30):
        self.cal.at(day, hour, minute)
        self.h = H(ok(self.c.post("/auth/login", json={"identifier": self.ident, "password": self.pw}),
                      f"login {self.ident}")["token"])
        return self

    def visit_before_ref(self, hours):
        self.cal.before_ref(hours)
        self.h = H(ok(self.c.post("/auth/login", json={"identifier": self.ident, "password": self.pw}),
                      f"login {self.ident}")["token"])
        return self

    def post(self, path, body):
        return ok(self.c.post(path, json=body, headers=self.h), f"{self.ident} {path}")

    def state(self, topic):
        return ok(self.c.get(f"/learn/state?topic={topic}", headers=self.h), f"{self.ident} state {topic}")

    def answer(self, st, choose, limit=None):
        n = 0
        for item in st["assessment"]["questions"]:
            if item["answered"]:
                continue
            if limit is not None and n >= limit:
                break
            q = questions()[item["id"]]
            out = self.post("/learn/answer", {"assessment_id": st["assessment"]["id"], "question_id": q["id"],
                                              "answer": choose(q)})
            st, n = out["state"], n + 1
            self.cal.clk.advance(seconds=55)          # a believable pace, about a minute a question
        return st

    def _gap_skill(self, st):
        with db.transaction() as conn:
            return conn.execute("SELECT skill_id FROM gaps WHERE case_id=? ORDER BY id DESC", (st["case_id"],)).fetchone()[0]

    # -- one step each, with a check that the real workflow ended where the story expects
    def checkin(self, topic, mistake_on=None, expect=None, slips=None):
        """All correct, or the misconception's answer wherever a question invites it (`slips=1`: only once, which
        is what an unclear case looks like)."""
        st = self.post("/learn/start", {"topic_id": topic})
        used = [0]

        def choose(q):
            p = _pattern(q, mistake_on)
            if p and (slips is None or used[0] < slips):
                used[0] += 1
                return p
            return correct_answer_text(q)
        st = self.answer(st, choose if mistake_on else correct_answer_text)
        want = expect or ("verify" if mistake_on else "done")
        if st["phase"] != want:
            raise SystemExit(f"{self.ident} {topic}: expected phase {want!r} after the check-in, got {st['phase']!r}")
        return st

    def double_check(self, topic, outcome):
        st = self.state(topic)
        gs = self._gap_skill(st)
        if outcome == "confirm":
            st = self.answer(st, lambda q: _pattern(q, gs) or _plain_wrong(q))
        elif outcome == "reject":
            st = self.answer(st, correct_answer_text)
        else:   # mixed: a different kind of mistake on the first new question, the other right -> inconclusive
            first = st["assessment"]["questions"][0]["id"]
            st = self.answer(st, lambda q: _plain_wrong(q) if q["id"] == first else correct_answer_text(q))
        want = {"confirm": "learning", "reject": "closed", "mixed": "teacher_review"}[outcome]
        with db.transaction() as conn:
            got = conn.execute("SELECT stage FROM cases WHERE id=?", (st["case_id"],)).fetchone()[0]
        if got != want:
            raise SystemExit(f"{self.ident} {topic}: double-check '{outcome}' left the case in {got!r}, expected {want!r}")
        return st

    def practise(self, topic, limit=None):
        st = self.answer(self.state(topic), correct_answer_text, limit)
        if limit is None and st["phase"] == "learn":
            st = self.post("/learn/practice/finish", {"assessment_id": st["assessment"]["id"]})
        return st

    def retest(self, topic, passed=True):
        st = self.post("/learn/retest/start", {"early": False, "topic_id": topic})   # only works once it's due
        return self.answer(st, correct_answer_text if passed else _plain_wrong)


class Teacher:
    """The demo teacher, using the real review routes. Every decision needs a reason and is logged."""

    def __init__(self, c, cal, pw):
        self.c, self.cal, self.pw, self.h = c, cal, pw, None

    def visit(self, day, hour=6, minute=0):          # 06:00 UTC = 11:30 IST, during school
        self.cal.at(day, hour, minute)
        self.h = H(ok(self.c.post("/auth/login", json={"identifier": TEACHER, "password": self.pw}), "teacher login")["token"])
        return self

    def decide(self, case_id, decision, reason, focus_skill=None):
        body = {"decision": decision, "reason": reason, **({"focus_skill": focus_skill} if focus_skill else {})}
        return ok(self.c.post(f"/progress/cases/{case_id}/decision", json=body, headers=self.h), "teacher decision")

    def focus(self, case_id, skill, reason):
        return ok(self.c.post(f"/progress/cases/{case_id}/focus", json={"focus_skill": skill, "reason": reason},
                              headers=self.h), "teacher focus")

    def note(self, case_id, note):
        return ok(self.c.post(f"/progress/cases/{case_id}/note", json={"note": note}, headers=self.h), "teacher note")

    def view(self, user_id):                          # opening a profile is itself logged in access_log
        return ok(self.c.get(f"/progress/students/{user_id}", headers=self.h), "teacher view")


# ---------------------------------------------------------------- accounts

def _conflicts(conn):
    marks = ",".join("?" * len(DEMO_EMAILS))
    names = ",".join("?" * len(DEMO_USERNAMES))
    rows = conn.execute(f"SELECT id FROM users WHERE email IN ({marks}) OR username IN ({names})",
                        (*DEMO_EMAILS, *DEMO_USERNAMES)).fetchall()
    reg = {r["ref_id"] for r in conn.execute("SELECT ref_id FROM demo_registry WHERE kind='user'").fetchall()}
    return [r["id"] for r in rows if r["id"] not in reg]


def _register(conn, slug, uid):
    conn.execute("INSERT INTO demo_registry (kind, ref_id, slug, created_at) VALUES ('user',?,?,?)", (uid, slug, now_iso()))


def _enrol(c, cal, pw, code, student, day):
    slug, uname, name, scode, age, pname, pmail, perms = student
    cal.at(day, 9, 0)
    s = ok(c.post("/auth/register/school-student", json={
        "full_name": name, "date_of_birth": years_ago(age), "username": uname, "password": pw,
        "parent_name": pname, "parent_email": pmail, "code": code}), f"{slug} sign-up")
    cal.at(day, 13, 0)
    p = ok(c.post("/consent/accept", json={"token": token_from_outbox(pmail), "is_parent_or_guardian": True,
                                           "is_adult": True, "agree_purposes": True, "permissions": perms,
                                           "full_name": pname, "password": pw}), f"{slug} consent")
    cal.at(day + 1, 5, 0)
    with db.transaction() as conn:
        eid = conn.execute("SELECT id FROM class_enrollments WHERE student_user_id=? AND status='pending'",
                           (s["user"]["id"],)).fetchone()["id"]
    tok = H(ok(c.post("/auth/login", json={"identifier": TEACHER, "password": pw}), "teacher login")["token"])
    ok(c.post(f"/school/enrollments/{eid}/approve", headers=tok), f"approve {slug}")
    return s["user"]["id"], p["user"]["id"]


def create_accounts(c, cal, pw) -> dict:
    cal.at(-3, 5, 0)                                  # the school is set up a few days before the window starts
    with db.transaction() as conn:
        out = schools.create_school(conn, name=SCHOOL_NAME, admin_email=ADMIN, state="Maharashtra",
                                    district="Pune", is_demo=True)
        conn.execute("INSERT INTO demo_registry (kind, ref_id, slug, created_at) VALUES ('school',?,?,?)",
                     (out["school_id"], "school", now_iso()))
    admin = ok(c.post("/invites/accept", json={"token": token_from_outbox(ADMIN), "full_name": "Kavita Menon",
                                               "password": pw}), "admin invite")
    cls = ok(c.post("/school/classes", json={"grade": 9, "division": "A", "academic_year": ACADEMIC_YEAR},
                    headers=H(admin["token"])), "class")
    ok(c.post("/school/teachers/invite", json={"email": TEACHER}, headers=H(admin["token"])), "teacher invite")
    t = ok(c.post("/invites/accept", json={"token": token_from_outbox(TEACHER), "full_name": "Ananya Mehta",
                                           "password": pw}), "teacher accept")
    ok(c.post("/school/assignments", json={"teacher_id": t["user"]["id"], "class_id": cls["id"],
                                           "can_create_codes": True}, headers=H(admin["token"])), "assign")
    code = ok(c.post("/school/codes", json={"class_id": cls["id"], "expires_days": 180, "max_uses": 40},
                     headers=H(t["token"])), "code")["code"]
    ids = {"admin": admin["user"]["id"], "teacher": t["user"]["id"]}
    joined = {"riya": 0, "arjun": 0, "kabir": 1, "meera": 2, "zoya": 96}   # Zoya joins the class in month 4
    for st in STUDENTS:
        ids[st[0]], ids[PARENT_SLUG[st[0]]] = _enrol(c, cal, pw, code, st, joined[st[0]])
        if st[0] == "arjun":
            # the fresh learner signs up early on too (no history: for a live walkthrough)
            cal.at(0, 14, 0)
            ok(c.post("/auth/register/learner", json={"full_name": "Dev Kapoor", "date_of_birth": years_ago(19),
                                                      "email": LEARNER, "password": pw, "accept_terms": True}), "learner")
            ok(c.post("/auth/verify-email", json={"token": token_from_outbox(LEARNER)}), "verify learner")
    with db.transaction() as conn:
        ids["fresh"] = conn.execute("SELECT id FROM users WHERE email=?", (LEARNER,)).fetchone()[0]
        for slug, uid in ids.items():
            _register(conn, slug, uid)
        for st in STUDENTS:
            conn.execute("INSERT INTO demo_profiles (user_id, student_code, reference_date, period_start, created_at) "
                         "VALUES (?,?,?,?,?)", (ids[st[0]], st[3], cal.ref.date().isoformat(),
                                                cal.t0.date().isoformat(), now_iso()))
    return {"code": code, "ids": ids, "class_id": cls["id"]}


# ---------------------------------------------------------------- six months of learning

def history_riya(c, cal, pw, teacher):
    """Riya Sharma, Grade 9. A believable year so far: an initial round of check-ins, targeted lessons,
    delayed retests (two of them failed first time), wider subjects, and a few things still open now."""
    r = Student(c, cal, "riya.demo", pw)
    case = {}
    # Month 1: initial assessment across subjects
    case["lin"] = r.visit(2).checkin("linear_equations", "two_step_equations")["case_id"]
    r.double_check("linear_equations", "confirm")                              # confirmed gap
    r.visit(4).checkin("forces_motion")                                        # no gap found
    r.visit(6).checkin("subject_verb_agreement", "sva_tricky")
    r.double_check("subject_verb_agreement", "reject")                         # suspected, then rejected: a slip
    case["var"] = r.visit(9).checkin("variables", "variable_tracing")["case_id"]
    r.double_check("variables", "confirm")
    case["lat"] = r.visit(12).checkin("latitude_longitude", "lat_long_meaning", slips=1)["case_id"]
    r.double_check("latitude_longitude", "mixed")                              # inconclusive -> teacher
    teacher.visit(14).view(r_id(c, "riya"))
    teacher.decide(case["lat"], "confirm", "Riya mixed up latitude and longitude again in the atlas exercise in "
                                           "class, so the gap is real.")
    r.visit(16).checkin("statistics", "finding_median")
    r.double_check("statistics", "reject")
    # Month 2: first lessons and retests
    r.visit(33).practise("linear_equations")                                   # lesson + practice -> retest booked
    r.visit(36).retest("linear_equations", passed=False)                       # failed: Planner makes a new plan
    r.visit(38).practise("variables")
    r.visit(41).retest("variables")                                            # mastered
    r.visit(44).practise("latitude_longitude")
    r.visit(47).retest("latitude_longitude")                                   # mastered
    case["apos"] = r.visit(52).checkin("apostrophes", "apostrophes_for_possession")["case_id"]
    r.double_check("apostrophes", "confirm")
    r.practise("apostrophes", limit=2)
    # Month 3: retests decide
    r.visit(64).practise("linear_equations")                                   # the new lesson
    r.visit(67).retest("linear_equations")                                     # passed second time: mastered
    r.visit(70).practise("apostrophes")
    r.visit(73).retest("apostrophes", passed=False)                            # still present
    teacher.visit(75).note(case["apos"], "Worked through its / it's and the girls' / girl's examples with Riya "
                                         "in the English period.")
    case["mat"] = r.visit(81).checkin("states_of_matter", "conservation_of_mass")["case_id"]
    r.double_check("states_of_matter", "confirm")
    r.practise("states_of_matter")
    r.visit(84).retest("states_of_matter")                                     # mastered
    # Month 4: wider subjects, teacher steps in
    case["tz"] = r.visit(95).checkin("time_zones", "longitude_and_time")["case_id"]
    r.double_check("time_zones", "confirm")
    case["cond"] = r.visit(98).checkin("conditionals", "elif_chains")["case_id"]
    r.double_check("conditionals", "confirm")
    case["pct"] = r.visit(103).checkin("percentages", "percent_of_quantity")["case_id"]
    r.double_check("percentages", "confirm")
    r.visit(106).practise("time_zones")
    r.visit(108).retest("time_zones")                                          # mastered
    r.visit(111).practise("apostrophes")
    r.visit(113).retest("apostrophes")                                         # mastered after the re-plan
    # Month 5: improvement, one more re-plan
    r.visit(126).practise("conditionals")
    r.visit(129).retest("conditionals", passed=False)
    teacher.visit(130).focus(case["cond"], "if_else", "Riya's mistakes come from reading a single if/else, so "
                                                      "start there before elif chains.")
    r.visit(131).practise("percentages")
    r.visit(133).retest("percentages")                                         # mastered
    r.visit(138).practise("conditionals")
    r.visit(141).retest("conditionals")                                        # mastered
    r.visit(144).checkin("fair_testing")                                       # no gap
    r.visit(148).checkin("parts_of_speech", "adjectives_and_adverbs")
    r.double_check("parts_of_speech", "reject")
    # Month 6: what's open now
    case["dt"] = r.visit(160).checkin("data_types", "type_conversion")["case_id"]
    r.double_check("data_types", "confirm")
    r.practise("data_types", limit=2)                                          # lesson in progress
    case["past"] = r.visit(171).checkin("past_tense", "irregular_past", slips=1)["case_id"]
    r.double_check("past_tense", "mixed")                                      # waiting for the teacher
    case["ratio"] = r.visit(176).checkin("ratio_proportion", "sharing_in_ratio")["case_id"]
    r.double_check("ratio_proportion", "confirm")
    r.visit_before_ref(2).practise("ratio_proportion")                          # retest due ~22 h after the reference
    return case


def history_arjun(c, cal, pw, teacher):
    """Arjun Patel: finding maths hard. Repeated failed retests on integers end with the Checker handing the case
    to the teacher (no unseen retest questions left)."""
    a = Student(c, cal, "arjun.demo", pw)
    case = {}
    case["int"] = a.visit(3).checkin("integers", "adding_integers")["case_id"]
    a.double_check("integers", "confirm")
    a.visit(10).checkin("variables", "variable_assignment")
    a.double_check("variables", "reject")
    a.visit(20).practise("integers")
    a.visit(23).retest("integers", passed=False)
    teacher.visit(25).note(case["int"], "Went over the number line with Arjun in class.")
    a.visit(40).practise("integers")
    a.visit(43).retest("integers", passed=False)
    a.visit(58).practise("integers")                                           # no unseen retest questions: teacher
    case["sva"] = a.visit(70).checkin("subject_verb_agreement", "sva_tricky")["case_id"]
    a.double_check("subject_verb_agreement", "confirm")
    a.visit(78).practise("subject_verb_agreement")
    a.visit(80).retest("subject_verb_agreement")                               # mastered
    a.visit(118).checkin("forces_motion", "gravity_and_weight")
    a.double_check("forces_motion", "confirm")
    a.practise("forces_motion", limit=1)
    case["frac"] = a.visit(165).post("/learn/start", {"topic_id": "fractions"})["case_id"]
    st = a.answer(a.state("fractions"), lambda q: {"DA3": "2/5"}.get(q["id"]) or correct_answer_text(q))
    a.answer(st, lambda q: {"CD-V1": "3/4"}.get(q["id"]) or correct_answer_text(q))   # mixed: waiting for teacher
    case["lin"] = a.visit(178).checkin("linear_equations", "one_step_equations")["case_id"]   # double-check not done
    return case


def history_kabir(c, cal, pw, teacher):
    """Kabir Singh: strong across the board; one real gap, closed quickly."""
    k = Student(c, cal, "kabir.demo", pw)
    k.visit(5).checkin("linear_equations")
    k.visit(8).checkin("boolean_logic")
    k.visit(15).checkin("latitude_longitude", "hemispheres")
    k.double_check("latitude_longitude", "reject")
    k.visit(60).checkin("time_zones", "east_west_time")
    k.double_check("time_zones", "confirm")
    k.practise("time_zones")
    k.visit(62).retest("time_zones")                                           # mastered
    k.visit(120).checkin("states_of_matter")
    k.visit(150).checkin("algorithms")
    return {}


def history_meera(c, cal, pw, teacher):
    """Meera Nair: steady; one teacher rejection of an unclear case, one re-plan in Computer Science."""
    m = Student(c, cal, "meera.demo", pw)
    case = {}
    m.visit(7).checkin("percentages", "percent_of_quantity")
    m.double_check("percentages", "confirm")
    m.visit(18).practise("percentages")
    m.visit(21).retest("percentages")                                          # mastered
    case["mat"] = m.visit(50).checkin("states_of_matter", "particle_model", slips=1)["case_id"]
    m.double_check("states_of_matter", "mixed")
    teacher.visit(53).decide(case["mat"], "reject", "Meera explained the particle model correctly when I asked "
                                                     "her in class; the wrong answer was a misread question.")
    m.visit(90).checkin("loops", "loop_counting")
    m.double_check("loops", "confirm")
    m.practise("loops")
    m.visit(93).retest("loops", passed=False)
    m.visit(110).practise("loops")
    m.visit(114).retest("loops")                                               # mastered after the re-plan
    m.visit(155).checkin("apostrophes", "contractions_vs_possessives")
    m.double_check("apostrophes", "confirm")
    m.practise("apostrophes")                                                  # retest booked, not yet taken
    m.visit(158).retest("apostrophes")
    return case


def history_zoya(c, cal, pw, teacher):
    """Zoya Khan: joined in month 4; two gaps found, both being worked on now."""
    z = Student(c, cal, "zoya.demo", pw)
    z.visit(100).checkin("conditionals", "if_else")
    z.double_check("conditionals", "confirm")
    z.visit(130).checkin("time_zones", "east_west_time")
    z.double_check("time_zones", "confirm")
    z.visit(170).practise("conditionals", limit=2)
    z.visit_before_ref(5).practise("time_zones")                                # retest due tomorrow
    return {}


_IDS: dict = {}


def r_id(c, slug):
    return _IDS[slug]


def create_activity(c, cal, pw) -> dict:
    teacher = Teacher(c, cal, pw)
    # stories run in date order per student; the calendar may move back between students, which is fine:
    # each record keeps the simulated time it was written at.
    out = {"riya": history_riya(c, cal, pw, teacher), "arjun": history_arjun(c, cal, pw, teacher)}
    history_kabir(c, cal, pw, teacher)
    out["meera"] = history_meera(c, cal, pw, teacher)
    history_zoya(c, cal, pw, teacher)
    return out


# ---------------------------------------------------------------- reset (demo rows only)

def delete_demo(conn) -> dict:
    users = [r["ref_id"] for r in conn.execute("SELECT ref_id FROM demo_registry WHERE kind='user'").fetchall()]
    schools_ = [r["ref_id"] for r in conn.execute(
        "SELECT r.ref_id FROM demo_registry r JOIN schools s ON s.id=r.ref_id WHERE r.kind='school' AND s.is_demo=1").fetchall()]
    U, S = users or [0], schools_ or [0]
    u, s = ",".join("?" * len(U)), ",".join("?" * len(S))
    students = [r[0] for r in conn.execute(f"SELECT student_id FROM learner_links WHERE user_id IN ({u})", U).fetchall()] or [0]
    st = ",".join("?" * len(students))
    cases = [r[0] for r in conn.execute(f"SELECT id FROM cases WHERE student_id IN ({st})", students).fetchall()] or [0]
    cs = ",".join("?" * len(cases))
    classes = [r[0] for r in conn.execute(f"SELECT id FROM classes WHERE school_id IN ({s})", S).fetchall()] or [0]
    cl = ",".join("?" * len(classes))
    E = ",".join("?" * len(DEMO_EMAILS))
    steps = [
        (f"DELETE FROM responses WHERE student_id IN ({st}) OR assessment_id IN (SELECT id FROM assessments WHERE case_id IN ({cs}))", students + cases),
        *[(f"DELETE FROM {t} WHERE case_id IN ({cs})", cases) for t in
          ("agent_runs", "teacher_overrides", "lessons", "plans", "gaps", "case_topics", "assessments")],
        (f"DELETE FROM cases WHERE id IN ({cs})", cases),
        (f"DELETE FROM skill_mastery WHERE student_id IN ({st})", students),
        (f"DELETE FROM learner_links WHERE user_id IN ({u})", U),
        (f"DELETE FROM students WHERE id IN ({st})", students),
        (f"DELETE FROM demo_profiles WHERE user_id IN ({u})", U),
        (f"DELETE FROM access_log WHERE viewer_user_id IN ({u}) OR subject_user_id IN ({u})", U + U),
        (f"DELETE FROM share_grants WHERE owner_user_id IN ({u}) OR grantee_user_id IN ({u})", U + U),
        (f"DELETE FROM consent_records WHERE student_user_id IN ({u}) OR given_by_user_id IN ({u})", U + U),
        (f"DELETE FROM parent_student_links WHERE parent_user_id IN ({u}) OR student_user_id IN ({u})", U + U),
        (f"DELETE FROM teacher_class_assignments WHERE teacher_user_id IN ({u}) OR class_id IN ({cl})", U + classes),
        (f"DELETE FROM class_enrollments WHERE student_user_id IN ({u}) OR class_id IN ({cl})", U + classes),
        (f"DELETE FROM referral_codes WHERE school_id IN ({s}) OR created_by IN ({u})", S + U),
        (f"DELETE FROM school_memberships WHERE user_id IN ({u}) OR school_id IN ({s})", U + S),
        (f"UPDATE student_profiles SET school_id=NULL WHERE school_id IN ({s}) AND user_id NOT IN ({u})", S + U),
        *[(f"DELETE FROM {t} WHERE user_id IN ({u})", U) for t in
          ("student_profiles", "parent_profiles", "teacher_profiles", "auth_sessions")],
        (f"DELETE FROM email_tokens WHERE user_id IN ({u}) OR email IN ({E})", U + DEMO_EMAILS),
        (f"DELETE FROM email_outbox WHERE to_email IN ({E})", DEMO_EMAILS),
        (f"DELETE FROM classes WHERE id IN ({cl})", classes),
        (f"DELETE FROM schools WHERE id IN ({s}) AND is_demo=1", S),
        (f"DELETE FROM users WHERE id IN ({u})", U),
        ("DELETE FROM demo_registry", []),
    ]
    for sql, args in steps:
        conn.execute(sql, args)
    return {"users": len(users), "schools": len(schools_), "cases": len([x for x in cases if x])}


# ---------------------------------------------------------------- entry points

def _password(password: str | None) -> str:
    return password or os.getenv("ELEVIA_DEMO_PASSWORD") or ("Demo-" + secrets.token_urlsafe(12))


def seed(activity: bool = True, reference_date: date | None = None, password: str | None = None) -> dict:
    pw = _password(password)
    ref = reference_instant(reference_date or _env_reference())
    with TestClient(app) as c:
        c.event_hooks["response"].append(lambda r: c.cookies.clear())   # use explicit tokens, not cookies
        with db.transaction() as conn:
            if conn.execute("SELECT 1 FROM demo_registry LIMIT 1").fetchone():
                raise SystemExit("Demo accounts already exist. Use: python scripts/demo.py reset")
            clash = _conflicts(conn)
            if clash:
                raise SystemExit(f"Stopped: demo usernames/emails are already used by non-demo accounts {clash}. "
                                 "Nothing was changed.")
        with clock.simulated(ref - timedelta(days=HISTORY_DAYS + 3)) as clk:
            cal = Calendar(clk, ref)
            acc = create_accounts(c, cal, pw)
            _IDS.clear()
            _IDS.update(acc["ids"])
            act = create_activity(c, cal, pw) if activity else {}
    return {"class_code": acc["code"], "reference_date": ref.date().isoformat(),
            "period_start": (ref - timedelta(days=HISTORY_DAYS)).date().isoformat(), "cases": act, "password": pw}


def _env_reference() -> date | None:
    v = os.getenv("ELEVIA_DEMO_REFERENCE_DATE")
    return date.fromisoformat(v) if v else None


def reset(reference_date: date | None = None, password: str | None = None) -> dict:
    with db.transaction() as conn:
        gone = delete_demo(conn)
    return {"deleted": gone, **seed(reference_date=reference_date, password=password)}


def status() -> list:
    with db.transaction() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT r.slug, u.full_name, u.role, u.status, p.student_code, p.reference_date FROM demo_registry r "
            "JOIN users u ON u.id=r.ref_id LEFT JOIN demo_profiles p ON p.user_id=u.id "
            "WHERE r.kind='user' ORDER BY r.slug").fetchall()]


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    ref = None
    if "--reference-date" in args:
        ref = date.fromisoformat(args[args.index("--reference-date") + 1])
    if cmd in ("seed", "reset"):
        out = seed("--no-activity" not in args, reference_date=ref) if cmd == "seed" else reset(reference_date=ref)
        pw = out.pop("password")
        print(f"Demo {'created' if cmd == 'seed' else 'reset'}: six months of history from {out['period_start']} "
              f"to {out['reference_date']}.")
        print("Demo logins (fictional accounts; keep this password private, it is not stored anywhere else):")
        for who in ("riya.demo", "arjun.demo", "kabir.demo", "meera.demo", "zoya.demo", TEACHER, ADMIN, LEARNER,
                    PARENT_RIYA):
            print(f"  {who}")
        print(f"  password: {pw}")
        print("For judges: set ELEVIA_DEMO_MODE=1 (one-click student demo) and ELEVIA_DEMO_TEACHER_CODE "
              "(teacher demo access code) on the server.")
    elif cmd == "status":
        rows = status()
        print("\n".join(f"{r['slug']:8} {r['full_name']:15} {r['role']:12} {r['status']:8} "
                        f"{r['student_code'] or '':12} {r['reference_date'] or ''}" for r in rows) or "No demo accounts.")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
