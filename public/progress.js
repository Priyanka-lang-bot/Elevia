/* ELEVIA progress views for teachers, parents and people a learner shares with.
   Uses helpers from app.js. All data comes from /api/progress, which checks permissions on every request. */
"use strict";

const STAGE_KIND = { diagnostic: "wait", verification: "wait", learning: "now", retest_pending: "wait", retest: "now",
  teacher_review: "bad", completed: "ok", closed: "ok" };

const ACTION_LABEL = { confirm_gap: "Confirmed the gap", reject_gap: "Rejected the gap", change_focus: "Changed the focus", note: "Added a note" };

function childSummary(s) {
  if (!s.started) return "Hasn't started any topic yet.";
  const parts = [`Has worked on ${s.topics_started} topic${s.topics_started === 1 ? "" : "s"} and mastered ${s.skills_mastered} skill${s.skills_mastered === 1 ? "" : "s"} (a skill counts as mastered only after passing a retest on new questions).`];
  if (s.active.length) parts.push("Right now: " + s.active.map((a) => `${a.topic} (${a.stage_label.toLowerCase()})`).join(", ") + ".");
  if (s.confirmed_gaps) parts.push(`${s.confirmed_gaps} confirmed gap${s.confirmed_gaps === 1 ? " is" : "s are"} being worked on.`);
  if (s.needs_review) parts.push("One topic is waiting for the teacher's decision.");
  return parts.join(" ");
}

async function progressPanels(me) {
  let data;
  try { data = await api("GET", "/progress/students"); }
  catch (e) { return [panel("Students' learning", el("p", { class: "alert bad", text: e.detail }))]; }
  const teacher = me.user.role === "teacher";
  const head = teacher ? "Students' learning" : me.user.role === "parent" ? "Your children's learning" : "Learning shared with you";
  if (!data.groups.length) {
    return [panel(head, el("p", { class: "hint", text: teacher
      ? "No approved students yet. Students appear here after you approve them for your class."
      : "Nothing to show yet. Progress appears once your child starts learning and you've allowed 'See progress and skills'." }))];
  }
  const out = [];
  if (teacher) {
    out.push(panel("Review queue",
      data.queue.length ? el("ul", { class: "queue" }, data.queue.map((q) => el("li", { class: "queue-item" },
        el("div", { class: "grow" }, el("strong", { text: `${q.student} · ${q.topic}` }),
          el("span", { class: "hint", text: (q.skill ? `${q.skill}${q.suspected ? ` (suspected: ${q.suspected})` : ""} · ` : "") + q.reason }),
          el("span", { class: "hint", text: "Waiting since " + fmt(q.since) })),
        el("a", { class: "btn small main", href: `#/progress/${q.user_id}`, text: "Review" }))))
        : el("p", { class: "hint", text: "Nothing waiting. Cases appear here when ELEVIA isn't sure and needs your decision." })));
    for (const g of data.groups) if (g.overview) out.push(...classOverview(g.overview, g.label));
  }
  out.push(panel(head, ...data.groups.map((g) => el("div", { class: "pgroup" },
    teacher || data.groups.length > 1 ? el("h3", { text: g.label }) : null,
    g.insights ? el("div", { class: "insights" },
      el("span", { class: "chip", text: `${g.insights.started}/${g.insights.students} students started` }),
      el("span", { class: "chip" + (g.insights.needs_review ? " warn" : ""), text: `${g.insights.needs_review} need your review` }),
      g.insights.common_gaps.length ? el("span", { class: "hint", text: "Most common confirmed misconceptions: " + g.insights.common_gaps.map((c) => `${c.label} (${c.students})`).join("; ") })
        : el("span", { class: "hint", text: "No confirmed misconceptions in this class yet." })) : null,
    teacher ? el("div", { class: "table-wrap" }, el("table", { class: "ptable" },
      el("thead", {}, el("tr", {}, ["Student", "Now working on", "Confirmed gaps", "Mastered", "Answers right", ""].map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, g.students.map((s) => el("tr", {},
        el("th", { scope: "row" }, s.name, s.student_code ? el("span", { class: "hint", text: ` ${s.student_code}` }) : null,
          s.needs_review ? pill("needs review", "bad") : null),
        el("td", { text: s.started ? (s.active.map((a) => `${a.topic}: ${a.stage_label}`).join("; ") || "Nothing in progress") : "Not started yet" }),
        el("td", { text: String(s.confirmed_gaps) }),
        el("td", { text: String(s.skills_mastered) }),
        el("td", { text: s.answers ? `${s.correct}/${s.answers}` : "0" }),
        el("td", {}, el("a", { class: "btn small", href: `#/progress/${s.user_id}`, text: "Open" })))))))
      : el("ul", { class: "kids" }, g.students.map((s) => el("li", { class: "kid" },
        el("div", { class: "kid-head" }, el("strong", { text: s.name }), s.last_activity ? el("span", { class: "hint", text: "Last active " + fmt(s.last_activity) }) : null),
        el("p", { style: "margin:0;line-height:1.55", text: childSummary(s) }),
        el("div", { class: "stats" }, stat(s.topics_started, "Topics"), stat(s.skills_mastered, "Skills mastered"), stat(s.confirmed_gaps, "Gaps being worked on")),
        el("a", { class: "btn small", href: `#/progress/${s.user_id}`, text: "See details" }))))))));
  if (teacher) {
    out.push(panel("Intervention history",
      data.interventions.length ? el("ul", { class: "list" }, data.interventions.map((i) => el("li", { class: "item" },
        el("span", { class: "grow" }, el("strong", { text: `${ACTION_LABEL[i.action] || i.action}` }), ` · ${i.student}, ${i.topic}: `, el("span", { class: "hint", text: i.reason })),
        el("span", { class: "hint", text: `${i.by} · ${fmt(i.date)}` }))))
        : el("p", { class: "hint", text: "Your decisions and notes will be listed here, with the reason you gave." })));
  }
  return out;
}

async function progressDetailView(uid) {
  let me = state.me;
  try { if (!me) me = state.me = await api("GET", "/auth/me"); } catch (e) { go("#/login"); return; }
  board(me, panel("Loading…", el("p", { class: "hint", role: "status", text: "One moment." })));
  let d;
  try { d = await api("GET", `/progress/students/${uid}`); }
  catch (e) { board(me, el("a", { href: "#/home", text: "← Back" }), panel("Can't show this student", el("p", { class: "alert bad", text: e.status === 404 ? "You don't have access to this student's progress." : e.detail }))); return; }
  const parts = [el("a", { href: "#/home", text: "← Back to overview" }),
    el("section", { class: "panel" }, el("h1", { class: "learn-title", text: d.name }),
      el("p", { class: "hint", style: "margin:0", text: `Access: ${{ teacher_class: "you teach this student's class", parent_link: "parent (with your child's consent)", share_grant: "shared with you by the learner" }[d.access_via] || d.access_via}` }),
      d.started ? el("div", { class: "stats" }, stat(d.summary.topics_started, "Topics started"), stat(d.summary.confirmed_gaps, "Verified gaps open"),
        stat(d.summary.skills_mastered, "Skills mastered"), stat(d.summary.answers ? `${d.summary.correct}/${d.summary.answers}` : "0", "Answers correct")) : null)];
  if (d.demo) parts.push(demoBanner(d.demo));
  if (!d.started) parts.push(panel("Not started", el("p", { class: "hint", text: "This student hasn't begun any topic yet." })));
  if (d.started) {
    try {
      const h = await api("GET", `/progress/students/${uid}/history`);
      parts.push(...historyPanels(h, d.name.split(" ")[0]));
    } catch (e) { parts.push(panel("Learning history", el("p", { class: "alert bad", text: e.detail }))); }
    if (d.topics.length) parts.push(el("h2", { class: "sec-title", text: d.can_review ? "Evidence and review, topic by topic" : "Topic by topic" }));
  }
  for (const t of d.topics) {
    parts.push(el("section", { class: "panel" }, el("h2", { text: t.topic }),
      el("div", { class: "chips" }, t.skills.map((s) => el("span", { class: "chip" + (s.status === "Mastered" ? " ok" : s.status === "Needs practice" ? " warn" : ""), text: `${s.name}: ${s.status}` }))),
      t.rounds.map((r) => roundCard(me, d, r))));
  }
  board(me, ...parts);
}

function roundCard(me, d, r) {
  const box = el("div", { class: "round" },
    el("div", { class: "round-head" }, el("strong", { text: fmt(r.date) }), pill(r.stage_label, STAGE_KIND[r.stage] || "off")));
  if (r.gap) {
    const g = r.gap;
    box.append(el("dl", { class: "facts" },
      el("dt", { text: "Gap" }), el("dd", { text: `${g.skill} · ${g.status_label}` }),
      g.misconception ? [el("dt", { text: "Misconception" }), el("dd", { text: `${g.misconception}. ${g.explanation || ""}` })] : null,
      g.checker_reason ? [el("dt", { text: "Checker's verdict" }), el("dd", { text: g.checker_reason })] : null,
      g.verified_by ? [el("dt", { text: "Verified by" }), el("dd", { text: g.verified_by.startsWith("teacher:") ? "Teacher: " + g.verified_by.slice(8) : "Automatic double-check" })] : null,
      g.hypothesis ? [el("dt", { text: "Diagnoser" }), el("dd", { text: g.hypothesis })] : null,
      g.evidence.length ? [el("dt", { text: "Check-in answers" }), el("dd", {}, el("ul", {}, g.evidence.map((e) => el("li", { text: `${e.prompt}  →  answered ${e.answer}` }))))] : null,
      g.check_evidence && g.check_evidence.length ? [el("dt", { text: "Double-check answers" }), el("dd", {}, el("ul", {}, g.check_evidence.map((e) =>
        el("li", { text: `${e.prompt}  →  answered ${e.answer} (${e.correct ? "right" : e.supports_gap ? "same mistake again" : "a different mistake"})` }))))] : null,
      g.retests.length ? [el("dt", { text: "Retests" }), el("dd", { text: g.retests.map((x) => `${x.score.correct}/${x.score.total} ${x.passed ? "passed" : "not passed"}`).join(", ") })] : null));
  }
  if (r.plan) box.append(el("p", { class: "hint", style: "margin:0" }, el("strong", { text: "Plan: " }), `${r.plan.focus}. ${r.plan.rationale}`));
  if (r.assessments) box.append(el("p", { class: "hint", style: "margin:0", text: "Assessments: " + r.assessments.map((a) => `${{ diagnostic: "check-in", verification: "double-check", practice: "practice", retest: "retest" }[a.kind]} ${a.correct}/${a.total}`).join(" · ") }));
  if (r.overrides && r.overrides.length) box.append(el("ul", { class: "audit" }, r.overrides.map((o) => el("li", { text: `${fmt(o.date)} · ${o.by} · ${o.action.replace("_", " ")}: ${o.reason}` }))));
  if (r.actions && (r.actions.decide || r.actions.focus)) box.append(reviewForm(me, d, r));
  return box;
}

function reviewForm(me, d, r) {
  const msg = el("p", { class: "alert bad", role: "alert", hidden: true });
  const reason = el("textarea", { id: "why" + r.case_id, rows: 2, maxlength: 500, placeholder: "Why? (required, saved in the audit log)" });
  const focus = el("select", { id: "f" + r.case_id }, el("option", { value: "", text: "Keep ELEVIA's choice" }),
    d.teachable_skills.map((s) => el("option", { value: s.skill_id, text: s.name })));
  const act = async (path, body, btn) => {
    msg.hidden = true;
    if (reason.value.trim().length < 5) { msg.textContent = "Please write a short reason (at least 5 characters)."; msg.hidden = false; reason.focus(); return; }
    btn.disabled = true;
    try { await api("POST", `/progress/cases/${r.case_id}/${path}`, { ...body, reason: reason.value.trim() }); progressDetailView(d.user_id); }
    catch (e) { msg.textContent = e.detail; msg.hidden = false; btn.disabled = false; }
  };
  const buttons = [];
  if (r.actions.decide) {
    const c = el("button", { class: "btn small main", type: "button", text: "Confirm gap and teach" });
    c.addEventListener("click", () => act("decision", { decision: "confirm", focus_skill: focus.value || null }, c));
    const x = el("button", { class: "btn small", type: "button", text: "Reject: no lesson needed" });
    x.addEventListener("click", () => act("decision", { decision: "reject" }, x));
    buttons.push(c, x);
  }
  if (r.actions.focus) {
    const f = el("button", { class: "btn small", type: "button", text: "Change focus to selected skill" });
    f.addEventListener("click", () => { if (!focus.value) { msg.textContent = "Choose a skill first."; msg.hidden = false; return; } act("focus", { focus_skill: focus.value }, f); });
    buttons.push(f);
  }
  return el("div", { class: "review" }, el("h3", { text: "Teacher review" }),
    el("div", { class: "field" }, el("label", { for: "why" + r.case_id, text: "Reason" }), reason),
    el("div", { class: "field" }, el("label", { for: "f" + r.case_id, text: "Focus skill (optional)" }), focus),
    msg, el("div", { class: "actions" }, buttons));
}
