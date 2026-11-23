/* Landing page behaviour.
   Everything here is an enhancement: without JavaScript the worksheet shows all its annotations, every book
   shows its page, every folder shows its sheet and the subject index is the static copy in the HTML.
   No scroll-jacking: the page always scrolls natively; JS only reads the scroll position. */
"use strict";
let landingReady = false;
const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

function initLanding() {
  if (landingReady) return;
  landingReady = true;
  const root = document.getElementById("landing");
  const nav = document.querySelector(".lnav");
  const toggle = document.querySelector(".lnav-toggle");
  const setNavH = () => root.style.setProperty("--navh", nav.offsetHeight + "px");
  setNavH(); addEventListener("resize", setNavH);
  toggle.addEventListener("click", () => {
    const open = !nav.classList.contains("open");
    nav.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
  });
  // In-page links scroll without touching the hash (the hash is used for app routes, so Back stays natural).
  document.querySelectorAll("#landing a[data-scroll]").forEach((a) => a.addEventListener("click", (ev) => {
    const id = a.getAttribute("href").slice(1);
    const target = document.getElementById(id);
    if (!target) return;
    ev.preventDefault();
    nav.classList.remove("open"); toggle.setAttribute("aria-expanded", "false");
    scrollToY(target.getBoundingClientRect().top + window.scrollY - nav.offsetHeight + 1);
    target.setAttribute("tabindex", "-1"); target.focus({ preventScroll: true });
  }));
  // Screenshot tabs
  const shots = { dash: ["/img/shot-dash.jpg", "Student dashboard with what to do next, continue learning and upcoming retests"],
    verify: ["/img/shot-verify.jpg", "Double-check screen: the possible gap is not confirmed yet and two new questions are asked"],
    lesson: ["/img/shot-lesson.jpg", "Lesson screen with the confirmed gap, steps and worked examples"],
    result: ["/img/shot-result.jpg", "Result screen: the gap is closed after passing the retest on new questions"] };
  const img = document.getElementById("shot-img");
  document.querySelectorAll(".shot-tabs button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".shot-tabs button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    const [src, alt] = shots[b.dataset.shot]; img.src = src; img.alt = alt;
  }));
  initFolders();
  initBooks();
  initSymptom();
  initIndexReveal();
  loadCatalog();
  renderDemoCards(document.getElementById("demo-grid"));
  let ticking = false;
  addEventListener("scroll", () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { ticking = false; onLandingScroll(); });
  }, { passive: true });
  addEventListener("resize", onLandingScroll);
  onLandingScroll();
}

function scrollToY(y) {
  window.scrollTo({ top: Math.max(0, y), behavior: reduceMotion() ? "auto" : "smooth" });
}

const scrollHandlers = [];
function onLandingScroll() {
  if (document.getElementById("landing").hidden) return;
  scrollHandlers.forEach((f) => f());
}

/* ------------------------------------------------------------------ demo: student reader cards */
// One-click demo login, student accounts only. The server offers it only when ELEVIA_DEMO_MODE=1.
// `compact` is the small version on the login page, which stays hidden unless the demo is available.
async function renderDemoCards(box, onEnabled, compact) {
  if (!box) return;
  let d = null;
  try {
    const r = await fetch("/api/demo/accounts", { credentials: "same-origin" });
    if (r.ok) d = await r.json();
  } catch (e) { d = null; }
  if (!d || !d.enabled || !d.ready) {
    if (compact) return;
    box.replaceChildren(el("div", { class: "demo-off" },
      el("p", { text: d && d.enabled
        ? "The demo accounts haven't been set up on this server yet, so the cards aren't available."
        : "The live demo isn't switched on for this copy of ELEVIA right now. You can create your own account instead: it takes about a minute, and the first check-in is five questions." }),
      el("div", { class: "actions" }, el("a", { class: "btn main", href: "#/start", text: "Get started" }),
        el("a", { class: "btn", href: "#/login", text: "Log in" }))));
    return;
  }
  if (onEnabled) onEnabled();
  box.replaceChildren(...d.accounts.map((a) => {
    const first = a.name.split(" ")[0];
    const label = `Open as ${first}`;
    const btn = el("button", { class: "btn main" + (compact ? " small" : ""), type: "button", text: label,
      "aria-label": `Open the demo as ${a.name}, ${a.role}` });
    const err = el("p", { class: "alert bad", role: "alert", hidden: true });
    btn.addEventListener("click", async () => {
      btn.disabled = true; btn.textContent = "Opening…"; err.hidden = true;
      try {
        await api("POST", "/demo/login", { slug: a.slug });
        state.me = null; go("#/home");
      } catch (e) { err.textContent = e.detail; err.hidden = false; btn.disabled = false; btn.textContent = label; }
    });
    const action = a.available ? btn : el("p", { class: "hint", text: "Not set up yet" });
    if (compact) {
      return el("article", { class: "demo-card compact" },
        el("div", { class: "demo-top" }, el("div", {}, el("h3", { text: a.name }), el("p", { class: "demo-role", text: `${a.role} · ${a.badge}` }))),
        action, err);
    }
    return el("article", { class: "lib-card" },
      el("p", { class: "lib-head", text: "Demo student card" }),
      el("h3", { class: "lib-name", text: a.name }),
      el("p", { class: "lib-role", text: `${a.role} · ${a.badge}` }),
      el("p", { class: "lib-ex", text: a.explore }),
      action, err);
  }));
}

/* ------------------------------------------------------------------ the problem: worksheet annotations */
function initSymptom() {
  const stage = document.getElementById("ws-stage");
  const grid = stage && stage.closest(".symptom-grid");
  if (!stage) return;
  const steps = [...grid.querySelectorAll(".sstep")];
  const wide = matchMedia("(min-width: 1001px)");
  const apply = () => {
    const on = wide.matches;
    stage.classList.toggle("seq", on); grid.classList.toggle("seq-on", on);
    if (!on) { stage.dataset.step = "3"; steps.forEach((s) => s.classList.add("on")); } else update();
  };
  const update = () => {
    if (!wide.matches) return;
    const line = innerHeight * 0.58;
    let n = 0;
    steps.forEach((s) => { if (s.getBoundingClientRect().top < line) n = Number(s.dataset.step); });
    stage.dataset.step = String(n);
    steps.forEach((s) => s.classList.toggle("on", Number(s.dataset.step) === n || (n === 0 && s.dataset.step === "1")));
  };
  wide.addEventListener("change", apply);
  scrollHandlers.push(update);
  apply();
}

/* ------------------------------------------------------------------ how it works: book stack */
function initBooks() {
  const section = document.getElementById("how");
  if (!section) return;
  const items = [...section.querySelectorAll(".bk-item")];
  const wide = matchMedia("(min-width: 1001px)");
  let active = -1;
  section.classList.add("js-books");
  const activate = (i) => {
    if (i === active) return;
    active = i;
    items.forEach((it, k) => {
      it.classList.toggle("active", k === i);
      it.querySelector(".book").setAttribute("aria-expanded", String(k === i));
    });
  };
  const span = () => section.offsetHeight - innerHeight;
  const navH = () => document.querySelector(".lnav").offsetHeight;
  const update = () => {
    if (!section.classList.contains("live")) return;
    const p = (navH() - section.getBoundingClientRect().top) / Math.max(1, span());
    activate(Math.min(items.length - 1, Math.max(0, Math.floor(p * items.length))));
  };
  items.forEach((it, i) => it.querySelector(".book").addEventListener("click", () => {
    if (section.classList.contains("live")) {
      // scroll the page to where this book is open; the page still scrolls natively
      const top = section.getBoundingClientRect().top + scrollY - navH();
      scrollToY(top + ((i + 0.5) / items.length) * span());
    } else {
      activate(i);
      if (!reduceMotion()) it.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }));
  const apply = () => {
    section.classList.toggle("live", wide.matches);
    if (wide.matches) { active = -1; update(); } else if (active < 0) activate(0);
  };
  wide.addEventListener("change", apply);
  scrollHandlers.push(update);
  activate(0);
  apply();
}

/* ------------------------------------------------------------------ what's built: folders */
function initFolders() {
  const list = document.getElementById("folders");
  if (!list) return;
  list.classList.add("js-folders");
  const items = [...list.querySelectorAll(".folder")];
  const tabs = items.map((f) => f.querySelector(".folder-tab"));
  const fine = matchMedia("(hover: hover) and (pointer: fine) and (min-width: 901px)");
  const narrow = matchMedia("(max-width: 900px)");
  const setOpen = (i) => items.forEach((f, k) => {
    f.classList.toggle("open", k === i);
    tabs[k].setAttribute("aria-expanded", String(k === i));
  });
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => {
      // on phones a tapped open folder closes again; on wide screens one folder is always open
      if (narrow.matches && items[i].classList.contains("open")) setOpen(-1); else setOpen(i);
    });
    t.addEventListener("keydown", (ev) => {
      const d = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[ev.key];
      if (!d) return;
      ev.preventDefault();
      const n = (i + d + tabs.length) % tabs.length;
      tabs[n].focus(); setOpen(n);
    });
  });
  let timer = 0;
  items.forEach((f, i) => {
    f.addEventListener("mouseenter", () => {
      if (!fine.matches) return;
      clearTimeout(timer);
      timer = setTimeout(() => setOpen(i), 90);   // a short delay so sweeping across the stack doesn't flicker
    });
    f.addEventListener("mouseleave", () => clearTimeout(timer));
  });
}

/* ------------------------------------------------------------------ subjects: index from the live catalogue */
let indexObserver = null;
function initIndexReveal() {
  const book = document.getElementById("subj-grid");
  if (!book || !("IntersectionObserver" in window) || reduceMotion()) return;
  book.classList.add("idx-live");
  indexObserver = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (!e.isIntersecting) return;
    const subs = [...book.querySelectorAll(".idx-sub")];
    // reveal columns one after another, left to right
    subs.forEach((s, k) => setTimeout(() => s.classList.add("in"), k * 160));
    indexObserver.disconnect();
  }), { rootMargin: "0px 0px -15% 0px", threshold: 0.05 });
  indexObserver.observe(book);
}

function indexColumn(s) {
  const n = s.topics.length;
  return el("section", { class: "idx-sub", style: `--c:${s.color}`, "aria-labelledby": "idx-" + s.id },
    el("header", { class: "idx-tab" }, el("h3", { id: "idx-" + s.id, text: s.name }),
      el("p", { class: "idx-count", text: `${n} topic${n === 1 ? "" : "s"} to play` })),
    el("p", { class: "idx-desc", text: s.description }),
    el("ul", { class: "idx-topics" }, s.topics.map((t, k) => el("li", { style: `--k:${k}` },
      el("a", { href: "#/learn/" + t.id, "aria-label": `Start ${t.name}, ${s.name}, grades ${t.grades}` },
        el("span", { class: "t", text: t.name }), el("span", { class: "lead", "aria-hidden": "true" }),
        el("span", { class: "g", text: `Grades ${t.grades}` }))))),
    s.planned.length ? el("div", { class: "idx-soon" }, el("p", { class: "idx-soon-h", text: "Coming soon, not playable yet" }),
      el("ul", { "aria-label": `${s.name} topics coming soon` }, s.planned.map((p) => el("li", { text: p })))) : null);
}

async function loadCatalog() {
  const book = document.getElementById("subj-grid");
  let data;
  try {
    const r = await fetch("/api/learn/catalog", { credentials: "same-origin" });
    if (!r.ok) return;                        // keep the static index already on the page
    data = await r.json();
  } catch (e) { return; }
  const c = data.counts;
  document.getElementById("hero-counts").textContent =
    `${c.subjects} subjects, ${c.topics} topics, ${c.questions} questions. Every answer is checked by fixed rules, not guessed by AI.`;
  const revealed = book.querySelector(".idx-sub.in") !== null || !book.classList.contains("idx-live");
  book.replaceChildren(...data.subjects.map(indexColumn));
  if (revealed) book.querySelectorAll(".idx-sub").forEach((s) => s.classList.add("in"));
}
