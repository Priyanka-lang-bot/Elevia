"""Browser end-to-end check of the whole product, driven like a real user (Playwright + Chrome).

    # terminal 1: a fresh database with the demo accounts, demo mode on
    ELEVIA_DB_PATH=/tmp/e2e.db python scripts/demo.py seed
    ELEVIA_DB_PATH=/tmp/e2e.db ELEVIA_DEMO_MODE=1 python -m uvicorn app:app --port 8765
    # terminal 2
    python scripts/e2e_browser.py [--base http://localhost:8765] [--shots]   (--shots refreshes public/img/*.jpg)

Covers: landing page (nav, catalogue, mobile menu), login, dashboard, a full fractions journey (check-in ->
double-check -> lesson -> practice -> retest -> result), a code question, teacher overview -> student detail
-> confirming an inconclusive gap with a reason, parent view, and mobile layouts. Fails on any console error.
"""
import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.content import questions  # noqa: E402
from backend.engine import correct_answer_text, render_prompt  # noqa: E402

PW = "Demo-Pass-2026!"
KEY = {q["id"]: correct_answer_text(q) for q in questions().values()}
BY_PROMPT = {}
for q in questions().values():
    BY_PROMPT.setdefault(" ".join(render_prompt(q).split()), []).append(q["id"])


def main():
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
        pg.locator("#subj-grid .topic-links a").first.wait_for()
        assert pg.locator("#subj-grid .topic-links a").count() == 24
        broken = pg.evaluate("[...document.images].filter(i => i.loading !== 'lazy' && !(i.complete && i.naturalWidth > 0)).map(i => i.src)")
        assert not broken, broken
        pg.locator("#demo-grid .demo-card").first.wait_for()
        assert pg.locator("#demo-grid .demo-card").count() == 6 and "Demo-Pass" not in pg.content()
        pg.click(".lnav-links a[href='#how']"); pg.wait_for_timeout(700)
        assert pg.evaluate("window.scrollY") > 400 and pg.evaluate("location.hash") == ""
        for sec in ("features", "students", "teachers", "about"):
            assert pg.locator(f"#{sec}").count() == 1
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
        step(f"landing: hero, {len(hrefs)} links checked, live catalogue (24 topics), 6 demo cards, no broken images")
        pg.evaluate("window.scrollTo(0,0)")
        pg.click(".lnav-links a.btn"); expect(pg.locator("#app h1")).to_contain_text("How would you like")
        step("Get started opens the account-type chooser")

        # ---------------------------------------------------------------- student journey (independent learner)
        pg = new_page()
        pg.goto(B + "/"); pg.locator("#demo-grid .demo-card").first.wait_for()
        pg.click("button[aria-label^='Open the demo as Ananya']")
        pg.locator("#app .tabs").wait_for()
        step("one-click demo login (Ananya, new student) lands on the dashboard")
        pg.locator("#app button[aria-label='Start the check-in: Fractions']").click()
        expect(pg.locator("#dgrade-err")).to_be_visible()
        pg.select_option("#dgrade", "6")
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
        pg.locator("#app #tab-computer_science").click()
        pg.locator("#app button[aria-label='Start the check-in: Loops']").click()
        pg.locator("#app pre.code").wait_for()
        answer(pg); answer(pg)
        step("code question: program shown, typed output checked")
        pg.reload(); pg.locator("#app .qcount").wait_for()
        expect(pg.locator("#app .qcount")).to_contain_text("question 3 of 5")
        step("reload keeps progress (resumed at question 3 of 5)")
        pg.locator("#app a", has_text="My dashboard").click()
        pg.locator("#app .cont-item").first.wait_for()
        assert pg.locator("#app .cont-item").count() == 1
        assert int(pg.locator("#app .stat-v").nth(1).inner_text()) >= 1          # retest pass mastered skills
        step("dashboard: continue learning, mastered skill, history")
        mp = new_page(390, 844)
        login(mp, "riya.demo"); mp.locator("#app .next-step").wait_for()
        assert mp.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        step("password login (Riya) works; dashboard with 'what to do next' fits a 390px phone screen")
        rp = new_page()
        rp.goto(B + "/#/login"); rp.locator(".demo-strip .demo-card").first.wait_for()
        rp.click(".demo-strip button[aria-label^='Open the demo as Riya']")
        rp.locator("#app .next-step").wait_for()
        expect(rp.locator("#app .next-step h2")).to_contain_text("Past tense")
        assert rp.locator("#app .upcoming, #app .list .item").count() >= 1
        shot(rp, "dash")
        rp.locator("#app .next-step button").click()
        rp.locator("#app .lesson h2").wait_for()
        step("Riya (demo strip on login page): next step opens her lesson in progress")

        # ---------------------------------------------------------------- teacher
        tp = new_page()
        login(tp, "demo.teacher@example.com")
        tp.locator("#app .queue-item").wait_for()
        expect(tp.locator("#app .queue-item")).to_contain_text("Arjun Patel · Fractions")
        tp.wait_for_timeout(300)
        shot(tp, "teacher")
        tp.locator("#app .queue-item a", has_text="Review").click()
        fr = tp.locator("#app section.panel", has=tp.locator("h2", has_text=re.compile("^Fractions$")))
        rv = fr.locator(".review").first
        rv.wait_for()
        expect(fr.locator(".round").first).to_contain_text("Inconclusive")
        expect(fr.locator(".round").first).to_contain_text("Evidence")
        step("teacher: review queue -> Arjun's case with evidence and review form")
        rv.locator("button", has_text="Confirm gap").click()
        expect(rv.locator(".alert")).to_be_visible()                               # reason required
        rv.locator("textarea").fill("Saw the same mistake in class on Monday")
        rv.locator("button", has_text="Confirm gap").click()
        fr = tp.locator("#app section.panel", has=tp.locator("h2", has_text=re.compile("^Fractions$")))
        expect(fr.locator(".round").first).to_contain_text("In the learning room")
        expect(fr.locator(".audit").first).to_contain_text("Saw the same mistake")
        step("teacher confirms with a reason; lesson created; override logged")

        # ---------------------------------------------------------------- parent + student sees teacher decision
        pp = new_page()
        login(pp, "demo.parent@example.com")
        pp.locator("#app .kid").wait_for()
        expect(pp.locator("#app .kid")).to_contain_text("Riya Sharma")
        assert pp.locator("#app .kid").count() == 1 and "Arjun" not in pp.locator("#app main").inner_text()
        pp.locator("#app .kid a", has_text="See details").click()
        pp.locator("#app .round").first.wait_for()
        assert pp.locator("#app .review").count() == 0
        step("parent (Sunita) sees only Riya, in plain language, with no review controls")
        sp = new_page()
        login(sp, "arjun.demo")
        sp.locator("#app .cont-item").first.wait_for()
        sp.goto(B + "/#/learn/fractions")
        expect(sp.locator("#app .where")).to_contain_text("Your teacher chose")
        step("student sees the teacher's decision on their journey")

        # ---------------------------------------------------------------- mobile landing
        mp.goto(B + "/"); mp.locator(".lnav-toggle").click()
        expect(mp.locator(".lnav-links")).to_be_visible()
        assert mp.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        step("landing on a phone: menu opens, no horizontal overflow")
        browser.close()

    if errors:
        print("\nConsole errors:"); [print("  ", e) for e in errors]
        sys.exit(1)
    print(f"\nAll {len(log)} browser checks passed, no console errors.")


if __name__ == "__main__":
    main()
