"""Browser end-to-end check of the whole product, driven like a real user (Playwright + Chrome).

    # terminal 1: a fresh database with the six-month demo, demo mode and the teacher access code on
    export ELEVIA_DEMO_PASSWORD=some-test-password ELEVIA_DEMO_TEACHER_CODE=some-judges-code
    ELEVIA_DB_PATH=/tmp/e2e.db python scripts/demo.py seed
    ELEVIA_DB_PATH=/tmp/e2e.db ELEVIA_DEMO_MODE=1 python -m uvicorn app:app --port 8765
    # terminal 2 (same two variables exported)
    python scripts/e2e_browser.py [--base http://localhost:8765] [--shots]   (--shots refreshes public/img/*.jpg)

Covers: landing page (nav, catalogue, mobile menu), login, dashboard, a full fractions journey (check-in ->
double-check -> lesson -> practice -> retest -> result), a code question, teacher overview -> student detail
-> confirming an inconclusive gap with a reason, parent view, and mobile layouts. Fails on any console error.
"""
import argparse
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.content import questions  # noqa: E402
from backend.engine import correct_answer_text, render_prompt  # noqa: E402

PW = os.environ.get("ELEVIA_DEMO_PASSWORD", "")                 # the password the demo was seeded with
TEACHER_CODE = os.environ.get("ELEVIA_DEMO_TEACHER_CODE", "")    # the server's judges' access code
KEY = {q["id"]: correct_answer_text(q) for q in questions().values()}
BY_PROMPT = {}
for q in questions().values():
    BY_PROMPT.setdefault(" ".join(render_prompt(q).split()), []).append(q["id"])


def main():
    if not PW or not TEACHER_CODE:
        sys.exit("Set ELEVIA_DEMO_PASSWORD and ELEVIA_DEMO_TEACHER_CODE (the values the demo server uses).")
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8765")
    ap.add_argument("--shots", action="store_true")
    ap.add_argument("--chrome", default="/usr/bin/google-chrome")
    a = ap.parse_args()
    B, IMG = a.base, ROOT / "public" / "img"
    errors, log = [], []

    def step(m):
        log.append(m); print("  ✓", m)

    def shot(page, name, full=False):
        if a.shots:
            page.screenshot(path=str(IMG / f"shot-{name}.jpg"), type="jpeg", quality=82, full_page=full)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=a.chrome, args=["--no-sandbox"])

        def new_page(w=1200, h=900):
            pg = browser.new_context(viewport={"width": w, "height": h}).new_page()
            pg.on("console", lambda m: errors.append(f"{pg.url}: {m.text}") if m.type == "error" and "fonts.g" not in m.text else None)
            pg.on("pageerror", lambda e: errors.append(f"{pg.url}: {e}"))
            return pg

        def login(pg, ident):
            pg.goto(B + "/#/login")
            pg.fill("input[name=identifier]", ident); pg.fill("input[name=password]", PW)
            pg.click("#app button[type=submit]")

        def qid_on(pg, assessment_ids=None):
            prompt = " ".join(pg.locator("#app .prompt").first.inner_text().split())
            ids = BY_PROMPT[prompt]
            if len(ids) > 1 and pg.locator("#app pre.code").count():          # code questions share a prompt
                code = pg.locator("#app pre.code").first.inner_text().strip()
                ids = [i for i in ids if questions()[i].get("code", "").strip() == code]
            return ids[0]

        def answer(pg, override=None, wrong=None):
            qid = qid_on(pg)
            text = (override or {}).get(qid) or (wrong if wrong else KEY[qid])
            if pg.locator("#app input[type=radio]").count():
                pg.locator("#app label.choice", has_text=re.compile("^" + re.escape(text) + "$")).first.click()
            else:
                pg.fill("#app input.answer-input", text)
            pg.locator("#app form.qform button[type=submit]").click()
            pg.locator("#app .feedback").wait_for()
            pg.locator("#app .actions .btn.main").last.click()

        # ---------------------------------------------------------------- landing
        pg = new_page(1300, 900)
        pg.goto(B + "/")
        expect(pg.locator("h1.hero-h")).to_contain_text("missing understanding")
        pg.locator("#subj-grid .idx-topics a").first.wait_for()
        assert pg.locator("#subj-grid .idx-topics a").count() == 26
        assert pg.locator("#subj-grid .idx-soon a").count() == 0 and pg.locator("#subj-grid .idx-soon li").count() >= 12
        broken = pg.evaluate("[...document.images].filter(i => i.loading !== 'lazy' && !(i.complete && i.naturalWidth > 0)).map(i => i.src)")
        assert not broken, broken
        pg.locator("#demo-grid .lib-card").first.wait_for()
        pg.locator("#demo-grid .teacher-card").wait_for()
        assert pg.locator("#demo-grid .lib-card").count() == 4 and PW not in pg.content() and TEACHER_CODE not in pg.content()
        names = pg.locator("#demo-grid .lib-name").all_inner_texts()
        assert names == ["Riya Sharma", "Dev Kapoor", "Arjun Patel", "Ananya Mehta"], names
        assert pg.locator("#teacher-code").get_attribute("type") == "password"
        staff = pg.request.post(B + "/api/demo/login", data={"slug": "teacher"},
                                headers={"x-elevia-web": "1"}).status        # outside the page: no console noise
        assert staff == 403, staff
        pg.click(".lnav-links a[href='#how']"); pg.wait_for_timeout(700)
        assert pg.evaluate("window.scrollY") > 400 and pg.evaluate("location.hash") == ""
        for sec in ("problem", "how", "features", "subjects", "students", "teachers", "why", "about", "demo"):
            assert pg.locator(f"#{sec}").count() == 1, sec
        hrefs = pg.eval_on_selector_all("#landing a[href]", "els => els.map(e => e.getAttribute('href'))")
        for h in hrefs:      # no dead links: every in-page anchor exists, every app route is known
            if h.startswith("#") and not h.startswith("#/"):
                assert pg.locator(h).count() == 1, h
            elif h.startswith("#/"):
                assert re.match(r"#/(start|login|learn/[a-z_]+)?$", h), h
        for y in range(0, pg.evaluate("document.body.scrollHeight"), 700):   # load lazy screenshots, then check them
            pg.evaluate(f"window.scrollTo(0,{y})"); pg.wait_for_timeout(60)
        pg.wait_for_timeout(500)
        broken = pg.evaluate("[...document.images].filter(i => !(i.complete && i.naturalWidth > 0)).map(i => i.src)")
        assert not broken, broken
        step(f"landing: {len(hrefs)} links checked, index of 26 playable topics in 5 subjects (coming-soon titles are not "
             "links), 3 student cards + a teacher card that needs the access code, no secrets in the page, no broken images")

        pg.evaluate("document.getElementById('students').scrollIntoView()"); pg.wait_for_timeout(900)
        assert pg.evaluate("[...document.querySelectorAll('#students .rv')].every(n => n.classList.contains('in'))")
        pg.focus("#st-dash"); pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(400)
        assert pg.get_attribute("#st-verify", "aria-selected") == "true" and pg.evaluate("document.activeElement.id") == "st-verify"
        expect(pg.locator("#shot-cap")).to_contain_text("double-check")
        assert "shot-verify" in pg.get_attribute("#shot-img", "src")
        pg.keyboard.press("End"); pg.wait_for_timeout(400)
        assert pg.get_attribute("#st-result", "aria-selected") == "true" and "shot-result" in pg.get_attribute("#shot-img", "src")
        pg.click("#st-lesson"); pg.wait_for_timeout(400)
        expect(pg.locator("#shot-cap")).to_contain_text("lesson")
        step("For students: section slides in once; Dashboard/Double-check/Lesson/Result tabs work by click and arrow keys, with captions")

        pg.evaluate("window.scrollTo(0,0)")
        pg.click(".lnav-links a.nav-demo"); pg.wait_for_timeout(700)
        top = pg.evaluate("document.getElementById('demo').getBoundingClientRect().top")
        assert 0 <= top < 120, top
        step("Try demo in the top navigation scrolls to the student demo cards")

        def active_book():
            return pg.evaluate("[...document.querySelectorAll('#how .bk-item')].findIndex(x => x.classList.contains('active'))")
        assert pg.evaluate("document.getElementById('how').classList.contains('live')")
        y = pg.evaluate("""(() => { const s = document.getElementById('how');
            return s.getBoundingClientRect().top + scrollY - document.querySelector('.lnav').offsetHeight + (s.offsetHeight - innerHeight) * 0.5 })()""")
        pg.evaluate(f"window.scrollTo({{top: {y}, behavior: 'instant'}})"); pg.wait_for_timeout(500)
        assert active_book() == 2, active_book()
        expect(pg.locator("#leaf-2")).to_be_visible()
        pg.click("#how .bk-item:nth-child(5) .book"); pg.wait_for_timeout(1400)
        assert active_book() == 4 and pg.locator("#how .bk-item:nth-child(5) .book").get_attribute("aria-expanded") == "true"
        step("book stack: scrolling opens one book at a time (3rd at mid-section); clicking a spine opens its page")

        def ws_step():
            return pg.evaluate("document.getElementById('ws-stage').dataset.step")
        for n in ("1", "3"):
            pg.evaluate(f"""(() => {{ const s = document.querySelector('.sstep[data-step="{n}"]');
                scrollTo({{top: s.getBoundingClientRect().top + scrollY - innerHeight * 0.4, behavior: "instant"}}) }})()"""); pg.wait_for_timeout(500)
            assert ws_step() == n, (n, ws_step())
        step("worksheet: red-pen annotations appear one idea at a time as you scroll (1, then 3)")

        pg.evaluate("document.getElementById('features').scrollIntoView()"); pg.wait_for_timeout(1200)
        assert pg.evaluate("document.getElementById('folders').classList.contains('in')")       # entrance ran once
        right = pg.evaluate("Math.max(...[...document.querySelectorAll('#folders .folder-tab')].map(t => t.getBoundingClientRect().right))")
        assert right <= pg.evaluate("innerWidth"), right                                         # all nine fit
        pg.click("#ft-3"); pg.wait_for_timeout(700)
        assert pg.locator(".folder.open").count() == 1 and pg.get_attribute("#ft-3", "aria-expanded") == "true"
        expect(pg.locator("#fs-3")).to_be_visible()
        pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(700)
        assert pg.get_attribute("#ft-4", "aria-expanded") == "true" and pg.evaluate("document.activeElement.id") == "ft-4"
        pg.hover("#ft-7"); pg.wait_for_timeout(700)
        assert pg.get_attribute("#ft-7", "aria-expanded") == "true"
        expect(pg.locator("#fs-7")).to_contain_text("How it works")
        step("What's built: folders slide in, all nine fit; click, arrow keys and hover open one panel with how it works and what's built")

        pg.evaluate("window.scrollTo(0,0)")
        pg.click(".lnav-links a.btn"); expect(pg.locator("#app h1")).to_contain_text("How would you like")
        step("Get started opens the account-type chooser")

        # ---------------------------------------------------------------- student journey: a full topic, live (Dev)
        pg = new_page()
        pg.goto(B + "/"); pg.locator("#demo-grid .lib-card").first.wait_for()
        pg.click("button[aria-label^='Open the demo as Dev']")
        pg.locator("#app .tabs").wait_for()
        step("one-click demo login (Dev, new learner) lands on the dashboard")
        pg.locator("#app button[aria-label='Start the check-in: Fractions']").click()
        expect(pg.locator("#dgrade-err")).to_be_visible()
        pg.select_option("#dgrade", "9")
        pg.locator("#app button[aria-label='Start the check-in: Fractions']").click()
        pg.locator("#app .qcount").wait_for()
        expect(pg.locator("#app .qcount")).to_contain_text("question 1 of 5")
        step("grade required once, then fractions check-in starts")
        for _ in range(5):
            answer(pg, {"DA3": "2/5", "DA5": "3/7"})
        expect(pg.locator("#app .gapbox")).to_contain_text("not confirmed")
        shot(pg, "verify")
        step("Diagnoser: suspected gap shown as not confirmed; double-check asked")
        for _ in range(2):
            answer(pg, {"CD-V1": "2/9", "CD-V3": "10"})
        expect(pg.locator("#app .gapbox")).to_contain_text("Gap confirmed")
        expect(pg.locator("#app .lesson h2")).to_be_visible()
        shot(pg, "lesson")
        step("Checker confirmed -> Planner + Tutor lesson")
        pg.locator("#app button", has_text="Show a hint").click(); pg.locator("#app .hintbox").wait_for()
        answer(pg); answer(pg)
        pg.locator("#app button", has_text="done practising").click()
        expect(pg.locator("#app .countdown")).to_contain_text("Unlocks")
        pg.locator("#app button", has_text="Start now").click()
        for _ in range(3):
            answer(pg)
        expect(pg.locator("#app .result h2")).to_have_text("Gap closed")
        shot(pg, "result")
        step("practice -> delayed retest (demo shortcut) -> 3/3 -> gap closed")
        pg.locator("#app a", has_text="Choose another topic").click()
        pg.locator("#app #tab-social_science").click()
        pg.locator("#app button[aria-label='Start the check-in: Time zones and Indian Standard Time']").click()
        pg.locator("#app .qcount").wait_for()
        answer(pg); answer(pg)
        step("Social Science topic plays through the same engine")
        pg.reload(); pg.locator("#app .qcount").wait_for()
        expect(pg.locator("#app .qcount")).to_contain_text("question 3 of 5")
        step("reload keeps progress (resumed at question 3 of 5)")

        # ---------------------------------------------------------------- historical data journey (Riya)
        rp = new_page()
        rp.goto(B + "/"); rp.locator("#demo-grid .lib-card").first.wait_for()
        rp.click("button[aria-label^='Open the demo as Riya']")
        rp.locator("#app .next-step").wait_for()
        expect(rp.locator("#app .demo-banner")).to_contain_text("DEMO-09-001")
        expect(rp.locator("#app .demo-banner")).to_contain_text("Class 9 A, ELEVIA Demonstration School, 2026-27")
        expect(rp.locator("#app .next-step h2")).to_contain_text("Data types")
        rp.locator("#app .mcol").first.wait_for()
        shot(rp, "dash")
        months = rp.locator("#app .mchart .mcol").count()
        assert months >= 6, months
        rp.locator("#app .mtable summary").click()
        col = rp.eval_on_selector_all("#app .mtable tbody tr", "rs => rs.map(r => Number(r.children[1].textContent))")
        stat_answers = int(rp.locator("#app #h-time ~ .stats .stat-v").first.inner_text())
        header_answers = int(rp.locator("#app .hello .stat-v").nth(2).inner_text())
        assert sum(col) == stat_answers == header_answers, (col, stat_answers, header_answers)
        step(f"six-month timeline: {months} months; monthly table adds up to the totals ({stat_answers} answers) shown on the dashboard")
        subj = rp.locator("#app .subj-row .subj-name").all_inner_texts()
        assert subj == ["Mathematics", "Science", "English", "Social Science", "Computer Science"], subj
        mastered = rp.locator("#app .sm-chip.mastered:not(.sm-key .sm-chip)").count()
        assert mastered == int(rp.locator("#app .hello .stat-v").nth(1).inner_text()) == 8, mastered
        rp.select_option("#evf", "Social Science")
        texts = rp.locator("#app .events .ev").all_inner_texts()
        assert texts and all("Social Science" in t for t in texts)
        assert any("Retest passed" in t for t in texts) and any("Teacher confirmed" in t for t in texts)
        step("all five subjects, skill map agrees with mastered count (8), history filters by subject with retests and teacher decisions")
        rp.locator("#app .next-step button").click()
        rp.locator("#app .lesson h2").wait_for()
        answer(rp)                                                     # she had done 2 practice questions already
        rp.locator("#app button", has_text="done practising").click()
        expect(rp.locator("#app .countdown")).to_contain_text("Unlocks")
        step("Riya's next step opens her lesson in progress; finishing practice books a real delayed retest")
        mp = new_page(390, 844)
        login(mp, "riya.demo"); mp.locator("#app .mcol").first.wait_for()
        assert mp.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        step("password login (Riya) works; dashboard with timeline and skill map fits a 390px phone screen")

        # ---------------------------------------------------------------- teacher journey (judges' access code)
        tp = new_page()
        tp.goto(B + "/"); tp.locator("#teacher-code").wait_for()
        before = len(errors)
        tp.fill("#teacher-code", "not-the-code"); tp.click(".teacher-card button[type=submit]")
        expect(tp.locator(".teacher-card .alert")).to_contain_text("isn't right")
        tp.wait_for_timeout(200)
        # the browser logs the refused request itself (403); that one expected entry is the only thing dropped
        expected = [e for e in errors[before:] if "status of 403" in e]
        assert len(expected) <= 1 and len(errors[before:]) == len(expected), errors[before:]
        del errors[before:]
        tp.fill("#teacher-code", TEACHER_CODE); tp.click(".teacher-card button[type=submit]")
        tp.locator("#app .queue-item").first.wait_for()
        expect(tp.locator("#app #co-h")).to_contain_text("Class overview · Class 9 A")
        expect(tp.locator("#app #co-h ~ .stats .stat-v").first).to_have_text("5")
        expect(tp.locator("#app #ci-h ~ .insight-grid")).to_contain_text("Arjun Patel")
        tp.evaluate("window.scrollTo({top: 0, behavior: 'instant'})"); tp.wait_for_timeout(300)
        shot(tp, "teacher")
        step("teacher demo: wrong access code refused, right one opens the class overview, insights and review queue")
        q = tp.locator("#app .queue-item", has_text="Riya Sharma · Past tense verbs")
        q.locator("a", has_text="Review").click()
        tp.locator("#app .demo-banner").wait_for()
        tp.locator("#app .mcol").first.wait_for()
        pt = tp.locator("#app section.panel", has=tp.locator("h2", has_text=re.compile("^Past tense verbs$")))
        rv = pt.locator(".review").first
        rv.wait_for()
        rnd = pt.locator(".round").first
        for text in ("Inconclusive", "Diagnoser", "Check-in answers", "Double-check answers", "Checker's verdict", "a different mistake"):
            expect(rnd).to_contain_text(text)
        step("Riya's profile: six-month timeline, skill map, and the flagged case with Diagnoser hypothesis and Checker evidence")
        rv.locator("button", has_text="Confirm gap").click()
        expect(rv.locator(".alert")).to_be_visible()                               # reason required
        rv.locator("textarea").fill("Riya wrote 'thinked' in her diary entry in class today")
        rv.locator("button", has_text="Confirm gap").click()
        pt = tp.locator("#app section.panel", has=tp.locator("h2", has_text=re.compile("^Past tense verbs$")))
        expect(pt.locator(".round").first).to_contain_text("In the learning room")
        expect(pt.locator(".audit").first).to_contain_text("diary entry")
        tp.locator("#app #h-log").wait_for()
        expect(tp.locator("#app .events .ev").first).to_contain_text("Teacher confirmed the gap")
        tp.locator("#app a", has_text="Back to overview").click()
        tp.locator("#app .queue-item").first.wait_for()
        hist = tp.locator("#app section.panel", has=tp.locator("h2", has_text="Intervention history"))
        expect(hist.locator(".item").first).to_contain_text("diary entry")
        assert tp.locator("#app .queue-item", has_text="Riya Sharma · Past tense verbs").count() == 0
        step("teacher confirms with a reason; saved in the case audit, Riya's history and the intervention history; queue updated")

        # ---------------------------------------------------------------- parent + student sees teacher decision
        pp = new_page()
        login(pp, "demo.parent@example.com")
        pp.locator("#app .kid").wait_for()
        expect(pp.locator("#app .kid")).to_contain_text("Riya Sharma")
        assert pp.locator("#app .kid").count() == 1 and "Arjun" not in pp.locator("#app main").inner_text()
        pp.locator("#app .kid a", has_text="See details").click()
        pp.locator("#app .mcol").first.wait_for()
        assert pp.locator("#app .review").count() == 0
        step("parent (Sunita) sees only Riya, with her timeline, and no review controls")
        sp = new_page()
        login(sp, "riya.demo")
        sp.locator("#app .next-step").first.wait_for()
        sp.goto(B + "/#/learn/past_tense")
        expect(sp.locator("#app .where")).to_contain_text("Your teacher chose")
        step("student sees the teacher's decision on her journey")

        # ---------------------------------------------------------------- mobile landing
        mp.goto(B + "/"); mp.locator(".lnav-toggle").click()
        expect(mp.locator(".lnav-links")).to_be_visible()
        assert mp.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        expect(mp.locator(".nav-demo-m")).to_be_visible()
        mp.locator(".lnav-toggle").click()
        mp.evaluate("document.getElementById('features').scrollIntoView()")
        mp.click("#ft-2"); expect(mp.locator("#fs-2")).to_be_visible()
        assert not mp.locator("#fs-5").is_visible()
        mp.click("#ft-2"); assert not mp.locator("#fs-2").is_visible()             # tap again to close
        mp.click("#how .bk-item:nth-child(4) .book"); expect(mp.locator("#leaf-3")).to_be_visible()
        assert not mp.locator("#leaf-0").is_visible()
        for w in (768, 1024):                                                       # tablet widths
            tp2 = new_page(w, 1000); tp2.goto(B + "/"); tp2.wait_for_timeout(400)
            assert tp2.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), w
        step("phone and tablet: Try demo always visible, menu opens, tap-to-open folders and books, no horizontal overflow")

        nj = browser.new_context(viewport={"width": 1300, "height": 900}, java_script_enabled=False).new_page()
        nj.goto(B + "/")
        for i in range(9):
            expect(nj.locator(f"#fs-{i}")).to_be_visible()
        for i in range(5):
            expect(nj.locator(f"#leaf-{i}")).to_be_visible()
        assert nj.locator("#subj-grid .idx-topics a").count() == 26 and nj.locator("#ws-stage .a3").is_visible()
        assert nj.locator("#students .split-copy").is_visible()
        step("without JavaScript every folder sheet, book page, annotation, the student section and all 26 topics are readable")

        rm = browser.new_context(viewport={"width": 1300, "height": 900}, reduced_motion="reduce").new_page()
        rm.on("pageerror", lambda e: errors.append(f"reduced-motion: {e}"))
        rm.goto(B + "/"); rm.locator("#subj-grid .idx-topics a").first.wait_for()
        assert not rm.evaluate("document.getElementById('subj-grid').classList.contains('idx-live')")
        rm.evaluate("document.getElementById('subjects').scrollIntoView()")
        expect(rm.locator("#subj-grid .idx-topics a").first).to_be_visible()
        step("reduced motion: no reveal animations, content shown straight away")
        browser.close()

    if errors:
        print("\nConsole errors:"); [print("  ", e) for e in errors]
        sys.exit(1)
    print(f"\nAll {len(log)} browser checks passed, no console errors.")


if __name__ == "__main__":
    main()
