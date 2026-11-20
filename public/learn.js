/* ELEVIA learning journey (student screens).
   Loaded after app.js and uses its helpers (api, el, show, topbar, panel, pill, go).
   All decisions are made by the backend at /api/learn; this file only shows the current step and sends answers.
   Student and lesson text is always inserted with textContent, never as HTML. */
"use strict";

let learnTimer = null;
function stopLearnTimer() { if (learnTimer) { clearInterval(learnTimer); learnTimer = null; } }

const ANSWER_HELP = {
  fraction: "Type a fraction like 3/4, a whole number like 4, or a mixed number like 1 1/2.",
  integer: "Type a whole number, like 12.",
  choice: "Choose the bigger fraction.",
};

function learnEntryPanel() {
  return panel("Your fractions journey",
    el("p", { text: "A short check-in finds what to practise. ELEVIA double-checks it, teaches the missing step, and retests you on new questions." }),
    el("div", { class: "actions" }, el("a", { class: "btn main", href: "#/learn", text: "Start or continue learning" })));
}

// ------------------------------------------------------------------ loading, errors, shell

function learnMain(me, ...kids) { show(topbar(me), el("main", { class: "board learn" }, kids)); }

async function learnView() {
  stopLearnTimer();
  let me = state.me;
  try { if (!me) me = await api("GET", "/auth/me"); }
  catch (e) { if (e.status === 401) { go("#/login"); return; } learnMain({ user: { full_name: "", role_label: "" } }, panel("Can't load", el("p", { class: "alert bad", text: e.detail }))); return; }
  state.me = me;
  return loadLearn(me);
}

async function loadLearn(me, notice) {
  stopLearnTimer();
  learnMain(me, panel("Getting your journey ready…", el("p", { class: "hint", role: "status", text: "One moment." })));
  try {
    renderLearn(me, await api("GET", "/learn/state"), notice);
  } catch (e) {
    if (e.status === 401) { go("#/login"); return; }
    learnMain(me, panel("We couldn't open your learning journey",
      el("p", { class: "alert bad", role: "alert", text: e.status === 403 ? "The learning area is for students and independent learners." : e.detail }),
      el("p", { class: "hint", text: "Your progress is saved. Nothing was lost." }),
      el("div", { class: "actions" },
        e.status === 403 ? null : el("button", { class: "btn main", type: "button", text: "Try again", onClick: () => loadLearn(me) }),
        el("a", { class: "btn", href: "#/home", text: "Back to home" }))));
  }
}

// ------------------------------------------------------------------ shared pieces

function journeyBar(st) {
  const cur = st.journey.findIndex((s) => s.status === "current");
  const done = st.journey.every((s) => s.status === "done");
  const label = cur >= 0 ? `Step ${cur + 1} of ${st.journey.length}: ${st.journey[cur].label}` : (done ? "All steps finished" : "Your learning journey");
  return el("nav", { class: "journey-wrap", "aria-label": "Your learning journey" },
    el("p", { class: "journey-now", text: label + (st.round > 1 && st.phase !== "done" ? ` · Round ${st.round}` : "") }),
    el("ol", { class: "journey" }, st.journey.map((s, i) =>
      el("li", { class: "step " + s.status, "aria-current": s.status === "current" ? "step" : null },
        el("span", { class: "dot", "aria-hidden": "true", text: s.status === "done" ? "✓" : s.status === "skipped" ? "–" : String(i + 1) }),
        el("span", { class: "lbl", text: s.label }),
        s.status === "skipped" ? el("span", { class: "sr", text: " (not needed)" }) : null))));
}

function whereBox(st) {
  const kids = [el("h1", { class: "learn-title", text: st.phase === "done" ? "Your result" : st.headline })];
  if (st.testing_on && st.testing_on.length)
    kids.push(el("p", { class: "line" }, el("strong", { text: "You're being tested on: " }), st.testing_on.join(", ")));
  if (st.why && st.phase !== "done") kids.push(el("p", { class: "line" }, el("strong", { text: "Why: " }), st.why));
  if (st.why_learning) kids.push(el("p", { class: "line" }, el("strong", { text: "Why this lesson: " }), st.why_learning));
  return el("section", { class: "panel where" }, kids);
}

function gapBox(st) {
  if (!st.gap || st.gap.state === "none" || st.phase === "done") return null;
  const icon = { checking: "?", verified: "✓", not_supported: "✓", unclear: "…", resolved: "★", still_present: "↻" }[st.gap.state] || "";
  return el("section", { class: "panel gapbox " + st.gap.state, "aria-label": "Has the suspected gap been verified?" },
    el("span", { class: "gapicon", "aria-hidden": "true", text: icon }),
    el("div", {}, el("h2", { text: st.gap.headline }), el("p", { style: "margin:4px 0 0", text: st.gap.text })));
}

function skillsPanel(st) {
  const pillKind = { mastered: "ok", developing: "wait", needs_practice: "bad", not_assessed: "off" };
  const items = st.skills.filter((s) => s.attempts || s.status !== "not_assessed");
  return el("details", { class: "panel skills" },
    el("summary", { text: "Your fraction skills" }),
    items.length
      ? el("ul", { class: "list" }, items.map((s) => el("li", { class: "item" }, el("span", { class: "grow", text: s.name }),
          el("span", { class: "hint", text: s.attempts ? `${s.correct}/${s.attempts} right so far` : "" }), pill(s.label, pillKind[s.status] || "off"))))
      : el("p", { class: "hint", text: "Nothing checked yet. Your skills show up here after the check-in." }),
    st.rounds && st.rounds.length ? el("div", {},
      el("h3", { text: "Your rounds" }),
      el("ul", { class: "list" }, st.rounds.map((r) => el("li", { class: "item" },
        el("span", { class: "grow", text: r.skill ? `${r.outcome}: ${r.skill}` : r.outcome }), el("span", { class: "hint", text: fmt(r.date) }))))) : null);
}

function renderLearn(me, st, notice) {
  stopLearnTimer();
  const body = {
    welcome: () => welcomePanel(me, st), start: () => welcomePanel(me, st),
    checkin: () => questionPanel(me, st), verify: () => questionPanel(me, st), retest: () => questionPanel(me, st),
    learn: () => learnPanels(me, st), retest_wait: () => retestWaitPanel(me, st),
    teacher_wait: () => teacherPanel(me, st), done: () => donePanel(me, st),
  }[st.phase];
  const parts = body ? body() : [panel("Something unexpected", el("p", { text: "Please refresh the page. Your progress is saved." }))];
  learnMain(me,
    notice ? el("p", { class: "alert good", role: "status", text: notice }) : null,
    journeyBar(st), whereBox(st), gapBox(st), ...parts, skillsPanel(st),
    el("p", { class: "hint center", text: "ELEVIA points out possible gaps in what you know from your answers. It isn't a medical or psychological test." }));
  const first = root.querySelector("input[type=text]"); if (first) first.focus({ preventScroll: true });
}

// ------------------------------------------------------------------ welcome / start

function welcomePanel(me, st) {
  const sel = el("select", { id: "grade", "aria-label": "Your grade" },
    el("option", { value: "", text: "Choose your grade" }), (st.grades || []).map((g) => el("option", { value: String(g), text: `Grade ${g}` })));
  const err = el("p", { class: "alert bad", role: "alert", hidden: true });
  const btn = el("button", { class: "btn main", type: "button", text: st.phase === "welcome" ? "Start the check-in" : st.next_action.label });
  btn.addEventListener("click", async () => {
    err.hidden = true;
    if (st.needs_grade && !sel.value) { err.textContent = "Please choose your grade first."; err.hidden = false; sel.focus(); return; }
    btn.disabled = true; btn.textContent = "Getting your questions ready…";
    try {
      const next = await api("POST", "/learn/start", st.needs_grade ? { grade: Number(sel.value) } : {});
      renderLearn(me, next);
    } catch (e) { err.textContent = e.detail; err.hidden = false; btn.disabled = false; btn.textContent = "Try again"; }
  });
  return [panel("How it works",
    el("ol", { class: "how" },
      el("li", { text: "Check-in: 5 fraction questions." }),
      el("li", { text: "Double-check: if something looks like a gap, 2 new questions make sure." }),
      el("li", { text: "Learn & practise: a short lesson with examples, only for a confirmed gap." }),
      el("li", { text: "Retest: 3 new questions later. Get 2 right to close the gap." })),
    st.needs_grade ? el("div", { class: "field" }, el("label", { for: "grade", text: "Which grade are you in?" }), sel) : null,
    err, el("div", { class: "actions" }, btn))];
}

// ------------------------------------------------------------------ questions (check-in, double-check, retest, practice)

function questionPanel(me, st, practice) {
  const a = st.assessment;
  const q = a.questions.find((x) => !x.answered);
  if (!q) return [panel("All questions answered", el("button", { class: "btn main", type: "button", text: "Continue", onClick: () => loadLearn(me) }))];
  const isLast = a.answered + 1 >= a.total;
  const kind = a.kind;
  const box = el("section", { class: "panel q", "aria-labelledby": "qprompt" });
  const form = el("form", { novalidate: true, class: "qform" });
  const err = el("p", { class: "alert bad", role: "alert", hidden: true });
  const status = el("p", { class: "hint", role: "status" });
  const help = el("p", { class: "hint", text: ANSWER_HELP[q.input_kind] || ANSWER_HELP.fraction });
  let input;
  if (q.input_kind === "choice") {
    input = el("div", { class: "choices", role: "radiogroup", "aria-labelledby": "qprompt" }, q.choices.map((c, i) =>
      el("label", { class: "choice" }, el("input", { type: "radio", name: "answer", value: c, id: "c" + i }), el("span", { text: c }))));
  } else {
    input = el("input", { type: "text", name: "answer", class: "answer-input", autocomplete: "off", autocapitalize: "off",
      spellcheck: "false", maxlength: "20", "aria-label": "Your answer", "aria-describedby": "ahelp" });
  }
  help.id = "ahelp";
  const submit = el("button", { class: "btn main", type: "submit", text: isLast ? (practice ? "Check my answer" : "Submit my last answer") : "Check my answer" });
  const hintBox = el("div", { class: "hintbox", hidden: true, "aria-live": "polite" });
  let hintLevel = 0;
  const hintBtn = kind === "practice" ? el("button", { class: "btn small", type: "button", text: "Show a hint" }) : null;
  if (hintBtn) hintBtn.addEventListener("click", async () => {
    hintBtn.disabled = true;
    try {
      const h = await api("GET", `/learn/hint?assessment_id=${a.id}&question_id=${encodeURIComponent(q.id)}&level=${hintLevel + 1}`);
      hintLevel = h.level; hintBox.hidden = false; hintBox.textContent = `Hint ${h.level} of ${h.total}: ${h.hint}`;
      hintBtn.textContent = "Show another hint"; hintBtn.disabled = h.level >= h.total;
    } catch (e) { err.textContent = e.detail; err.hidden = false; hintBtn.disabled = false; }
  });

  let inflight = false;
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (inflight) return;                                  // no double submissions
    err.hidden = true;
    const checked = q.input_kind === "choice" ? form.querySelector("input[name=answer]:checked") : null;
    const text = (q.input_kind === "choice" ? (checked ? checked.value : "") : input.value).trim();
    if (!text) { err.textContent = q.input_kind === "choice" ? "Please choose one." : "Please type an answer first."; err.hidden = false; return; }
    inflight = true; submit.disabled = true;
    status.textContent = isLast && kind !== "practice" ? "Checking your answers… this can take a few seconds." : "Saving your answer…";
    try {
      const r = await api("POST", "/learn/answer", { assessment_id: a.id, question_id: q.id, answer: text, hints_used: hintLevel });
      if (!r.accepted) { err.textContent = r.error || "Please check your answer."; err.hidden = false; input.focus && input.focus(); return; }
      if (r.duplicate) { renderLearn(me, r.state, "That answer was already saved, so we moved on."); return; }
      showFeedback(me, box, q, r, kind, isLast);
    } catch (e) {
      if (e.status === 409 || e.status === 404) { loadLearn(me, "That was already saved. Here is where you are."); return; }
      err.textContent = e.status === 0 ? e.detail + " Your answer is still here. Try again." : e.detail;
      err.hidden = false;
    } finally { inflight = false; if (submit.isConnected) submit.disabled = false; status.textContent = ""; }
  });
  form.append(input, help, err, el("div", { class: "actions" }, submit, hintBtn || false), hintBox, status);

  box.append(
    el("p", { class: "qcount", text: `${kind === "practice" ? "Practice" : kind === "retest" ? "Retest" : kind === "verification" ? "Double-check" : "Check-in"} · question ${a.answered + 1} of ${a.total}` }),
    el("p", { class: "prompt", id: "qprompt", text: q.prompt }), form,
    kind === "practice" && a.answered >= 2 ? finishPracticeButton(me, a) : null);
  return [box];
}

function finishPracticeButton(me, a) {
  const b = el("button", { class: "btn", type: "button", text: "I'm done practising: go to my retest" });
  b.addEventListener("click", async () => {
    b.disabled = true; b.textContent = "Scheduling your retest…";
    try { renderLearn(me, await api("POST", "/learn/practice/finish", { assessment_id: a.id })); }
    catch (e) { b.disabled = false; b.textContent = "Try again"; b.after(el("p", { class: "alert bad", role: "alert", text: e.detail })); }
  });
  return el("div", { class: "finish" }, b);
}

function showFeedback(me, box, q, r, kind, isLast) {
  const f = r.feedback;
  const good = f.is_correct;
  const card = el("div", { class: "feedback " + (good ? "good" : "bad"), role: "status" },
    el("h2", { text: good ? "Correct!" : "Not quite" }));
  if (kind === "practice") {
    if (!good) card.append(el("p", { text: `The answer is ${f.expected}.` }));
    if (f.solution && f.solution.length) card.append(el("ol", { class: "sol" }, f.solution.map((s) => el("li", { text: s }))));
  } else if (f.message) {
    card.append(el("p", { text: f.message }));
  }
  (f.notes || []).forEach((n) => card.append(el("p", { class: "hint", text: n })));
  const nextLabel = !isLast ? "Next question"
    : kind === "diagnostic" ? "See what ELEVIA found" : kind === "verification" ? "See the result of the double-check"
    : kind === "practice" ? "Continue" : "See my retest result";
  const nextBtn = el("button", { class: "btn main", type: "button", text: nextLabel, onClick: () => renderLearn(me, r.state) });
  box.replaceChildren(
    el("p", { class: "qcount", text: "Question answered" }),
    el("p", { class: "prompt", text: q.prompt }), card, el("div", { class: "actions" }, nextBtn));
  nextBtn.focus();
}

// ------------------------------------------------------------------ learn (lesson + practice)

function learnPanels(me, st) {
  const out = [];
  if (st.previous_retest && !st.previous_retest.passed) {
    out.push(el("section", { class: "panel notice" },
      el("h2", { text: `Last retest: ${st.previous_retest.score.correct} out of ${st.previous_retest.score.total}` }),
      el("p", { text: "That's okay. Getting this wrong the first time is common. Here is a fresh lesson and new practice questions, and then a new retest with different questions." })));
  }
  const l = st.lesson;
  if (l) {
    out.push(el("section", { class: "panel lesson" },
      el("h2", { text: l.title }),
      el("p", { class: "bigidea", text: l.big_idea }),
      el("div", { class: "note", text: l.personal_note }),
      el("h3", { text: "Step by step" }),
      el("ol", { class: "steps" }, l.steps.map((s) => el("li", { text: s }))),
      el("p", { class: "sense", text: l.sense_check }),
      el("h3", { text: "Worked examples" }),
      l.worked_examples.map((ex, i) => el("details", { class: "example", open: i === 0 },
        el("summary", { text: ex.prompt.replace(" = ?", "") + " = " + ex.answer }),
        el("ol", { class: "sol" }, ex.steps.map((s) => el("li", { text: s })))))));
  }
  if (st.assessment) {
    out.push(el("p", { class: "hint", text: l ? l.practice_note : "" }));
    out.push(...questionPanel(me, st, true));
  }
  return out;
}

// ------------------------------------------------------------------ retest waiting

function fmtLeft(sec) {
  if (sec <= 0) return "any moment now";
  const h = Math.floor(sec / 3600), m = Math.ceil((sec % 3600) / 60);
  return h ? `${h} h ${m} min` : `${m} min`;
}

function retestWaitPanel(me, st) {
  const r = st.retest;
  const target = Date.parse(r.available_at);
  const left = el("p", { class: "countdown", role: "timer" });
  const err = el("p", { class: "alert bad", role: "alert", hidden: true });
  const start = el("button", { class: "btn main", type: "button" });
  const refresh = () => {
    const sec = Math.max(0, Math.round((target - Date.now()) / 1000));
    const open = sec === 0 || r.unlocked;
    left.textContent = open ? "Your retest is ready." : `Unlocks in ${fmtLeft(sec)} (${fmt(r.available_at)})`;
    start.textContent = open ? "Start my retest" : "Start now (demo shortcut)";
    start.hidden = !open && !r.can_start_early;
    return open;
  };
  start.addEventListener("click", async () => {
    err.hidden = true; start.disabled = true;
    try { renderLearn(me, await api("POST", "/learn/retest/start", { early: !refresh() })); }
    catch (e) { err.textContent = e.detail; err.hidden = false; start.disabled = false; }
  });
  refresh();
  learnTimer = setInterval(() => { if (refresh() && !r.unlocked) { r.unlocked = true; } }, 30000);
  return [panel("Your retest",
    left,
    el("p", { text: `ELEVIA waits ${r.delay_hours >= 1 ? Math.round(r.delay_hours) + " hours" : "a little while"} before the retest so it checks what you remember, not just what you just practised.` }),
    !r.unlocked && r.can_start_early ? el("p", { class: "hint", text: "The shortcut is for demos. It is recorded in your history." }) : null,
    err, el("div", { class: "actions" }, start,
      el("button", { class: "btn", type: "button", text: "Check again", onClick: () => loadLearn(me) })))];
}

// ------------------------------------------------------------------ teacher wait and results

function teacherPanel(me, st) {
  return [panel("What happens next",
    el("p", { text: st.why }),
    el("p", { class: "hint", text: "Nothing is lost. Your answers are saved and will still be here." }),
    el("div", { class: "actions" }, el("button", { class: "btn", type: "button", text: "Check again", onClick: () => loadLearn(me) })))];
}

function donePanel(me, st) {
  const o = st.outcome;
  const kids = [el("h2", { text: o.title }), el("p", { text: o.text })];
  if (o.retest) kids.push(el("p", { class: "score", text: `Retest: ${o.retest.score.correct} out of ${o.retest.score.total} right` }));
  const again = el("button", { class: "btn main", type: "button", text: st.next_action.label });
  again.addEventListener("click", async () => {
    again.disabled = true; again.textContent = "Getting your questions ready…";
    try { renderLearn(me, await api("POST", "/learn/start", {})); }
    catch (e) { again.disabled = false; again.textContent = "Try again"; again.before(el("p", { class: "alert bad", role: "alert", text: e.detail })); }
  });
  return [el("section", { class: "panel result " + o.tone }, kids,
    el("p", { class: "hint", text: "Next: a new check-in uses different questions, so ELEVIA can see what has changed." }),
    el("div", { class: "actions" }, again, el("a", { class: "btn", href: "#/home", text: "Back to home" })))];
}
