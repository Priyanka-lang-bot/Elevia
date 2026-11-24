/* ELEVIA learning history: six-month timeline, subject progress, skill map, activity log, class overview.
   Used by the student dashboard (learn.js) and the teacher/parent views (progress.js). Every figure comes from
   /api/learn/history, /api/progress/students/{id}/history or /api/progress/students; nothing is estimated here.
   Text is always inserted with textContent. */
"use strict";

const SKILL_STATE = {
  mastered: { icon: "✓", label: "Mastered (passed a retest)" },
  working: { icon: "●", label: "Gap being worked on" },
  checked: { icon: "○", label: "Checked, not mastered yet" },
  not_started: { icon: "·", label: "Not started" },
};
const EVENT_ICON = { suspected: "?", no_gap: "✓", confirmed: "!", rejected: "–", inconclusive: "≈", lesson: "✎",
  retest_booked: "⏲", retest_passed: "★", retest_failed: "↺", teacher: "T" };

function fmtDay(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function demoBanner(demo) {
  if (!demo) return null;
  return el("section", { class: "panel demo-banner", "aria-label": "Demonstration account" },
    el("p", { class: "demo-tag", text: "Demonstration account" }),
    el("p", { class: "demo-line" },
      el("strong", { text: `Student ID ${demo.student_code}` }),
      demo.class ? ` · ${demo.class}, ${demo.school}, ${demo.academic_year}` : "",
      ` · History ${fmtDay(demo.period_start)} to ${fmtDay(demo.reference_date)}`),
    el("p", { class: "hint", style: "margin:0", text: demo.note }));
}

// One column per month: a bar for answers checked (one series, one colour), with the month's other events
// written underneath as numbers, so nothing is read from colour alone. A table view holds every figure.
function monthChart(months, title) {
  const max = Math.max(1, ...months.map((m) => m.answers));
  const cols = months.map((m) => {
    const h = Math.round((m.answers / max) * 100);
    const tip = `${m.label}: ${m.answers} answers` + (m.accuracy !== null ? `, ${m.accuracy}% right` : "") +
      `; ${m.checkins} check-ins, ${m.confirmed} gaps confirmed, ${m.rejected} rejected, ${m.inconclusive} sent to the teacher; ` +
      `${m.lessons} lessons; retests ${m.retests_passed} passed, ${m.retests_failed} not yet; ${m.mastered} skills mastered; ` +
      `${m.teacher} teacher actions`;
    return el("li", { class: "mcol", tabindex: "0", "aria-label": tip, title: tip },
      el("span", { class: "mval", text: String(m.answers) }),
      el("span", { class: "mbar-wrap", "aria-hidden": "true" }, el("span", { class: "mbar", style: `height:${h}%` })),
      el("span", { class: "mlab", text: m.label.split(" ")[0] }),
      el("span", { class: "macc", text: m.accuracy === null ? "–" : `${m.accuracy}%` }),
      el("span", { class: "mev" },
        m.mastered ? el("span", { class: "mtag ok", text: `★ ${m.mastered}` }) : null,
        m.retests_failed ? el("span", { class: "mtag", text: `↺ ${m.retests_failed}` }) : null,
        m.confirmed ? el("span", { class: "mtag", text: `! ${m.confirmed}` }) : null));
  });
  const table = el("details", { class: "mtable" }, el("summary", { text: "Show as a table" }),
    el("div", { class: "table-wrap" }, el("table", { class: "ptable" },
      el("thead", {}, el("tr", {}, ["Month", "Answers checked", "Right", "Practice answers", "Check-ins", "Gaps confirmed", "Rejected (slips)",
        "Sent to teacher", "Lessons", "Retests passed", "Retests not yet", "Skills mastered", "Teacher actions"].map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, months.map((m) => el("tr", {}, el("th", { scope: "row", text: m.label }),
        [m.answers, m.accuracy === null ? "–" : `${m.accuracy}%`, m.practice, m.checkins, m.confirmed, m.rejected, m.inconclusive, m.lessons,
          m.retests_passed, m.retests_failed, m.mastered, m.teacher].map((v) => el("td", { text: String(v) }))))))));
  return el("figure", { class: "mchart" },
    el("figcaption", { class: "hint", text: title }),
    el("ol", { class: "mcols" }, cols),
    el("p", { class: "mkey hint", text: "Bar: answers checked that month (check-ins, double-checks and retests; practice answers are listed in the table but never count towards progress). Below: % right · ★ skills mastered · ↺ retests not passed yet · ! gaps confirmed." }),
    table);
}

function subjectRows(subjects) {
  return el("ul", { class: "subj-rows" }, subjects.map((s) => {
    const pct = s.skills_total ? Math.round((s.skills_mastered / s.skills_total) * 100) : 0;
    return el("li", { class: "subj-row", style: `--c:${s.color}` },
      el("span", { class: "subj-name", text: s.name }),
      el("span", { class: "subj-meta", text: `${s.topics_started}/${s.topics_total} topics started` }),
      el("span", { class: "meter", role: "img", "aria-label": `${s.skills_mastered} of ${s.skills_total} skills mastered` },
        el("span", { style: `width:${pct}%` })),
      el("span", { class: "subj-meta", text: `${s.skills_mastered}/${s.skills_total} skills mastered` }),
      el("span", { class: "subj-meta", text: s.answers ? `${s.accuracy}% of ${s.answers} answers right` : "No answers yet" }),
      el("span", { class: "subj-meta" + (s.open_gaps ? " warn" : ""), text: s.open_gaps ? `${s.open_gaps} gap${s.open_gaps > 1 ? "s" : ""} open` : "No open gaps" }),
      s.planned.length ? el("span", { class: "hint subj-soon", text: `${s.planned.length} more topics coming soon (not playable yet)` }) : null);
  }));
}

function skillMapView(map) {
  return el("div", { class: "skillmap" },
    el("ul", { class: "sm-key", "aria-label": "Key" }, Object.entries(SKILL_STATE).map(([k, v]) =>
      el("li", { class: "sm-chip " + k }, el("span", { "aria-hidden": "true", text: v.icon }), " " + v.label))),
    map.map((s) => el("section", { class: "sm-subject", style: `--c:${s.color}` },
      el("h3", { text: s.name }),
      el("ul", { class: "sm-topics" }, s.topics.map((t) => el("li", { class: "sm-topic" + (t.started ? "" : " quiet") },
        el("span", { class: "sm-tname", text: t.topic }),
        el("ul", { class: "sm-skills" }, t.skills.map((k) => el("li", { class: "sm-chip " + k.state, title: SKILL_STATE[k.state].label },
          el("span", { "aria-hidden": "true", text: SKILL_STATE[k.state].icon }), " " + k.name,
          el("span", { class: "sr", text: ` (${SKILL_STATE[k.state].label})` }))))))))));
}

function eventLog(events, total) {
  const subjects = [...new Set(events.map((e) => e.subject))];
  const sel = el("select", { id: "evf", "aria-label": "Filter by subject" }, el("option", { value: "", text: "All subjects" }),
    subjects.map((s) => el("option", { value: s, text: s })));
  const list = el("ol", { class: "events" });
  let limit = 20;
  const more = el("button", { class: "btn small", type: "button", text: "Show more" });
  const draw = () => {
    const rows = events.filter((e) => !sel.value || e.subject === sel.value);
    list.replaceChildren(...rows.slice(0, limit).map((e) => el("li", { class: "ev " + e.kind },
      el("span", { class: "ev-ic", "aria-hidden": "true", text: EVENT_ICON[e.kind] || "•" }),
      el("div", { class: "grow" },
        el("p", { class: "ev-t" }, el("strong", { text: e.text }), el("span", { class: "hint", text: ` · ${e.subject}, ${e.topic}` })),
        e.detail ? el("p", { class: "hint ev-d", text: (e.by ? `${e.by}: ` : "") + e.detail }) : null,
        e.due ? el("p", { class: "hint ev-d", text: "Due " + fmt(e.due) }) : null),
      el("time", { class: "hint", datetime: e.date, text: fmtDay(e.date) }))));
    more.hidden = rows.length <= limit;
  };
  sel.addEventListener("change", () => { limit = 20; draw(); });
  more.addEventListener("click", () => { limit += 30; draw(); });
  draw();
  return el("div", {}, el("div", { class: "ev-bar" }, el("label", { for: "evf", class: "hint", text: "Show" }), sel,
    el("span", { class: "hint", text: total > events.length ? `latest ${events.length} of ${total} events` : `${total} events` })), list, more);
}

// The student's (or, for teachers, one student's) whole record. `who` is "you" or the student's first name.
function historyPanels(h, who) {
  if (!h || !h.started) return [];
  const t = h.totals;
  const acc = t.answers ? Math.round((t.correct / t.answers) * 100) : null;
  const span = `${fmtDay(h.period.start)} to ${fmtDay(h.period.end)}`;
  return [
    el("section", { class: "panel", "aria-labelledby": "h-time" },
      el("h2", { id: "h-time", text: who === "you" ? "Your last six months" : "Six-month learning timeline" }),
      el("div", { class: "stats" },
        stat(t.answers, "Answers checked", (acc === null ? "" : `${acc}% right`) + ` · ${t.practice} practice`),
        stat(t.checkins, "Check-ins"),
        stat(t.confirmed, "Gaps confirmed", `${t.rejected} rejected as slips, ${t.inconclusive} sent to the teacher`),
        stat(t.lessons, "Lessons"),
        stat(`${t.retests_passed}/${t.retests_passed + t.retests_failed}`, "Retests passed", `${t.mastered} skills mastered`)),
      monthChart(h.months, `Activity by month, ${span}`)),
    el("section", { class: "panel", "aria-labelledby": "h-sub" }, el("h2", { id: "h-sub", text: "Progress by subject" }),
      subjectRows(h.subjects)),
    el("section", { class: "panel", "aria-labelledby": "h-map" }, el("h2", { id: "h-map", text: "Skill map" }),
      el("p", { class: "hint", style: "margin-top:0", text: "Every skill ELEVIA can teach today, grouped by subject and topic. A skill counts as mastered only after a retest on new questions." }),
      skillMapView(h.skill_map)),
    el("section", { class: "panel", "aria-labelledby": "h-log" }, el("h2", { id: "h-log", text: "Learning history" }),
      el("p", { class: "hint", style: "margin-top:0", text: "Every check-in, double-check, lesson, retest and teacher decision, newest first." }),
      eventLog(h.events, h.event_count)),
  ];
}

// ------------------------------------------------------------------ teacher: class overview

function classOverview(o, label) {
  const t = o.totals;
  const list = (items, empty, row) => items.length ? el("ul", { class: "list" }, items.map(row)) : el("p", { class: "hint", text: empty });
  const link = (uid, name) => el("a", { href: `#/progress/${uid}`, text: name });
  const trendMax = Math.max(1, ...o.trend.map((m) => m.answers));
  return [
    el("section", { class: "panel", "aria-labelledby": "co-h" },
      el("h2", { id: "co-h", text: `Class overview · ${label}` }),
      el("div", { class: "stats" },
        stat(t.students, "Students", `${t.started} have started`),
        stat(t.open_confirmed_gaps, "Confirmed gaps open"),
        stat(t.upcoming_retests, "Retests coming up"),
        stat(t.mastered_recently, "Skills mastered", "in the last 45 days"),
        stat(t.needs_attention, "Need your attention")),
      el("div", { class: "two" },
        el("div", {}, el("h3", { text: "Students who need attention" }),
          list(o.needs_attention, "Nobody right now.", (a) => el("li", { class: "item" },
            el("span", { class: "grow" }, link(a.user_id, a.student), el("span", { class: "hint", text: " · " + a.reasons.join("; ") }))))),
        el("div", {}, el("h3", { text: "Upcoming retests" }),
          list(o.upcoming_retests, "No retests booked.", (r) => el("li", { class: "item" },
            el("span", { class: "grow" }, link(r.user_id, r.student), el("span", { class: "hint", text: ` · ${r.topic}` })),
            el("span", { class: "hint", text: fmt(r.due) })))))),
    el("section", { class: "panel", "aria-labelledby": "cs-h" }, el("h2", { id: "cs-h", text: "By subject" }),
      el("div", { class: "table-wrap" }, el("table", { class: "ptable" },
        el("thead", {}, el("tr", {}, ["Subject", "Students active", "Answers", "Right", "Confirmed gaps open", "Skills mastered"].map((h) => el("th", { scope: "col", text: h })))),
        el("tbody", {}, o.subjects.map((s) => el("tr", {},
          el("th", { scope: "row" }, el("span", { class: "subj-dot", style: `--c:${s.color}`, "aria-hidden": "true" }), s.name),
          el("td", { text: String(s.students) }), el("td", { text: String(s.answers) }),
          el("td", { text: s.accuracy === null ? "–" : `${s.accuracy}%` }), el("td", { text: String(s.open_gaps) }),
          el("td", { text: String(s.mastered) })))))),
      el("h3", { text: "Class activity by month" }),
      el("ol", { class: "mcols small" }, o.trend.map((m) => {
        const tip = `${m.label}: ${m.answers} answers` + (m.accuracy !== null ? `, ${m.accuracy}% right` : "") + `, ${m.active_students} students active, ${m.confirmed} gaps confirmed, ${m.mastered} skills mastered`;
        return el("li", { class: "mcol", tabindex: "0", title: tip, "aria-label": tip },
          el("span", { class: "mval", text: String(m.answers) }),
          el("span", { class: "mbar-wrap", "aria-hidden": "true" }, el("span", { class: "mbar", style: `height:${Math.round((m.answers / trendMax) * 100)}%` })),
          el("span", { class: "mlab", text: m.label.split(" ")[0] }),
          el("span", { class: "macc", text: m.accuracy === null ? "–" : `${m.accuracy}%` }),
          el("span", { class: "mev" }, m.mastered ? el("span", { class: "mtag ok", text: `★ ${m.mastered}` }) : null));
      })),
      el("p", { class: "mkey hint", text: "Bar: answers checked by the class that month. Below: % right · ★ skills mastered." })),
    el("section", { class: "panel", "aria-labelledby": "ci-h" }, el("h2", { id: "ci-h", text: "Class insights" }),
      el("p", { class: "hint", style: "margin-top:0", text: "Worked out from your students' saved answers, double-checks, retests and your decisions." }),
      el("div", { class: "insight-grid" },
        el("div", {}, el("h3", { text: "Topics causing difficulty" }),
          list(o.difficult_topics, "None yet.", (x) => el("li", { class: "item" }, el("span", { class: "grow", text: x.topic }),
            el("span", { class: "hint", text: `${x.count} confirmed gap${x.count > 1 ? "s" : ""} or failed retest${x.count > 1 ? "s" : ""}` })))),
        el("div", {}, el("h3", { text: "Most frequent misconceptions" }),
          list(o.frequent_misconceptions, "None confirmed yet.", (x) => el("li", { class: "item" }, el("span", { class: "grow", text: x.label }),
            el("span", { class: "hint", text: `${x.count} student${x.count > 1 ? "s" : ""}` })))),
        el("div", {}, el("h3", { text: "Repeated unsuccessful retests" }),
          list(o.repeated_failed_retests, "Nobody has failed the same retest twice.", (x) => el("li", { class: "item" },
            el("span", { class: "grow" }, link(x.user_id, x.student), el("span", { class: "hint", text: ` · ${x.topic}` })),
            el("span", { class: "hint", text: `${x.failed} not passed · ${x.status}` })))),
        el("div", {}, el("h3", { text: "Most improved" }),
          list(o.most_improved, "No retest has been passed after a failed one yet.", (x) => el("li", { class: "item" },
            el("span", { class: "grow" }, link(x.user_id, x.student), el("span", { class: "hint", text: ` · ${x.skill}` })),
            el("span", { class: "hint", text: `passed after ${x.failed_first} failed retest${x.failed_first > 1 ? "s" : ""}, ${fmtDay(x.date)}` })))),
        el("div", {}, el("h3", { text: "Recently mastered" }),
          list(o.recently_mastered, "Nothing in the last 45 days.", (x) => el("li", { class: "item" },
            el("span", { class: "grow" }, link(x.user_id, x.student), el("span", { class: "hint", text: ` · ${x.skill}` })),
            el("span", { class: "hint", text: fmtDay(x.date) })))))),
  ];
}
