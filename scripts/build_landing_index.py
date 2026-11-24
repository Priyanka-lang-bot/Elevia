"""Write the static subject index into public/index.html from the live curriculum.

The landing page refreshes the index from /api/learn/catalog in the browser; this static copy means the
index is complete for search engines, for visitors without JavaScript, and if the API is unreachable.
Run after changing the curriculum:  python scripts/build_landing_index.py
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

PAGE = ROOT / "public" / "index.html"
START, END = "<!-- SUBJECT-INDEX:START", "<!-- SUBJECT-INDEX:END -->"


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def render(data: dict) -> str:
    out = []
    for s in data["subjects"]:
        n = len(s["topics"])
        rows = "\n".join(
            f'          <li style="--k:{k}"><a href="#/learn/{esc(t["id"])}" aria-label="Start {esc(t["name"])}, '
            f'{esc(s["name"])}, grades {esc(t["grades"])}"><span class="t">{esc(t["name"])}</span>'
            f'<span class="lead" aria-hidden="true"></span><span class="g">Grades {esc(t["grades"])}</span></a></li>'
            for k, t in enumerate(s["topics"]))
        soon = ""
        if s["planned"]:
            items = "".join(f"<li>{esc(p)}</li>" for p in s["planned"])
            soon = (f'\n        <div class="idx-soon"><p class="idx-soon-h">Coming soon, not playable yet</p>'
                    f'<ul aria-label="{esc(s["name"])} topics coming soon">{items}</ul></div>')
        out.append(
            f'      <section class="idx-sub" style="--c:{esc(s["color"])}" aria-labelledby="idx-{esc(s["id"])}">\n'
            f'        <header class="idx-tab"><h3 id="idx-{esc(s["id"])}">{esc(s["name"])}</h3>'
            f'<p class="idx-count">{n} topic{"s" if n != 1 else ""} to play</p></header>\n'
            f'        <p class="idx-desc">{esc(s["description"])}</p>\n'
            f'        <ul class="idx-topics">\n{rows}\n        </ul>{soon}\n      </section>')
    return "\n".join(out)


def main() -> None:
    data = TestClient(app).get("/api/learn/catalog").json()
    page = PAGE.read_text(encoding="utf-8")
    pat = re.compile(re.escape(START) + r".*?-->\n.*?" + re.escape(END), re.S)
    head = re.search(re.escape(START) + r".*?-->", page, re.S).group(0)
    new, n = pat.subn(lambda m: head + "\n" + render(data) + "\n" + END, page)
    if n != 1:
        raise SystemExit("index markers not found in public/index.html")
    PAGE.write_text(new, encoding="utf-8")
    print(f"Wrote {data['counts']['topics']} topics in {data['counts']['subjects']} subjects to {PAGE.name}")


if __name__ == "__main__":
    main()
