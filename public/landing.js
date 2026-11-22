/* Landing page behaviour: mobile menu, smooth in-page scrolling, scroll reveal, live subject catalogue, screenshot tabs. */
"use strict";
let landingReady = false;

function initLanding() {
  if (landingReady) return;
  landingReady = true;
  const nav = document.querySelector(".lnav");
  const toggle = document.querySelector(".lnav-toggle");
  toggle.addEventListener("click", () => {
    const open = !nav.classList.contains("open");
    nav.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
  });
  // In-page links scroll without touching the hash (the hash is used for app routes).
  document.querySelectorAll("#landing a[data-scroll]").forEach((a) => a.addEventListener("click", (ev) => {
    const id = a.getAttribute("href").slice(1);
    const target = document.getElementById(id);
    if (!target) return;
    ev.preventDefault();
    nav.classList.remove("open"); toggle.setAttribute("aria-expanded", "false");
    const y = target.getBoundingClientRect().top + window.scrollY - (id === "home" ? 200 : nav.offsetHeight);
    window.scrollTo({ top: Math.max(0, y), behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    target.setAttribute("tabindex", "-1"); target.focus({ preventScroll: true });
  }));
  // Reveal on scroll
  const items = document.querySelectorAll("#landing .reveal");
  if ("IntersectionObserver" in window) {
    document.documentElement.classList.add("rv");
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }), { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    items.forEach((i) => io.observe(i));
  } else items.forEach((i) => i.classList.add("in"));
  // Screenshot tabs
  const shots = { dash: ["/img/shot-dash.jpg", "Student dashboard with subjects, continue learning and upcoming retests"],
    verify: ["/img/shot-verify.jpg", "Double-check screen: the possible gap is not confirmed yet and two new questions are asked"],
    lesson: ["/img/shot-lesson.jpg", "Lesson screen with the confirmed gap, steps and worked examples"],
    result: ["/img/shot-result.jpg", "Result screen: the gap is closed after passing the retest on new questions"] };
  const img = document.getElementById("shot-img");
  document.querySelectorAll(".shot-tabs button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".shot-tabs button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    const [src, alt] = shots[b.dataset.shot]; img.src = src; img.alt = alt;
  }));
  loadCatalog();
  renderDemoCards(document.getElementById("demo-grid"), () => {
    document.getElementById("demo").hidden = false;
    document.querySelectorAll(".demo-cta").forEach((a) => { a.hidden = false; });
  });
}

const DEMO_ICON = { Student: "🎒", "New student": "✨", Teacher: "🧑‍🏫", Parent: "🏠", "School admin": "🏫" };

// One-click demo login. Shown only when the server runs with ELEVIA_DEMO_MODE=1.
async function renderDemoCards(box, onEnabled, compact) {
  if (!box) return;
  let d;
  try {
    const r = await fetch("/api/demo/accounts", { credentials: "same-origin" });
    if (!r.ok) return;
    d = await r.json();
  } catch (e) { return; }
  if (!d.enabled) return;
  if (onEnabled) onEnabled();
  if (!d.ready) {
    box.replaceChildren(el("p", { class: "alert bad", text: "Demo accounts aren't set up on this server yet. The team runs: python scripts/demo.py seed" }));
    return;
  }
  box.replaceChildren(...d.accounts.map((a) => {
    const btn = el("button", { class: "btn main" + (compact ? " small" : ""), type: "button", text: `Explore as ${a.name.split(" ")[0]}`,
      "aria-label": `Open the demo as ${a.name}, ${a.role}` });
    const err = el("p", { class: "alert bad", role: "alert", hidden: true });
    btn.addEventListener("click", async () => {
      btn.disabled = true; btn.textContent = "Opening…"; err.hidden = true;
      try {
        await api("POST", "/demo/login", { slug: a.slug });
        state.me = null; go("#/home");
      } catch (e) { err.textContent = e.detail; err.hidden = false; btn.disabled = false; btn.textContent = `Explore as ${a.name.split(" ")[0]}`; }
    });
    return el("article", { class: "demo-card" + (compact ? " compact" : "") },
      el("div", { class: "demo-top" }, el("span", { class: "demo-ic", "aria-hidden": "true", text: DEMO_ICON[a.role] || "•" }),
        el("div", {}, el("h3", { text: a.name }), el("p", { class: "demo-role", text: `${a.role} · ${a.badge}` }))),
      compact ? null : el("p", { class: "demo-ex", text: a.explore }),
      a.available ? btn : el("p", { class: "hint", text: "Not set up yet" }), err);
  }));
}

async function loadCatalog() {
  const grid = document.getElementById("subj-grid");
  let data;
  try {
    const r = await fetch("/api/learn/catalog", { credentials: "same-origin" });
    if (!r.ok) return;                        // keep the static summary already on the page
    data = await r.json();
  } catch (e) { return; }
  const c = data.counts;
  document.getElementById("hero-counts").textContent =
    `${c.subjects} subjects, ${c.topics} topics, ${c.questions} questions. Every answer is checked by fixed rules, not guessed by AI.`;
  grid.replaceChildren(...data.subjects.map((s) => {
    const art = el("article", { class: "subj reveal in", style: `--c:${s.color}` },
      el("h3", {}, el("span", { "aria-hidden": "true", text: s.icon }), s.name),
      el("p", { text: s.description }),
      el("ul", { class: "topic-links" }, s.topics.map((t) => el("li", {},
        el("a", { href: "#/learn/" + t.id, "aria-label": `Start ${t.name} (${s.name})` }, el("span", { text: t.name }), el("small", { text: `Grades ${t.grades}` }))))),
      s.planned.length ? el("div", { class: "planned-l", "aria-label": "Planned topics" }, s.planned.map((p) => el("span", { text: p + " · planned" }))) : null);
    return art;
  }));
}
