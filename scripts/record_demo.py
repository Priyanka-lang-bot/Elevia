"""Record the demonstration video (silent, with on-screen captions) by driving the real app in a browser.

    # terminal 1: a server with a freshly reset demo, demo mode on and a teacher access code
    export ELEVIA_DEMO_TEACHER_CODE=<private> ELEVIA_DEMO_PASSWORD=<private>
    ELEVIA_DB_PATH=/tmp/video.db python scripts/demo.py reset
    ELEVIA_DB_PATH=/tmp/video.db ELEVIA_DEMO_MODE=1 python -m uvicorn app:app --port 8765
    # terminal 2 (same ELEVIA_DEMO_TEACHER_CODE exported)
    python scripts/record_demo.py --base http://localhost:8765 --out out/elevia-demo.webm
    python scripts/record_demo.py --short --out out/elevia-demo-3min.webm      # about 3 minutes

It follows docs/round3-submission/ROUND3_DEMO_SCRIPT.md. Captions carry the narration; a dot shows where the
presenter points. The teacher access code is typed into a masked field and never shown.
"""
import argparse
import os
import re
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.content import questions  # noqa: E402
from backend.engine import correct_answer_text, render_prompt  # noqa: E402

KEY = {q["id"]: correct_answer_text(q) for q in questions().values()}
BY_PROMPT = {}
for q in questions().values():
    BY_PROMPT.setdefault(" ".join(render_prompt(q).split()), []).append(q["id"])

OVERLAY = """
window.__rec = window.__rec || {};
window.__cap = (title, text) => {
  let el = document.getElementById('rec-cap');
  if (!el) {
    el = document.createElement('div'); el.id = 'rec-cap';
    el.setAttribute('aria-hidden', 'true');
    el.style.cssText = 'position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:2147483647;'
      + 'max-width:1120px;width:calc(100% - 120px);background:rgba(23,32,58,.93);color:#fff;border-radius:12px;'
      + 'padding:14px 22px;font:500 21px/1.45 Nunito,system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.25);'
      + 'pointer-events:none;transition:opacity .25s';
    document.documentElement.appendChild(el);
  }
  el.style.opacity = text ? '1' : '0';
  el.innerHTML = '';
  if (title) { const b = document.createElement('div'); b.textContent = title;
    b.style.cssText = 'font-weight:800;font-size:14px;letter-spacing:.02em;color:#ffd9a0;margin-bottom:4px'; el.appendChild(b); }
  const t = document.createElement('div'); t.textContent = text || ''; el.appendChild(t);
};
window.__pt = (x, y) => {
  let d = document.getElementById('rec-pt');
  if (!d) {
    d = document.createElement('div'); d.id = 'rec-pt';
    d.style.cssText = 'position:fixed;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;'
      + 'background:rgba(230,57,70,.35);border:3px solid #e63946;z-index:2147483646;pointer-events:none;'
      + 'transition:left .5s ease,top .5s ease,opacity .3s';
    document.documentElement.appendChild(d);
  }
  if (x === null) { d.style.opacity = '0'; return; }
  d.style.opacity = '1'; d.style.left = x + 'px'; d.style.top = y + 'px';
};
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8765")
    ap.add_argument("--out", default="out/elevia-demo.webm")
    ap.add_argument("--chrome", default="/usr/bin/google-chrome")
    ap.add_argument("--note", default="")
    ap.add_argument("--short", action="store_true", help="about 3 minutes: same journey, fewer stops")
    a = ap.parse_args()
    code = os.environ.get("ELEVIA_DEMO_TEACHER_CODE", "")
    if not code:
        sys.exit("Set ELEVIA_DEMO_TEACHER_CODE (the value the server uses).")
    B = a.base
    S = a.short
    vid_dir = Path(a.out).parent / "raw"
    shutil.rmtree(vid_dir, ignore_errors=True)
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=a.chrome)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1,
                                  record_video_dir=str(vid_dir), record_video_size={"width": 1440, "height": 900})
        ctx.add_init_script(OVERLAY)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "status of 403" not in m.text else None)

        def cap(title, text, secs=None):
            pg.evaluate("([t, s]) => window.__cap(t, s)", [title, text])
            if secs is None:
                secs = max(2.6 if S else 3.0, len(text.split()) / (4.2 if S else 3.7))   # captions are read, not heard
            else:
                secs *= 0.5 if S else 0.62
            pg.wait_for_timeout(int(secs * 1000))

        def point(loc, secs=None):
            secs = (0.45 if S else 0.7) if secs is None else secs
            loc.scroll_into_view_if_needed()
            bb = loc.bounding_box()
            if bb:
                pg.evaluate("([x, y]) => window.__pt(x, y)", [bb["x"] + min(bb["width"] / 2, 60), bb["y"] + bb["height"] / 2])
            pg.wait_for_timeout(int(secs * 1000))

        def unpoint():
            pg.evaluate("window.__pt(null)")

        def click(loc, pause=0.7):
            point(loc, pause * (0.6 if S else 1))
            loc.click()
            unpoint()

        def glide(to_y, secs=2.5):
            """Scroll smoothly to a page position in small native steps (the page reacts as a user scrolls)."""
            start = pg.evaluate("scrollY")
            steps = max(1, int(secs * (0.4 if S else 0.55) * 30))
            for i in range(1, steps + 1):
                y = start + (to_y - start) * (i / steps)
                pg.evaluate(f"window.scrollTo(0, {y})")
                pg.wait_for_timeout(33)

        def section_y(sec, frac=0.0):
            return pg.evaluate(f"""(() => {{ const s = document.getElementById('{sec}'), nh = document.querySelector('.lnav').offsetHeight;
                return s.getBoundingClientRect().top + scrollY - nh + {frac} * Math.max(0, s.offsetHeight - innerHeight) }})()""")

        def qid():
            prompt = " ".join(pg.locator("#app .prompt").first.inner_text().split())
            ids = BY_PROMPT[prompt]
            if len(ids) > 1 and pg.locator("#app pre.code").count():
                c = pg.locator("#app pre.code").first.inner_text().strip()
                ids = [i for i in ids if questions()[i].get("code", "").strip() == c]
            return ids[0]

        def answer(override=None, hold=1.0):
            q = qid()
            text = (override or {}).get(q) or KEY[q]
            if pg.locator("#app input[type=radio]").count():
                click(pg.locator("#app label.choice", has_text=re.compile("^" + re.escape(text) + "$")).first, 0.5)
            else:
                box = pg.locator("#app input.answer-input")
                point(box, 0.4); box.click(); box.press_sequentially(text, delay=30 if S else 55); unpoint()
            pg.wait_for_timeout(300)
            click(pg.locator("#app form.qform button[type=submit]"), 0.4)
            pg.locator("#app .feedback").wait_for()
            pg.wait_for_timeout(int(hold * (0.55 if S else 1) * 1000))
            click(pg.locator("#app .actions .btn.main").last, 0.25 if S else 0.4)
            pg.wait_for_timeout(400)

        # ------------------------------------------------------------ title
        pg.goto(B + "/"); pg.locator("#demo-grid .lib-card").first.wait_for(); pg.wait_for_timeout(600)
        cap("ELEVIA · PRASUNEX Innovathon 2026, Round 3",
            "Demonstration of the working prototype. Silent recording with captions; the red dot shows where to look. "
            + (a.note or ""), 6 if S else 9)

        # ------------------------------------------------------------ 1. problem
        if S:
            glide(pg.evaluate("""(() => { const s = document.querySelector('.sstep[data-step="3"]');
                return s.getBoundingClientRect().top + scrollY - innerHeight * 0.4 })()"""), 2.5)
            cap("The problem", "Marks say THAT, not WHY. 1/2 + 1/3 = 2/5, twice, is a rule the student believes; "
                "the real gap is earlier.")
        for n in (() if S else ("1", "2", "3")):
            y = pg.evaluate(f"""(() => {{ const s = document.querySelector('.sstep[data-step="{n}"]');
                return s.getBoundingClientRect().top + scrollY - innerHeight * 0.4 }})()""")
            glide(y, 1.6)
            if n == "1":
                cap("1 · The problem", "This student wrote 1/2 + 1/3 = 2/5, and made the same move again on 1/4 + 2/3. "
                    "That isn't carelessness; it's a rule they believe.")
            elif n == "2":
                cap("1 · The problem", "One mistake can be a slip. The same rule twice is worth checking.", 5)
            else:
                cap("1 · The problem", "And the real gap is earlier: common denominators. Re-teaching the whole chapter misses it.")

        # ------------------------------------------------------------ 2. four roles
        glide(section_y("how", 0.0), 2)
        if S:
            glide(section_y("how", 0.3), 1.2)
            cap("Four roles", "Diagnoser suggests a possible gap; Checker verifies it before anything is taught.")
            glide(section_y("how", 0.7), 1.2)
            cap("Four roles", "Planner finds the missing skill, Tutor teaches it, a retest on unseen questions decides mastery.")
        else:
            cap("2 · How ELEVIA works", "Four roles take turns with each student, then a retest checks the result.", 4)
        roles = [
            "Diagnoser: matches wrong answers against 86 named misconceptions and suggests a POSSIBLE gap. Nothing is taught yet.",
            "Checker: asks two brand-new questions aimed at the same misconception. Confirmed, rejected as a slip, or sent to a teacher.",
            "Planner: walks a 58-skill prerequisite map to find where the lesson should start.",
            "Tutor: a short lesson that quotes the student's own answer, with worked examples, hints and practice.",
            "Retest: a day later, three unseen questions. Two right marks the skill mastered. These are fixed, testable rules, not AI guesses.",
        ]
        for i, text in enumerate([] if S else roles):
            glide(section_y("how", (i + 0.5) / 5), 1.4)
            cap("2 · The four roles", text)

        # ------------------------------------------------------------ 3. Riya
        glide(0, 1.5)
        click(pg.locator(".lnav-links a.nav-demo"))
        pg.wait_for_timeout(1200)
        if not S:
            cap("3 · Try the demo", "No sign-up. Riya Sharma is a fictional Class 9 student with six months of history.", 4.5)
        click(pg.locator("button[aria-label^='Open the demo as Riya']"))
        pg.locator("#app .next-step").wait_for(); pg.wait_for_timeout(800)
        point(pg.locator("#app .demo-banner"))
        if S:
            cap("Riya's six months", "One click, no sign-up: Riya Sharma, a fictional Class 9 student.", 3)
        else:
            cap("3 · Riya's dashboard", "Clearly labelled as a demonstration account: student DEMO-09-001, Class 9 A, ELEVIA "
                "Demonstration School. The history was produced by running ELEVIA's real rules on simulated answers.")
            point(pg.locator("#app .next-step"))
            cap("3 · Riya's dashboard", "One clear next step: her Data types lesson, ready after a confirmed gap.", 5)
        unpoint()
        glide(pg.evaluate("document.querySelector('#app .mchart').getBoundingClientRect().top + scrollY - 140"), 2)
        if S:
            cap("Riya's six months", "141 answers, 9 gaps confirmed, 3 rejected as slips, 8 skills mastered: real rules on simulated answers.")
        else:
            cap("3 · Six months of history", "Seven months of activity: 141 answers, 16 check-ins, 9 gaps confirmed, 3 rejected as "
                "slips, and 8 skills mastered.")
        if not S:
            click(pg.locator("#app .mtable summary"))
            pg.wait_for_timeout(500)
            cap("3 · Six months of history", "The monthly table adds up to the totals: every figure comes from the same stored records.", 5)
        glide(pg.evaluate("document.querySelector('#app .subj-row').getBoundingClientRect().top + scrollY - 160"), 2)
        cap("3 · Progress by subject", "All five Class 9 subjects." if S else
            "All five Class 9 subjects: Mathematics, Science, English, Social Science and Computer Science.", 3 if S else 5)
        if S:
            pass
        if not S:
            glide(pg.evaluate("document.querySelector('#app .sm-chip').getBoundingClientRect().top + scrollY - 200"), 1.5)
            cap("3 · Skill map", "Mastered skills are ticked. A skill only counts as mastered after a retest on new questions.", 5)
            glide(pg.evaluate("document.querySelector('#app #evf').getBoundingClientRect().top + scrollY - 160"), 1.5)
            pg.select_option("#evf", "Social Science"); pg.wait_for_timeout(700)
            cap("3 · Learning history", "Every check-in, double-check verdict, lesson, retest and teacher decision, filterable by subject.", 5.5)

        # ------------------------------------------------------------ 4. Dev: Diagnoser + Checker
        if S:
            cap("4 · A live journey", "Now Dev Kapoor, a new learner with no history.", 0.4)
        glide(0, 1)
        click(pg.locator("#app button", has_text="Log out"))
        pg.wait_for_timeout(1200)
        if not S:
            cap("4 · A live journey", "Dev Kapoor is a new learner with no history. Let's run a topic from the start.", 4)
        click(pg.locator("button[aria-label^='Open the demo as Dev']").locator("visible=true").first)
        pg.locator("#app .tabs").wait_for(); pg.wait_for_timeout(800)
        point(pg.locator("#dgrade")); pg.select_option("#dgrade", "9"); unpoint()
        click(pg.locator("#app button[aria-label='Start the check-in: Fractions']"))
        pg.locator("#app .qcount").wait_for()
        cap("4 · Dev, a new learner", "Five check-in questions; Dev adds tops and bottoms twice.", 2.5) if S else \
            cap("4 · Diagnoser", "A five-question check-in. Dev adds the tops and the bottoms on both addition questions.", 4)
        for _ in range(5):
            answer({"DA3": "2/5", "DA5": "3/7"}, hold=0.8)
        pg.locator("#app .gapbox").wait_for()
        point(pg.locator("#app .gapbox"))
        cap("4 · Diagnoser", "A POSSIBLE gap, not confirmed: the Checker asks two new questions first.") if S else \
            cap("4 · Diagnoser", "The Diagnoser flags a POSSIBLE gap: not confirmed yet, so nothing is taught. "
                "The Checker asks two new questions first.")
        unpoint()
        for _ in range(2):
            answer({"CD-V1": "2/9", "CD-V3": "10"}, hold=0.9)
        pg.locator("#app .gapbox").wait_for()
        point(pg.locator("#app .gapbox"))
        cap("4 · Checker", "Same mistake again: gap CONFIRMED. Both right would count as a slip.") if S else \
            cap("4 · Checker", "The same mistake again, so the gap is CONFIRMED. Both right would have been treated as a slip; "
                "a different mistake would go to the teacher.")

        # ------------------------------------------------------------ 5. Planner + Tutor
        unpoint()
        pg.locator("#app .lesson h2").wait_for()
        if S:
            cap("5 · Planner and Tutor", "The lesson starts at the missing skill, common denominators, quoting Dev's own answer.")
        else:
            cap("5 · Planner and Tutor", "The Planner chose common denominators, the earlier skill that's actually missing. "
                "The Tutor's lesson starts from Dev's own answer.")
            glide(pg.evaluate("document.querySelector('#app .lesson').getBoundingClientRect().top + scrollY + 250"), 2.5)
        if not S:
            cap("5 · Planner and Tutor", "Steps and worked examples, then practice with hints. Practice never counts towards progress.", 5)
            hint = pg.locator("#app button", has_text="Show a hint")
            click(hint); pg.locator("#app .hintbox").wait_for(); pg.wait_for_timeout(1500)
        answer(hold=0.8); answer(hold=0.8)
        click(pg.locator("#app button", has_text="done practising"))
        pg.locator("#app .countdown").wait_for(); pg.wait_for_timeout(600)
        point(pg.locator("#app .countdown"))
        if not S:
            cap("5 · Retest booked", "The Checker books a retest 24 hours later, on questions Dev hasn't seen.", 5)

        # ------------------------------------------------------------ 6. retest
        unpoint()
        cap("6 · Retest", "Booked for 24 hours later on unseen questions; the demo shortcut is logged.", 3.5 if S else 5)
        click(pg.locator("#app button", has_text="Start now"))
        for _ in range(3):
            answer(hold=0.7)
        pg.locator("#app .result h2").wait_for()
        point(pg.locator("#app .result h2"))
        cap("6 · Mastery", "Gap closed, skill mastered. A failed retest keeps the gap open and triggers a new plan.") if S else \
            cap("6 · Mastery", "Three unseen questions, two right needed: gap closed, skill mastered. A failed retest keeps the gap "
                "open and the Planner makes a new plan; if questions run out, the case goes to a teacher.")

        # ------------------------------------------------------------ 7. teacher
        unpoint()
        click(pg.locator("#app button", has_text="Log out"))
        pg.wait_for_timeout(800)
        pg.goto(B + "/"); pg.locator("#teacher-code").wait_for()
        glide(section_y("demo"), 1.5)
        cap("7 · Teacher portal", "The teacher view needs the judges' access code. It's a private server setting, never shown.", 3.5 if S else 5)
        box = pg.locator("#teacher-code")
        point(box, 0.5); box.click(); box.press_sequentially(code, delay=40); unpoint()
        click(pg.locator(".teacher-card button[type=submit]"))
        pg.locator("#app .queue-item").first.wait_for(); pg.wait_for_timeout(800)
        point(pg.locator("#app #co-h"))
        cap("7 · Class overview", "Ms Mehta's Class 9 A: who needs attention and why, and upcoming retests.") if S else \
            cap("7 · Class overview", "Ms Ananya Mehta's Class 9 A: five students, who needs attention and why, and upcoming retests, "
                "all worked out from saved answers, verdicts and retests.")
        if not S:
            glide(pg.evaluate("document.querySelector('#app #ci-h').getBoundingClientRect().top + scrollY - 120"), 2)
            cap("7 · Class insights", "Topics causing difficulty, frequent misconceptions, repeated failed retests (Arjun), and the "
                "most improved.")
        q = pg.locator("#app .queue-item", has_text="Riya Sharma · Past tense verbs")
        point(q)
        if not S:
            cap("7 · Review queue", "Cases the Checker couldn't decide wait here for the teacher.", 4)
        click(q.locator("a", has_text="Review"))
        pg.locator("#app .demo-banner").wait_for(); pg.locator("#app .mcol").first.wait_for(); pg.wait_for_timeout(600)
        if not S:
            cap("7 · Student record", "Riya's full record opens: her six-month timeline and skill map.", 4)
        pt = pg.locator("#app section.panel", has=pg.locator("h2", has_text=re.compile("^Past tense verbs$")))
        rnd = pt.locator(".round").first
        rnd.scroll_into_view_if_needed(); pg.wait_for_timeout(600)
        glide(pg.evaluate("scrollY") + 0, 0.2)
        if not S:
            point(rnd.locator("text=Diagnoser").first)
            cap("7 · Evidence", "The Diagnoser's suspected misconception, her check-in answers, and her double-check answers.", 5)
        point(rnd.locator("text=a different mistake").first)
        cap("7 · Evidence", "Mixed evidence, so the Checker sent Riya's case to the teacher instead of guessing.") if S else \
            cap("7 · Evidence", "One right and one DIFFERENT mistake: mixed evidence, so the Checker sent it to the teacher instead "
                "of guessing.")
        rv = pt.locator(".review").first
        click(rv.locator("button", has_text="Confirm gap"))
        point(rv.locator(".alert"))
        cap("7 · Teacher decision", "ELEVIA insists on a reason before any decision.", 3 if S else 4)
        ta = rv.locator("textarea")
        point(ta, 0.4); ta.click(); ta.press_sequentially("Riya wrote 'thinked' in her diary entry in class today", delay=10 if S else 22); unpoint()
        click(rv.locator("button", has_text="Confirm gap"))
        pt = pg.locator("#app section.panel", has=pg.locator("h2", has_text=re.compile("^Past tense verbs$")))
        pt.locator(".audit").first.wait_for(); pg.wait_for_timeout(500)
        point(pt.locator(".audit").first)
        cap("7 · Audited", "Saved with the reason in the audit log; Riya's lesson is now ready.") if S else \
            cap("7 · Audited", "Saved with the reason in the case audit; Riya's lesson is now ready and her history shows the teacher's decision.")
        if not S:
            click(pg.locator("#app a", has_text="Back to overview"))
            pg.locator("#app .queue-item").first.wait_for(); pg.wait_for_timeout(500)
            hist = pg.locator("#app section.panel", has=pg.locator("h2", has_text="Intervention history"))
            hist.scroll_into_view_if_needed(); point(hist.locator(".item").first)
            cap("7 · Intervention history", "Every teacher intervention is listed with its reason.", 4)
        unpoint()

        # ------------------------------------------------------------ 8. technical
        click(pg.locator("#app button", has_text="Log out"))
        pg.wait_for_timeout(600)
        pg.goto(B + "/"); pg.locator("#demo-grid .lib-card").first.wait_for()
        if not S:
            glide(section_y("features", 0.0), 2.5)
        if S:
            glide(pg.evaluate("document.body.scrollHeight - innerHeight"), 2)
            cap("Built and tested", "FastAPI on Vercel with Turso; 205 tests and 26 browser checks. Not yet classroom-tested; "
                "26 playable topics; synthetic demo data.")
        else:
          cap("8 · How it's built", "One FastAPI service on Vercel with a Turso (hosted SQLite) database, and a plain JavaScript front end. "
            "Every decision is written to an audit log.", 7)
        for i in (() if S else range(9)):
            glide(section_y("features", (i + 0.5) / 9), 0.6)
            pg.wait_for_timeout(250)
        if not S:
          cap("8 · Evidence", "205 automated tests pass on both databases, including checks that every dashboard number is backed by "
            "records; 26 browser checks walk the student, teacher and history journeys. Student code is never executed.")

        # ------------------------------------------------------------ 9. limitations
        if not S:
          glide(section_y("subjects", 0.0), 2)
          soon = pg.locator("#subj-grid .idx-soon").first
          soon.scroll_into_view_if_needed(); point(soon)
          cap("9 · Limitations", "Honest limits: not yet tested in classrooms, so no learning-outcome claims. 26 topics are playable; "
            "the rest are marked coming soon. The roles are fixed rules, not autonomous AI. The demo data is synthetic.")
          unpoint()
          cap("9 · Next", "Next: a classroom pilot with baseline measures, more topics, a validated mastery model, and Hindi and Marathi.", 6)

        # ------------------------------------------------------------ 10. closing
        if not S:
            glide(pg.evaluate("document.body.scrollHeight - innerHeight"), 3)
        cap("ELEVIA", "Don't just find the wrong answer. Find the missing understanding.", 3.5 if S else 5)
        cap("", "", 0.5)

        video = pg.video
        ctx.close()
        src = Path(video.path())
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), a.out)
        browser.close()
    shutil.rmtree(vid_dir, ignore_errors=True)
    print("saved", a.out)
    if errors:
        print("console/page errors:"); [print("  ", e) for e in errors]


if __name__ == "__main__":
    main()
