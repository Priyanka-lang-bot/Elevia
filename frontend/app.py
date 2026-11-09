"""ELEVIA Streamlit frontend.

Run:  streamlit run frontend/app.py
All data and decisions come from the FastAPI backend (frontend/api.py).
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

import os

import streamlit as st

# On Streamlit Community Cloud, settings live in "Secrets". Copy them into environment
# variables before the backend client is imported. Locally (no secrets file) this is skipped.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, (str, int, float, bool)):
            os.environ.setdefault(_k, str(_v))
except Exception:
    pass

import api  # noqa: E402

st.set_page_config(page_title="ELEVIA · Closing learning gaps", page_icon="📘", layout="wide",
                   initial_sidebar_state="auto")
st.markdown(f"<style>{(Path(__file__).parent / 'style.css').read_text()}</style>", unsafe_allow_html=True)

PAGES = ["Home", "Student Dashboard", "Maths Practice", "Agent Activity", "Learning Room", "Progress",
         "Teacher Dashboard"]
STATUS_TEXT = {"not_assessed": "Not assessed", "needs_practice": "Needs practice", "developing": "Developing",
               "mastered": "Mastered"}
MODE_TEXT = {"rules": "rule-based", "rules+llm": "rules + AI wording", "llm": "AI model", "template": "template (no AI)",
             "pending": "running"}

ss = st.session_state
ss.setdefault("page", "Home")
ss.setdefault("student_id", None)
ss.setdefault("teacher_pin", "")
ss.setdefault("hints", {})
ss.setdefault("feedback", None)


def go(page: str) -> None:
    ss["_nav"] = page


if "_nav" in ss:  # apply navigation before the sidebar radio is drawn
    ss.page = ss.pop("_nav")


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def badge(text: str, kind: str) -> str:
    return f'<span class="ev-badge b-{esc(kind)}">{esc(text)}</span>'


def card(body: str, extra_class: str = "") -> None:
    st.markdown(f'<div class="ev-card {extra_class}">{body}</div>', unsafe_allow_html=True)


def when(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso).astimezone()
        return dt.strftime("%d %b %Y, %H:%M")
    except ValueError:
        return iso


def call(fn, *args, **kwargs):
    """Run an API call; show a friendly error and return None on failure."""
    try:
        return fn(*args, **kwargs)
    except api.ApiError as e:
        st.error(str(e))
        return None


# ---------------------------------------------------------------- sidebar

health = None
try:
    health = api.get("/health")
except api.ApiError as e:
    st.sidebar.error(str(e))

with st.sidebar:
    st.markdown("## ELEVIA")
    st.caption("Closing learning gaps with agentic AI")
    st.radio("Go to", PAGES, key="page", label_visibility="collapsed")
    st.divider()
    students = call(api.get, "/students") if health else None
    if students:
        options = {s["id"]: f"{s['display_name']} · Grade {s['grade']}" + ("  (sample)" if s["is_sample"] else "")
                   for s in students}
        ids = list(options)
        idx = ids.index(ss.student_id) if ss.student_id in ids else 0
        ss.student_id = st.selectbox("Student", ids, index=idx, format_func=lambda i: options[i])
    if health:
        llm = health["llm"]
        if llm["mode"] == "llm":
            st.caption(f"AI model: {llm['provider']} · {llm['model']}")
        else:
            st.caption(f"⚠️ Demo mode: no AI model connected ({llm.get('reason')}). "
                       "Agents use rule-based logic and template wording, labelled as such.")

if health is None:
    st.title("ELEVIA")
    st.warning("The backend isn't reachable, so nothing can be loaded. Start it with "
               "`uvicorn backend.main:app --port 8000` and refresh.")
    st.stop()


def overview():
    if not ss.student_id:
        return None
    return call(api.get, f"/students/{ss.student_id}/overview")


def no_student():
    st.info("Pick a student in the sidebar, or create one on the Student Dashboard.")
    st.button("Go to Student Dashboard", on_click=go, args=("Student Dashboard",))


# ---------------------------------------------------------------- icons

ICONS = {
    "Diagnoser": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke-width="1.6"><circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/></svg>',
    "Checker": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke-width="1.6"><rect x="4" y="3.5" width="16" height="17" rx="2"/><path d="M8 12l3 3 5-6"/></svg>',
    "Planner": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke-width="1.6"><circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 18h5a3 3 0 0 0 3-3V8"/></svg>',
    "Tutor": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke-width="1.6"><path d="M4 5h7a2 2 0 0 1 2 2v12a2 2 0 0 0-2-2H4z"/><path d="M20 5h-7a2 2 0 0 0-2 2v12a2 2 0 0 1 2-2h7z"/></svg>',
}
AGENT_DESC = {
    "Diagnoser": "Looks at wrong answers and suggests a possible gap with a confidence level. A hypothesis only.",
    "Checker": "Asks new questions to test the suspicion, and later retests. Owns all assessment.",
    "Planner": "Acts only on a verified gap. Picks the earlier skill to learn using the skill map.",
    "Tutor": "Teaches in small steps with worked examples, hints and practice. Never grades itself.",
}


# ======================================================================
# pages
# ======================================================================

def page_home():
    st.markdown(
        '<div class="ev-hero"><div class="ev-tag">Personalised maths learning</div><h1>ELEVIA</h1>'
        '<p class="ev-lead">Marks tell a student <b>what</b> they got wrong. ELEVIA works out <b>why</b>: '
        'it suggests the underlying gap, checks it with new questions, plans the earlier skill to learn, '
        'teaches it, and retests later to see whether it stuck.</p></div>', unsafe_allow_html=True)
    st.write("")
    c1, c2, _ = st.columns([1.2, 1.2, 3])
    c1.button("Start learning", type="primary", on_click=go, args=("Student Dashboard",), width="stretch")
    c2.button("Teacher dashboard", on_click=go, args=("Teacher Dashboard",), width="stretch")

    st.markdown("### Four agents, one shared learning record")
    flow = "".join(
        f'<div class="ev-agent"><span class="num">{i}</span> {ICONS[a]}<h4>{a}</h4><p>{AGENT_DESC[a]}</p></div>'
        for i, a in enumerate(["Diagnoser", "Checker", "Planner", "Tutor"], 1))
    st.markdown(f'<div class="ev-flow">{flow}</div>', unsafe_allow_html=True)
    st.caption("Then the Checker retests later, ideally the next day, to measure improvement. "
               "Teachers can review and override every decision.")

    st.markdown("### Example: one student, one fractions check-in")
    steps = [
        ("Student scores 3/5", "Writes 1/2 + 1/3 = 2/5 and 1/4 + 2/3 = 3/7."),
        ("Diagnoser suspects a gap", "Adds tops and bottoms separately → possible gap in common denominators (high confidence)."),
        ("Checker verifies", "Two new questions. The same mistake appears again, so the gap is confirmed."),
        ("Planner + Tutor", "Focus: finding common denominators. Small steps, worked examples, hinted practice."),
        ("Checker retests later", "New questions after a delay. Improvement is measured, not assumed."),
    ]
    cols = st.columns(len(steps))
    for col, (t, d) in zip(cols, steps):
        col.markdown(f'<div class="ev-card ev-margin"><h4>{esc(t)}</h4><p class="ev-muted">{esc(d)}</p></div>',
                     unsafe_allow_html=True)

    st.markdown("### What this version covers")
    st.markdown(
        "- **Mathematics: fractions**, with a curriculum-based map of 8 skills and a skill-tagged question bank.\n"
        "- Every answer is checked with **exact fraction arithmetic** in Python, never by an AI model.\n"
        "- A suspected gap **cannot change a learning plan** until the Checker or a teacher verifies it.")
    st.caption("ELEVIA identifies possible academic knowledge gaps from a student's answers. It is not a clinical "
               "or psychological assessment and does not diagnose learning difficulties.")


def page_student_dashboard():
    st.title("Student dashboard")
    with st.expander("➕ Add a student"):
        with st.form("new_student", clear_on_submit=True):
            name = st.text_input("First name or nickname", max_chars=40,
                                 help="Avoid full names: keep student data private.")
            grade = st.number_input("Grade", min_value=3, max_value=8, value=5, step=1)
            if st.form_submit_button("Create student", type="primary"):
                if not name.strip():
                    st.error("Please enter a name.")
                else:
                    s = call(api.post, "/students", {"display_name": name.strip(), "grade": int(grade)})
                    if s:
                        ss.student_id = s["id"]
                        st.rerun()

    ov = overview()
    if not ov:
        no_student()
        return
    s = ov["student"]
    sample = badge("Sample data", "sample") if s["is_sample"] else ""
    st.markdown(f"#### {esc(s['display_name'])} · Grade {s['grade']} {sample}", unsafe_allow_html=True)
    if s["is_sample"]:
        st.caption("Sample student for demonstration. Their records were produced by running scripted answers "
                   "through the real workflow.")

    rec = ov["recommended_next"]
    with st.container():
        c1, c2 = st.columns([3, 1.2])
        txt = esc(rec["label"])
        if rec.get("available_at"):
            txt += f' <span class="ev-muted">(unlocks {esc(when(rec["available_at"]))})</span>'
        c1.markdown(f'<div class="ev-note"><b>Recommended next:</b> {txt}</div>', unsafe_allow_html=True)
        target = {"start": "Maths Practice", "practice": "Maths Practice", "retest": "Maths Practice",
                  "learn": "Learning Room", "wait": "Agent Activity"}[rec["action"]]
        if rec["action"] == "start":
            if c2.button("Start check-in", type="primary", width="stretch"):
                if call(api.post, f"/students/{s['id']}/cases"):
                    ss.feedback = None
                    go("Maths Practice")
                    st.rerun()
        else:
            c2.button("Open", type="primary", width="stretch", on_click=go, args=(target,))

    tot = ov["totals"]
    attempted = sum(v["attempted"] for k, v in tot.items() if k != "practice")
    correct = sum(v["correct"] for k, v in tot.items() if k != "practice")
    skills = ov["skills"]
    m = st.columns(4)
    m[0].metric("Assessment questions", attempted)
    m[1].metric("Correct", correct)
    m[2].metric("Skills mastered", sum(1 for x in skills if x["status"] == "mastered"))
    m[3].metric("Needing practice", sum(1 for x in skills if x["status"] == "needs_practice"))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Topics completed")
        done = [x for x in skills if x["status"] in ("mastered", "developing")]
        if done:
            st.markdown("".join(f'<span class="ev-skill">{badge(STATUS_TEXT[x["status"]], x["status"])}{esc(x["name"])}</span>'
                                for x in done), unsafe_allow_html=True)
        else:
            st.caption("Nothing yet.")
    with c2:
        st.markdown("##### Topics needing improvement")
        need = [x for x in skills if x["status"] == "needs_practice"]
        if need:
            st.markdown("".join(f'<span class="ev-skill">{badge("Needs practice", "needs_practice")}{esc(x["name"])}</span>'
                                for x in need), unsafe_allow_html=True)
        else:
            st.caption("None recorded.")

    st.markdown("##### Recent assessment results")
    if ov["assessments"]:
        st.dataframe([{"When": when(a["completed_at"]), "Type": a["kind"].capitalize(),
                       "Score": f"{a['correct'] or 0}/{a['total']}", "Case": a["case_id"]}
                      for a in ov["assessments"][:8]], hide_index=True, width="stretch")
    else:
        st.caption("No completed assessments yet.")


def _question_form(assessment: dict, practice: bool = False):
    pending = [q for q in assessment["questions"] if not q["answered"]]
    if not pending:
        return
    q = pending[0]
    n = assessment["answered"] + 1
    st.markdown(f'<span class="ev-muted">Question {n} of {assessment["total"]} · {esc(q["skill_name"])}</span>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="ev-q">{esc(q["prompt"])}</div>', unsafe_allow_html=True)

    hint_key = f"{assessment['id']}:{q['id']}"
    if practice:
        level = ss.hints.get(hint_key, 0)
        for lv in range(1, level + 1):
            h = call(api.get, f"/assessments/{assessment['id']}/hint", {"question_id": q["id"], "level": lv})
            if h:
                st.markdown(f'<div class="ev-step">💡 Hint {lv}: {esc(h["hint"])}</div>', unsafe_allow_html=True)
        if level < q.get("hint_count", 0):
            if st.button(f"Show hint {level + 1} of {q['hint_count']}", key=f"hint-{hint_key}"):
                ss.hints[hint_key] = level + 1
                st.rerun()

    with st.form(f"q-{assessment['id']}-{q['id']}", clear_on_submit=True):
        if q["input_kind"] == "choice":
            ans = st.radio("Your answer", q["choices"], index=None, horizontal=True)
        elif q["input_kind"] == "integer":
            ans = st.text_input("Your answer (whole number)", max_chars=6, placeholder="e.g. 12")
        else:
            ans = st.text_input("Your answer", max_chars=12, placeholder="e.g. 5/6 or 1 1/2")
        submitted = st.form_submit_button("Submit answer", type="primary")
    if submitted:
        if not ans or not str(ans).strip():
            st.error("Please enter an answer first.")
            return
        r = call(api.post, f"/assessments/{assessment['id']}/answers",
                 {"question_id": q["id"], "answer": str(ans), "hints_used": ss.hints.get(hint_key, 0)})
        if r is None:
            return
        if not r.get("accepted"):
            st.error(r.get("error"))
            return
        ss.feedback = {"kind": assessment["kind"], "prompt": q["prompt"], "answer": str(ans), **{k: r.get(k) for k in
                       ("is_correct", "message", "notes", "expected", "solution", "assessment_completed")}}
        st.rerun()


def _show_feedback(practice: bool):
    fb = ss.feedback
    if not fb or (fb.get("kind") == "practice") != practice:
        return
    if fb["is_correct"]:
        st.success(f"✓ {fb['prompt'].replace(' = ?', '')}: {fb['answer']} is correct.")
    elif practice:
        st.error(f"✗ {fb['prompt'].replace(' = ?', '')}: {fb['answer']} isn't right. The answer is {fb.get('expected')}.")
    else:
        st.warning(f"{fb['prompt'].replace(' = ?', '')}: {fb.get('message')}")
    for n in fb.get("notes") or []:
        st.caption(n)
    if practice and fb.get("solution"):
        with st.expander("See the worked solution", expanded=not fb["is_correct"]):
            for s in fb["solution"]:
                st.markdown(f'<div class="ev-step">{esc(s)}</div>', unsafe_allow_html=True)


def page_practice():
    st.title("Maths practice")
    ov = overview()
    if not ov:
        no_student()
        return
    case = ov["active_case"]
    if case is None:
        st.markdown("Start a short fractions check-in: **5 questions**. ELEVIA uses your answers to look for any "
                    "gaps underneath your mistakes.")
        if st.button("Start check-in", type="primary"):
            if call(api.post, f"/students/{ov['student']['id']}/cases"):
                ss.feedback = None
                st.rerun()
        _show_feedback(False)
        return

    stage = case["stage"]
    a = case["open_assessment"]
    _show_feedback(False)

    if stage == "diagnostic":
        st.markdown('<div class="ev-note">Check-in: answer each question. You\'ll see whether each answer is right, '
                    'but ELEVIA waits until it has all your answers before thinking about why.</div>',
                    unsafe_allow_html=True)
        _question_form(a)
    elif stage == "verification":
        st.markdown(f'<div class="ev-note">🔍 <b>ELEVIA is investigating.</b> The Diagnoser noticed something in your '
                    f'answers. Before deciding anything, the Checker wants you to try {a["total"]} new question(s).'
                    '</div>', unsafe_allow_html=True)
        _question_form(a)
    elif stage == "retest":
        st.markdown('<div class="ev-note">📋 <b>Retest by the Checker.</b> New questions on what you learned. '
                    'This is what decides your progress.</div>', unsafe_allow_html=True)
        _question_form(a)
    elif stage == "retest_pending":
        retest = a
        unlock = retest["available_at"]
        ready = unlock <= datetime.now(timezone.utc).isoformat()
        st.markdown(f'<div class="ev-note">Nice work in the learning room. The Checker has scheduled your retest for '
                    f'<b>{esc(when(unlock))}</b>. A delay shows whether the learning stuck.</div>',
                    unsafe_allow_html=True)
        st.write("")
        if ready:
            if st.button("Start retest", type="primary"):
                if call(api.post, f"/cases/{case['id']}/retest", {"early": False}):
                    ss.feedback = None
                    st.rerun()
        else:
            st.button("Start retest", disabled=True, help="Not unlocked yet")
            if health.get("allow_early_retest"):
                if st.button("Demo override: start retest now"):
                    if call(api.post, f"/cases/{case['id']}/retest", {"early": True}):
                        ss.feedback = None
                        st.rerun()
                st.caption("For demonstrations only. Skipping the wait is recorded in the agent log.")
    elif stage == "learning":
        st.info("Your plan is ready. Head to the learning room.")
        st.button("Open learning room", type="primary", on_click=go, args=("Learning Room",))
    elif stage == "teacher_review":
        st.info("Your teacher is looking at your answers before ELEVIA changes your plan. Check back soon.")

    if ss.feedback and ss.feedback.get("assessment_completed"):
        st.button("See what the agents found", on_click=go, args=("Agent Activity",))


def _run_summary(run: dict) -> str:
    o = run.get("output") or {}
    step = run["step"]
    if run["status"] == "skipped":
        return esc(o.get("reason", "Skipped"))
    if run["status"] == "failed":
        return f"Failed: {esc(run.get('error'))}"
    if run["status"] == "running":
        return "Running…"
    if step == "diagnose":
        if not o.get("has_gap"):
            return esc(o.get("summary"))
        p = o["primary"]
        return (f"{badge('SUSPECTED', 'suspected')} Possible gap: <b>{esc(p['skill_name'])}</b> · "
                f"confidence {esc(p['confidence_label'])} ({p['confidence']:.2f})<br>{esc(p['hypothesis'])}")
    if step == "select_verification":
        return "Chose new questions: " + ", ".join(
            f"<code>{esc(r['question_id'])}</code> ({esc(r['why'].lower())})" for r in o.get("rationale", []))
    if step == "evaluate_verification":
        return f"{badge(o['verdict'].upper(), o['verdict'])} {esc(o['reason'])}"
    if step == "plan":
        path = " → ".join(esc(p["skill_name"]) for p in o.get("path", []))
        return f"Focus: <b>{esc(o['focus_skill_name'])}</b><br>Path: {path}<br>{esc(o['rationale'])}"
    if step == "teach":
        return (f"Lesson: <b>{esc(o['title'])}</b> · {len(o.get('worked_examples', []))} worked examples · "
                f"{len(o.get('practice', []))} practice questions")
    if step == "schedule_retest":
        return f"Retest scheduled for {esc(when(o.get('available_at')))} ({o.get('delay_hours')} h after practice)."
    if step == "evaluate_retest":
        sc = o["score"]
        imp = o.get("improvement_points")
        imp_txt = f" Change vs verification: {imp:+d} points." if imp is not None else ""
        return f"{badge('PASSED' if o['passed'] else 'NOT YET', 'resolved' if o['passed'] else 'still_present')} " \
               f"{sc['correct']}/{sc['total']} correct.{esc(imp_txt)}"
    return esc(json.dumps(o)[:200])


def render_case(case: dict, teacher: bool = False):
    gap = case.get("gap")
    st.markdown(f"**Case #{case['id']}** · {esc(case['stage_label'])}" +
                (f" · <span class='ev-muted'>{esc(case['closed_reason'])}</span>" if case.get("closed_reason") else ""),
                unsafe_allow_html=True)
    if gap:
        verified = gap["status"] in ("confirmed", "resolved", "still_present")
        state = {"suspected": "Suspected, not yet verified", "confirmed": "Verified",
                 "rejected": "Not supported by the evidence", "inconclusive": "Inconclusive, needs a teacher",
                 "resolved": "Verified, now resolved", "still_present": "Verified, still present"}[gap["status"]]
        who = f" by {esc(gap['verified_by'])}" if gap.get("verified_by") and verified else ""
        card(f"<h4>Learning gap: {esc(gap['skill_name'])} {badge(gap['status'].replace('_', ' ').upper(), gap['status'])}</h4>"
             f"<p class='ev-muted'>{esc(state)}{who} · Diagnoser confidence: {esc(gap['confidence_label'])} "
             f"({gap['confidence']:.2f})</p><p>{esc(gap['hypothesis'])}</p>", "ev-margin")

    runs = case.get("agent_runs", [])
    if not runs:
        st.caption("No agent has run yet. Agents start when the check-in is finished.")
    for r in runs:
        icon = ICONS.get(r["agent"], "")
        mode = MODE_TEXT.get(r["mode"], r["mode"])
        card(f"<h4>{icon} {esc(r['agent'])} · <span class='ev-muted'>{esc(r['step'].replace('_', ' '))}</span> "
             f"{badge(r['status'], r['status'])}{badge(mode, 'mode')}</h4>"
             f"<p>{_run_summary(r)}</p><p class='ev-muted'>{esc(when(r['started_at']))}</p>")
        if teacher or st.session_state.get("show_raw"):
            with st.expander(f"Structured data exchanged ({r['agent']} · {r['step']})"):
                st.json({"input": r["input"], "output": r.get("output"), "error": r.get("error")}, expanded=False)
        llm_note = (r.get("output") or {}).get("llm_note")
        if llm_note:
            st.caption(llm_note)


def page_agents():
    st.title("Agent activity")
    st.caption("This is the actual execution log from the backend: what each agent received, what it decided, "
               "and whether it used rules, an AI model, or templates.")
    ov = overview()
    if not ov:
        no_student()
        return
    if not ov["cases"]:
        st.info("No activity yet. Start a check-in first.")
        st.button("Go to practice", on_click=go, args=("Maths Practice",))
        return
    ids = [c["id"] for c in ov["cases"]]
    cid = st.selectbox("Learning case", ids, format_func=lambda i: next(
        f"Case #{c['id']} · {c['stage_label']} · started {when(c['created_at'])}" for c in ov["cases"] if c["id"] == i))
    st.toggle("Show the structured data each agent exchanged", key="show_raw")
    case = call(api.get, f"/cases/{cid}")
    if case:
        render_case(case)
        if case["stage"] == "learning":
            st.button("Open learning room", type="primary", on_click=go, args=("Learning Room",))
        elif case["stage"] in ("verification", "retest", "retest_pending"):
            st.button("Continue in practice", type="primary", on_click=go, args=("Maths Practice",))


def page_learning():
    st.title("Learning room")
    ov = overview()
    if not ov:
        no_student()
        return
    case = ov["active_case"]
    lesson_row = case.get("lesson") if case else None
    if not case or case["stage"] != "learning" or not lesson_row:
        if case and case["stage"] == "retest_pending":
            st.info("You've finished practising. Your retest is waiting in Maths Practice.")
            st.button("Go to retest", on_click=go, args=("Maths Practice",))
        else:
            st.info("No lesson right now. A lesson appears once the Checker has verified a gap and the Planner "
                    "has chosen what to learn.")
        return
    L = lesson_row["content"]
    src = badge("Written by AI model, checked" if L["source"] == "llm" else "Template lesson (no AI)", "mode")
    st.markdown(f"### {esc(L['title'])} {src}", unsafe_allow_html=True)
    plan = case.get("plan") or {}
    if plan:
        path = " → ".join(esc(p["skill_name"]) for p in plan["path"]["path"])
        st.markdown(f'<span class="ev-muted">Your path: {path}</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="ev-note">{esc(L["personal_note"])}</div>', unsafe_allow_html=True)
    st.write("")
    st.markdown(f"**Big idea.** {esc(L['big_idea'])}")
    st.markdown("**Step by step**")
    for i, s in enumerate(L["steps"], 1):
        st.markdown(f'<div class="ev-step"><b>{i}.</b> {esc(s)}</div>', unsafe_allow_html=True)
    st.caption(L["sense_check"])

    st.markdown("**Worked examples**")
    cols = st.columns(len(L["worked_examples"]))
    for col, ex in zip(cols, L["worked_examples"]):
        with col:
            body = "".join(f'<div class="ev-step">{esc(s)}</div>' for s in ex["steps"])
            card(f"<h4>{esc(ex['prompt'])}</h4>{body}<p><b>Answer: {esc(ex['answer'])}</b></p>")

    st.markdown("### Practice")
    st.caption(L["grading_note"])
    a = case["open_assessment"]
    if not a or a["kind"] != "practice":
        st.info("Practice finished.")
        return
    _show_feedback(True)
    _question_form(a, practice=True)
    done = a["answered"]
    if done < a["total"]:
        st.progress(done / a["total"], text=f"{done} of {a['total']} practice questions tried")
        if done >= 2 and st.button("I'm ready: finish practice and schedule my retest"):
            if call(api.post, f"/assessments/{a['id']}/finish"):
                ss.feedback = None
                st.rerun()


def page_progress():
    st.title("Progress")
    ov = overview()
    if not ov:
        no_student()
        return
    tot = ov["totals"]
    att = sum(v["attempted"] for k, v in tot.items() if k != "practice")
    cor = sum(v["correct"] for k, v in tot.items() if k != "practice")
    pr = tot.get("practice", {"attempted": 0, "correct": 0})
    m = st.columns(4)
    m[0].metric("Assessment questions", att)
    m[1].metric("Correct", cor)
    m[2].metric("Incorrect", att - cor)
    m[3].metric("Practice tried", pr["attempted"], help="Practice is tracked but doesn't count toward mastery.")

    st.markdown("##### Skills")
    rows = []
    for s in ov["skills"]:
        rows.append({"Skill": s["name"], "Grade": s["grade"], "Status": STATUS_TEXT[s["status"]],
                     "Assessed correct": f"{s['correct']}/{s['attempts']}" if s["attempts"] else "—"})
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Mastered = passed a delayed retest with new questions. Developing = correct so far, not yet retested.")

    st.markdown("##### Improvement between assessments")
    if ov["improvements"]:
        for imp in ov["improvements"]:
            c = st.columns(3)
            c[0].metric(f"Verification · {imp['skill_name']}", f"{imp['verification_rate'] * 100:.0f}%")
            c[1].metric("Retest", f"{imp['retest_rate'] * 100:.0f}%", f"{imp['change_points']:+d} pts")
            c[2].metric("Case", f"#{imp['case_id']}")
        st.caption("Calculated from this student's actual answers: verification questions vs the later retest.")
    else:
        st.caption("No retest completed yet, so there's no improvement to show.")

    if ov["assessments"]:
        st.markdown("##### Assessment scores over time")
        data = [{"Assessment": f"{i + 1}. {a['kind']}", "Score %": round(100 * (a["correct"] or 0) / a["total"])}
                for i, a in enumerate(reversed(ov["assessments"]))]
        st.bar_chart(data, x="Assessment", y="Score %", color="#3d6fb6")

    st.markdown("##### Learning history")
    if ov["history"]:
        st.dataframe([{"When": when(h["created_at"]), "Activity": h["kind"].capitalize(), "Question": h["prompt"],
                       "Answer": h["answer_raw"], "Result": "✓" if h["is_correct"] else "✗"} for h in ov["history"]],
                     hide_index=True, width="stretch")
    else:
        st.caption("No answers yet.")


def page_teacher():
    st.title("Teacher dashboard")
    if health.get("demo_teacher_pin"):
        st.caption("⚠️ Demo PIN in use (2468). Set TEACHER_PIN in .env before sharing this site.")
    if not ss.teacher_pin:
        with st.form("pin"):
            pin = st.text_input("Teacher PIN", type="password")
            if st.form_submit_button("Unlock", type="primary"):
                if call(api.get, "/teacher/overview", pin=pin) is not None:
                    ss.teacher_pin = pin
                    st.rerun()
        return
    pin = ss.teacher_pin
    if st.button("Lock teacher view"):
        ss.teacher_pin = ""
        st.rerun()

    rows = call(api.get, "/teacher/overview", pin=pin)
    if rows is None:
        ss.teacher_pin = ""
        return
    review = [r for r in rows if r["needs_review"]]
    if review:
        st.warning(f"{len(review)} student(s) need your review: " +
                   ", ".join(r["student"]["display_name"] for r in review))
    st.dataframe([{"Student": r["student"]["display_name"] + (" (sample)" if r["student"]["is_sample"] else ""),
                   "Grade": r["student"]["grade"], "Stage": r["stage_label"], "Gap": r["gap_skill"] or "—",
                   "Gap status": r["gap_status"] or "—", "Confidence": r["confidence_label"] or "—",
                   "Answered": r["attempted"], "Correct": r["correct"]} for r in rows],
                 hide_index=True, width="stretch")

    sid = st.selectbox("Open student record", [r["student"]["id"] for r in rows],
                       format_func=lambda i: next(r["student"]["display_name"] for r in rows if r["student"]["id"] == i))
    ov = call(api.get, f"/teacher/students/{sid}", pin=pin)
    if not ov:
        return
    tabs = st.tabs(["Current case & overrides", "Gaps", "Assessment history", "Progress"])

    with tabs[0]:
        if not ov["cases"]:
            st.caption("No activity yet.")
        else:
            cid = st.selectbox("Case", [c["id"] for c in ov["cases"]],
                               format_func=lambda i: next(f"#{c['id']} · {c['stage_label']}" for c in ov["cases"] if c["id"] == i))
            case = call(api.get, f"/teacher/cases/{cid}", pin=pin)
            if case:
                _teacher_actions(case, pin)
                st.markdown("#### Agent recommendations")
                render_case(case, teacher=True)

    with tabs[1]:
        if ov["gaps"]:
            st.dataframe([{"Case": g["case_id"], "Skill": g["skill_name"], "Status": g["status"],
                           "Confidence": f"{g['confidence_label']} ({g['confidence']:.2f})",
                           "Verified by": g["verified_by"] or "—", "Hypothesis": g["hypothesis"]} for g in ov["gaps"]],
                         hide_index=True, width="stretch")
        else:
            st.caption("No gaps recorded.")
    with tabs[2]:
        if ov["history"]:
            st.dataframe([{"When": when(h["created_at"]), "Type": h["kind"], "Question": h["prompt"],
                           "Answer": h["answer_raw"], "Correct": bool(h["is_correct"]),
                           "Mistake pattern": h["pattern"] or ""} for h in ov["history"]],
                         hide_index=True, width="stretch")
        else:
            st.caption("No answers yet.")
    with tabs[3]:
        st.dataframe([{"Skill": s["name"], "Status": STATUS_TEXT[s["status"]], "Correct/attempts":
                       f"{s['correct']}/{s['attempts']}"} for s in ov["skills"]], hide_index=True,
                     width="stretch")
        for imp in ov["improvements"]:
            st.markdown(f"Case #{imp['case_id']} · {esc(imp['skill_name'])}: verification "
                        f"{imp['verification_rate'] * 100:.0f}% → retest {imp['retest_rate'] * 100:.0f}% "
                        f"({imp['change_points']:+d} pts)")


def _teacher_actions(case: dict, pin: str):
    skills = call(api.get, "/skills") or {"teachable": [], "skills": []}
    names = {s["id"]: s["name"] for s in skills["skills"]}
    teachable = skills["teachable"]
    gap = case.get("gap")
    st.markdown("#### Review and override")
    if not gap:
        st.caption("No gap to review in this case.")
    elif case["stage"] in ("diagnostic", "verification"):
        st.caption("The Checker hasn't finished verifying yet. Overrides open once verification is done.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            with st.form(f"decide-{case['id']}"):
                st.markdown("**Confirm or reject the gap**")
                decision = st.radio("Decision", ["confirm", "reject"], horizontal=True,
                                    format_func=lambda d: "Confirm gap" if d == "confirm" else "Reject gap")
                focus = st.selectbox("Focus skill if confirming (optional)", [""] + teachable,
                                     format_func=lambda s: "Let the Planner decide" if not s else names.get(s, s))
                tname = st.text_input("Your name", max_chars=60)
                reason = st.text_area("Reason (required)", max_chars=500)
                if st.form_submit_button("Save decision", type="primary"):
                    if call(api.post, f"/teacher/cases/{case['id']}/gap-decision",
                            {"decision": decision, "teacher_name": tname, "reason": reason,
                             "focus_skill": focus or None}, pin=pin):
                        st.success("Saved.")
                        st.rerun()
        with c2:
            with st.form(f"focus-{case['id']}"):
                st.markdown("**Change the learning focus**")
                cur = (case.get("plan") or {}).get("focus_skill")
                st.caption(f"Current focus: {names.get(cur, '—')}")
                nf = st.selectbox("New focus skill", teachable, format_func=lambda s: names.get(s, s))
                tname2 = st.text_input("Your name ", max_chars=60)
                reason2 = st.text_area("Reason (required) ", max_chars=500)
                if st.form_submit_button("Change focus"):
                    if call(api.post, f"/teacher/cases/{case['id']}/focus",
                            {"focus_skill": nf, "teacher_name": tname2, "reason": reason2}, pin=pin):
                        st.success("Focus changed. The Planner and Tutor re-ran with your choice.")
                        st.rerun()
    with st.form(f"note-{case['id']}", clear_on_submit=True):
        st.markdown("**Add a note**")
        tn = st.text_input("Your name  ", max_chars=60)
        note = st.text_area("Note", max_chars=500)
        if st.form_submit_button("Add note"):
            if call(api.post, f"/teacher/cases/{case['id']}/notes", {"teacher_name": tn, "note": note}, pin=pin):
                st.rerun()
    if case.get("overrides"):
        st.markdown("**Teacher log**")
        st.dataframe([{"When": when(o["created_at"]), "Teacher": o["teacher_name"], "Action": o["action"],
                       "From": o["old_value"] or "", "To": o["new_value"] or "", "Reason / note": o["reason"]}
                      for o in case["overrides"]], hide_index=True, width="stretch")


ROUTES = {
    "Home": page_home,
    "Student Dashboard": page_student_dashboard,
    "Maths Practice": page_practice,
    "Agent Activity": page_agents,
    "Learning Room": page_learning,
    "Progress": page_progress,
    "Teacher Dashboard": page_teacher,
}
ROUTES[ss.page]()
