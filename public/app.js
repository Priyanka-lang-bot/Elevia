/* ELEVIA web app: access type, sign-up pathways, consent, and role homes.
   Plain JavaScript, no build step. All decisions are made by the backend at /api;
   this page only shows screens and sends forms. User text is always inserted with
   textContent, never as HTML. */
"use strict";

const root = document.getElementById("app");
const state = { me: null, demo: [] };

// ------------------------------------------------------------------ API

let clientId = "";
try {
  clientId = localStorage.getItem("elevia_client") || "";
  if (!clientId) { clientId = crypto.randomUUID(); localStorage.setItem("elevia_client", clientId); }
} catch (e) { clientId = Math.random().toString(36).slice(2); }

async function api(method, path, body) {
  let res;
  try {
    res = await fetch("/api" + path, {
      method, credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Elevia-Web": "1", "X-Client-Id": clientId },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (e) {
    throw { status: 0, detail: "Can't reach ELEVIA. Check your internet connection and try again." };
  }
  let data = {};
  try { data = await res.json(); } catch (e) { /* empty body */ }
  if (data && data.demo_emails) { state.demo = state.demo.concat(data.demo_emails); }
  if (!res.ok) {
    let detail = data.detail;
    if (Array.isArray(detail)) detail = "Please check the highlighted fields.";
    throw { status: res.status, detail: detail || "Something went wrong.", field: data.field, code: data.code };
  }
  return data;
}

// ------------------------------------------------------------------ tiny DOM helpers

function el(tag, props, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "style") n.setAttribute("style", v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    n.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return n;
}

function decor(html) {  // trusted constant SVG from decor.js
  const d = el("div", { class: "decor-layer", "aria-hidden": "true" });
  d.innerHTML = html;
  return d;
}

let uid = 0;
function field(label, name, opts = {}) {
  const id = "f" + (++uid);
  const input = el(opts.tag || "input", {
    id, name, type: opts.type || "text", placeholder: opts.placeholder, autocomplete: opts.autocomplete,
    required: opts.required, max: opts.max, min: opts.min, value: opts.value, maxlength: opts.maxlength,
    inputmode: opts.inputmode, "aria-describedby": id + "-err",
  });
  const err = el("span", { class: "err", id: id + "-err", role: "status" });
  let control = input;
  if (opts.type === "password") {
    const t = el("button", { type: "button", class: "btn small toggle", "aria-label": "Show password", text: "Show" });
    t.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      t.textContent = show ? "Hide" : "Show";
      t.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
    control = el("div", { class: "pw" }, input, t);
  }
  const wrap = el("div", { class: "field", "data-name": name },
    el("label", { for: id, text: label }), control, opts.hint ? el("span", { class: "hint", text: opts.hint }) : null, err);
  return wrap;
}

function check(label, name, checked) {
  return el("label", { class: "chk" }, el("input", { type: "checkbox", name, checked }), el("span", {}, label));
}

function values(form) {
  const out = {};
  for (const n of form.querySelectorAll("input,select")) {
    if (!n.name) continue;
    if (n.type === "checkbox") {
      if (n.dataset.group) { (out[n.dataset.group] = out[n.dataset.group] || []); if (n.checked) out[n.dataset.group].push(n.value); }
      else out[n.name] = n.checked;
    } else out[n.name] = n.value.trim();
  }
  return out;
}

function clearErrors(form) {
  form.querySelectorAll(".err").forEach((e) => (e.textContent = ""));
  form.querySelectorAll("[aria-invalid]").forEach((e) => e.removeAttribute("aria-invalid"));
  const a = form.querySelector(".alert.bad"); if (a) a.remove();
}

function showError(form, err) {
  const f = err.field && form.querySelector(`.field[data-name="${err.field}"]`);
  if (f) {
    f.querySelector(".err").textContent = err.detail;
    const inp = f.querySelector("input,select"); if (inp) { inp.setAttribute("aria-invalid", "true"); inp.focus(); }
  } else {
    const a = el("p", { class: "alert bad", role: "alert", text: err.detail });
    const btn = form.querySelector("button[type=submit]");
    btn ? btn.before(a) : form.append(a);
  }
}

// Submit helper: disables the button, clears/shows errors.
function onSubmit(form, handler) {
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    clearErrors(form);
    const btn = form.querySelector("button[type=submit]");
    if (btn) btn.disabled = true;
    try { await handler(values(form)); }
    catch (err) { if (err && err.detail) showError(form, err); else { console.error(err); showError(form, { detail: "Something went wrong." }); } }
    finally { if (btn && btn.isConnected) btn.disabled = false; }
  });
  return form;
}

function demoBanner() {
  if (!state.demo.length) return null;
  const box = el("div", { class: "demo", role: "region", "aria-label": "Demo emails" },
    el("strong", { text: "Demo mode: emails aren't really sent. " }),
    "These are the links ELEVIA would have emailed:",
    el("ul", {}, state.demo.slice(-4).map((d) => el("li", {}, `${d.subject} → ${d.to}: `,
      d.link ? el("a", { href: d.link, text: "open link" }) : "no link"))),
    el("button", { class: "btn small", type: "button", style: "margin-top:8px", text: "Hide",
      onClick: () => { state.demo = []; box.remove(); } }));
  return box;
}

function show(...nodes) {
  root.replaceChildren(...nodes.filter(Boolean));
  const b = demoBanner(); if (b) root.append(b);
  const h = root.querySelector("h1"); if (h) { h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true }); }
  window.scrollTo(0, 0);
}

// A centred torn-paper sheet on grid paper.
function sheetPage(children, opts = {}) {
  return el("main", { class: "stage" },
    el("a", { class: "brand logo", href: "#/", text: "ELEVIA" }),
    decor(DECOR.corner),
    el("div", { class: "sheet-wrap" + (opts.wide ? " wide" : "") }, decor(DECOR.sheet),
      el("div", { class: "sheet" }, children)));
}

function title(text, sub) {
  return [el("h1", { class: "brand title", text }), sub ? el("p", { class: "sub", text: sub }) : null];
}

function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }

function age(dob) {
  if (!dob) return null;
  const d = new Date(dob + "T00:00:00"), t = new Date();
  let a = t.getFullYear() - d.getFullYear();
  if (t.getMonth() < d.getMonth() || (t.getMonth() === d.getMonth() && t.getDate() < d.getDate())) a--;
  return a;
}
const today = new Date().toISOString().slice(0, 10);
const fmt = (iso) => { try { return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); } catch (e) { return iso; } };

// ------------------------------------------------------------------ screens: entry

const ICONS = {
  student: '<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#1f2a44" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10V8a5 5 0 0 1 10 0v2"/><rect x="5" y="10" width="14" height="11" rx="3"/><path d="M9 14h6M12 14v3"/></svg>',
  school: '<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#1f2a44" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M5 21V10l7-5 7 5v11"/><path d="M10 21v-5h4v5M9 11h.01M15 11h.01"/></svg>',
  adult: '<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#1f2a44" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h6a2 2 0 0 1 2 2v13a2 2 0 0 0-2-2H4z"/><path d="M20 5h-6a2 2 0 0 0-2 2v13a2 2 0 0 1 2-2h6z"/></svg>',
};

function accessView() {
  const card = (icon, h, line, who, href) => {
    const i = el("span", { "aria-hidden": "true" }); i.innerHTML = ICONS[icon];
    return el("section", { class: "card" }, el("span", { class: "tape", "aria-hidden": "true" }), i,
      el("h2", { text: h }), el("p", { text: line }), el("p", { class: "hint", text: who }),
      el("span", { class: "grow" }), el("a", { class: "btn main", href, text: "Continue", "aria-label": `Continue as ${h}` }));
  };
  show(el("main", { class: "stage" },
    el("a", { class: "brand logo", href: "#/", text: "ELEVIA" }), decor(DECOR.access),
    el("h1", { class: "brand title", style: "font-size:50px;position:relative;z-index:1", text: "How would you like to use ELEVIA?" }),
    el("p", { class: "sub", style: "font-size:17px;margin-top:8px", text: "Pick the option that fits you. Not sure? Ask a parent or teacher." }),
    el("div", { class: "access" },
      card("student", "Individual Student", "I'm learning on my own, outside a school plan.", "Under 18? A parent or guardian approves your account.", "#/student"),
      card("school", "School / Institution", "My school uses ELEVIA and gave me a code.", "Students start here. Teachers and admins use their email invitation.", "#/school"),
      card("adult", "Independent Learner (18+)", "I'm an adult learning for myself.", "You control your account and who sees your progress.", "#/learner")),
    el("p", { class: "center", style: "margin-top:40px;font-weight:600;position:relative;z-index:1" }, "Already have an account? ", el("a", { href: "#/login", text: "Log in" })),
    el("p", { class: "center hint", style: "position:relative;z-index:1;max-width:640px;margin:16px auto 0" },
      "ELEVIA finds possible gaps in what a student has learned, checks them, and teaches the missing step. It is not a medical or psychological assessment.")));
}

function loginView() {
  const form = onSubmit(el("form", { novalidate: true },
    ...title("LOGIN", "Welcome back. Log in to continue."),
    field("Email or username", "identifier", { autocomplete: "username", placeholder: "you@example.com or your username" }),
    field("Password", "password", { type: "password", autocomplete: "current-password", placeholder: "Your password" }),
    el("a", { href: "#/forgot", style: "align-self:flex-end;font-size:14px", text: "Forgot password?" }),
    el("button", { class: "btn main", type: "submit", text: "Log in" }),
    el("p", { class: "center", style: "margin:0;font-weight:600" }, "New here? ", el("a", { href: "#/", text: "Create an account" }))),
    async (v) => { await api("POST", "/auth/login", { identifier: v.identifier, password: v.password }); go("#/home"); });
  form.className = "stack"; form.style.cssText = "display:flex;flex-direction:column;gap:16px";
  show(sheetPage(form));
}

function forgotView() {
  const box = el("div", { style: "display:flex;flex-direction:column;gap:16px" });
  const form = onSubmit(el("form", { novalidate: true, style: "display:flex;flex-direction:column;gap:16px" },
    ...title("RESET", "We'll email you a link to choose a new password."),
    field("Email", "email", { type: "email", autocomplete: "email", placeholder: "you@example.com" }),
    el("button", { class: "btn main", type: "submit", text: "Send reset link" }),
    el("p", { class: "hint center", style: "margin:0", text: "Students without an email: ask your parent or teacher to help." }),
    el("a", { href: "#/login", class: "center", text: "Back to log in" })),
    async (v) => {
      const r = await api("POST", "/auth/forgot-password", { email: v.email });
      box.replaceChildren(...title("CHECK EMAIL"), el("p", { class: "alert good", text: r.message }), el("a", { href: "#/login", class: "center", text: "Back to log in" }));
      show(sheetPage(box));
    });
  box.append(form);
  show(sheetPage(box));
}

function resetView(token) {
  const form = onSubmit(el("form", { novalidate: true, style: "display:flex;flex-direction:column;gap:16px" },
    ...title("NEW PASSWORD"),
    field("New password", "new_password", { type: "password", autocomplete: "new-password", hint: "At least 8 characters." }),
    el("button", { class: "btn main", type: "submit", text: "Save password" })),
    async (v) => {
      const r = await api("POST", "/auth/reset-password", { token, new_password: v.new_password });
      show(sheetPage([...title("DONE"), el("p", { class: "alert good", text: r.message }), el("a", { class: "btn main", href: "#/login", text: "Log in" })]));
    });
  show(sheetPage(form));
}

async function verifyView(token) {
  show(sheetPage([...title("CONFIRMING…")]));
  try {
    await api("POST", "/auth/verify-email", { token });
    show(sheetPage([...title("CONFIRMED", "Your email is confirmed and your account is active."), el("a", { class: "btn main", href: "#/home", text: "Continue" })]));
  } catch (e) {
    show(sheetPage([...title("LINK PROBLEM"), el("p", { class: "alert bad", text: e.detail }), el("a", { class: "btn", href: "#/login", text: "Log in to get a new link" })]));
  }
}

// ------------------------------------------------------------------ pathway 1 + 2 student form

function studentSignupView(school) {
  const parentBox = el("div", { style: "display:flex;flex-direction:column;gap:14px" },
    el("div", { class: "sec", text: "Your parent or guardian" }),
    el("div", { class: "row2" },
      field("Their name", "parent_name", { placeholder: "Parent's full name", autocomplete: "off" }),
      field("Their email", "parent_email", { type: "email", placeholder: "parent@example.com", autocomplete: "off" })),
    el("div", { class: "note", text: "Because you're under 18, we'll email your parent. Your account unlocks once they check it and say yes." }));
  const dob = field("Date of birth", "date_of_birth", { type: "date", max: today, autocomplete: "bday" });
  const form = onSubmit(el("form", { novalidate: true, style: "display:flex;flex-direction:column;gap:14px" },
    ...title("SIGN UP", school ? `Joining ${school.school_name} · ${school.class_label}` : "Individual student"),
    el("div", { class: "sec", text: "About you" }),
    field("Full name", "full_name", { autocomplete: "name", placeholder: "Your full name" }),
    el("div", { class: "row2" }, dob, field("Username", "username", { autocomplete: "username", placeholder: "e.g. riya_s", hint: "Letters, numbers, dots or underscores." })),
    field("Password", "password", { type: "password", autocomplete: "new-password", hint: "At least 8 characters." }),
    field("Your email (optional)", "student_email", { type: "email", autocomplete: "email", placeholder: "Only if you have one" }),
    parentBox,
    el("div", { class: "actions" }, el("a", { class: "btn", href: school ? "#/school" : "#/", text: "Back" }),
      el("button", { class: "btn main grow", type: "submit", text: "Create my account" }))),
    async (v) => {
      const body = { full_name: v.full_name, date_of_birth: v.date_of_birth, username: v.username, password: v.password,
        student_email: v.student_email || null, parent_name: v.parent_name || null, parent_email: v.parent_email || null };
      try {
        if (school) await api("POST", "/auth/register/school-student", { ...body, code: school.code });
        else await api("POST", "/auth/register/student", body);
      } catch (e) {
        if (e.code === "use_learner") e.detail += " ";
        throw e;
      }
      go("#/home");
    });
  const dobInput = dob.querySelector("input");
  dobInput.addEventListener("change", () => {
    const a = age(dobInput.value);
    parentBox.hidden = a !== null && a >= 18;
    if (!school && a !== null && a >= 18) {
      clearErrors(form);
      showError(form, { field: "date_of_birth", detail: "You're 18 or older, so please use the Independent Learner option." });
    }
  });
  show(sheetPage(form, { wide: true }));
}

function schoolCodeView() {
  const area = el("div", { style: "display:flex;flex-direction:column;gap:16px" });
  const form = onSubmit(el("form", { novalidate: true, style: "display:flex;flex-direction:column;gap:16px" },
    ...title("SCHOOL CODE", "Your teacher shares this code with your class."),
    el("div", { class: "codebox" }, field("Referral code", "code", { placeholder: "ELV-XXXX-XXXX", autocomplete: "off", maxlength: 14 })),
    el("button", { class: "btn main", type: "submit", text: "Check code" })),
    async (v) => {
      const r = await api("POST", "/auth/school-code/validate", { code: v.code });
      const found = el("div", { class: "found" }, el("strong", { text: "✓" }),
        el("div", {}, el("div", { style: "font-weight:800;font-size:17px", text: r.school_name }), el("div", { class: "hint", style: "font-size:15px", text: r.class_label })));
      area.replaceChildren(form, found,
        el("p", { class: "hint center", style: "margin:0", text: "Is this your school and class? If not, check the code with your teacher." }),
        el("button", { class: "btn main", type: "button", text: "Yes, continue",
          onClick: () => studentSignupView({ code: v.code, school_name: r.school_name, class_label: r.class_label }) }));
    });
  area.append(form, el("p", { class: "center hint", style: "margin:0", text: "Teacher or school admin? Open the invitation link from your email." }),
    el("a", { class: "center", href: "#/", text: "Back" }));
  show(sheetPage(area));
}

// ------------------------------------------------------------------ pathway 3

function learnerSignupView() {
  const form = onSubmit(el("form", { novalidate: true, style: "display:flex;flex-direction:column;gap:14px" },
    ...title("SIGN UP", "For adults learning on their own."),
    field("Full name", "full_name", { autocomplete: "name" }),
    field("Date of birth", "date_of_birth", { type: "date", max: today, autocomplete: "bday", hint: "You need to be 18 or over for this option." }),
    field("Email", "email", { type: "email", autocomplete: "email", placeholder: "you@example.com" }),
    field("Password", "password", { type: "password", autocomplete: "new-password", hint: "At least 8 characters." }),
    el("div", { class: "field", "data-name": "accept_terms" },
      el("label", { class: "chk" }, el("input", { type: "checkbox", name: "accept_terms" }),
        el("span", {}, "I agree to the terms and privacy notice. Nothing is shared with anyone unless I choose to share it.")),
      el("span", { class: "err" })),
    el("button", { class: "btn main", type: "submit", text: "Create account" }),
    el("p", { class: "hint center", style: "margin:0", text: "We'll email you a link to confirm your address." })),
    async (v) => { await api("POST", "/auth/register/learner", v); go("#/home"); });
  show(sheetPage(form));
}

// ------------------------------------------------------------------ parent consent (from the email)

async function consentView(token) {
  let info;
  try { info = await api("POST", "/consent/info", { token }); }
  catch (e) {
    show(sheetPage([...title("LINK PROBLEM"), el("p", { class: "alert bad", text: e.detail }),
      el("p", { class: "hint", text: "Ask your child to send a new request from their ELEVIA screen." })]));
    return;
  }
  const kid = info.child_first_name;
  const perms = Object.entries(info.permissions).map(([k, label]) => {
    const i = el("input", { type: "checkbox", name: "perm_" + k, value: k, checked: info.default_permissions.includes(k) });
    i.dataset.group = "permissions";
    return el("label", { class: "chk" }, i, el("span", { text: label }));
  });
  const accountFields = info.parent_has_account
    ? [el("div", { class: "sec", text: "Log in to your parent account" }),
       el("p", { class: "hint", style: "margin:0", text: `You already have an ELEVIA parent account (${info.parent_email}).` }),
       field("Password", "password", { type: "password", autocomplete: "current-password" })]
    : [el("div", { class: "sec", text: "Your parent account" }),
       field("Your full name", "full_name", { autocomplete: "name", value: info.parent_name || "" }),
       field("Create a password", "password", { type: "password", autocomplete: "new-password", hint: `For ${info.parent_email}. At least 8 characters.` })];
  const declineBtn = el("button", { class: "btn danger", type: "button", text: "Decline and delete" });
  let armed = false;
  declineBtn.addEventListener("click", async () => {
    if (!armed) { armed = true; declineBtn.textContent = "Tap again to confirm"; return; }
    try {
      const r = await api("POST", "/consent/decline", { token });
      show(sheetPage([...title("DECLINED"), el("p", { class: "alert good", text: r.message })]));
    } catch (e) { declineBtn.textContent = e.detail; }
  });
  const form = onSubmit(el("form", { novalidate: true, style: "display:flex;flex-direction:column;gap:14px" },
    ...title("PARENT CONSENT"),
    el("p", { class: "center", style: "margin:0;font-weight:600;font-size:16px", text: `${kid} wants to use ELEVIA. Their account stays locked until you decide.` }),
    el("div", { class: "sec", text: "What ELEVIA keeps" }),
    el("ul", { style: "margin:0;padding-left:20px;line-height:1.6" },
      el("li", { text: "Name, date of birth and username" }),
      el("li", { text: "Answers to practice questions and the progress worked out from them" }),
      el("li", { text: "No phone number, address, photo or ID number" })),
    el("div", { class: "sec", text: "Please confirm" }),
    el("div", { class: "field", "data-name": "declarations" },
      el("label", { class: "chk" }, el("input", { type: "checkbox", name: "is_parent_or_guardian" }), el("span", { text: `I am ${kid}'s parent or lawful guardian.` })),
      el("label", { class: "chk" }, el("input", { type: "checkbox", name: "is_adult" }), el("span", { text: "I am 18 or older." })),
      el("span", { class: "err" })),
    el("div", { class: "field", "data-name": "purposes" },
      el("label", { class: "chk" }, el("input", { type: "checkbox", name: "agree_purposes" }),
        el("span", {}, el("strong", { text: "Required: " }), Object.values(info.purposes).join(". ") + ".")),
      el("span", { class: "err" })),
    el("div", { class: "sec", text: "Your choices (you can change these any time)" }), ...perms,
    ...accountFields,
    el("p", { class: "hint", style: "margin:0", text: `Privacy notice version ${info.notice_version}. Your answer is recorded with the date and time.` }),
    el("div", { class: "actions" }, declineBtn, el("button", { class: "btn main grow", type: "submit", text: "Give consent" }))),
    async (v) => {
      await api("POST", "/consent/accept", {
        token, is_parent_or_guardian: !!v.is_parent_or_guardian, is_adult: !!v.is_adult, agree_purposes: !!v.agree_purposes,
        permissions: v.permissions || [], full_name: v.full_name || null, password: v.password || null });
      show(sheetPage([...title("THANK YOU", `${kid}'s account is now active.`), el("a", { class: "btn main", href: "#/home", text: "Go to my parent dashboard" })]));
    });
  show(sheetPage(form, { wide: true }));
}

// ------------------------------------------------------------------ staff invitation + share invitation

async function inviteView(token) {
  let info;
  try { info = await api("POST", "/invites/info", { token }); }
  catch (e) { show(sheetPage([...title("LINK PROBLEM"), el("p", { class: "alert bad", text: e.detail })])); return; }
  const role = info.role === "teacher" ? "a teacher" : "school admin";
  if (info.account_exists) {
    show(sheetPage([...title("ALREADY SET UP", `${info.email} already has an account.`), el("a", { class: "btn main", href: "#/login", text: "Log in" })]));
    return;
  }
  const form = onSubmit(el("form", { novalidate: true, style: "display:flex;flex-direction:column;gap:14px" },
    ...title("WELCOME", `Join ${info.school_name} as ${role}.`),
    field("Email", "email_display", { value: info.email }),
    field("Your full name", "full_name", { autocomplete: "name" }),
    field("Create a password", "password", { type: "password", autocomplete: "new-password", hint: "At least 8 characters." }),
    el("button", { class: "btn main", type: "submit", text: "Create my account" })),
    async (v) => { await api("POST", "/invites/accept", { token, full_name: v.full_name, password: v.password }); go("#/home"); });
  form.querySelector('input[name="email_display"]').readOnly = true;
  show(sheetPage(form));
}

async function shareAcceptView(token) {
  let me = null;
  try { me = await api("GET", "/auth/me"); } catch (e) { /* not logged in */ }
  if (!me) {
    sessionStorage.setItem("elevia_after_login", JSON.stringify({ action: "share", token }));
    show(sheetPage([...title("SHARED PROGRESS", "Someone invited you to see their ELEVIA progress."),
      el("p", { class: "hint center", style: "margin:0", text: "Log in with a parent, teacher or adult account that uses the invited email address. Then open the link again." }),
      el("a", { class: "btn main", href: "#/login", text: "Log in" })]));
    return;
  }
  try {
    const r = await api("POST", "/sharing/accept", { token });
    show(sheetPage([...title("ACCEPTED", `You can now see ${r.owner_name}'s ${r.scopes.join(", ")}.`), el("a", { class: "btn main", href: "#/home", text: "Continue" })]));
  } catch (e) { show(sheetPage([...title("LINK PROBLEM"), el("p", { class: "alert bad", text: e.detail }), el("a", { class: "btn", href: "#/home", text: "Back" })])); }
}

// ------------------------------------------------------------------ signed-in area

function topbar(me) {
  return el("header", { class: "topbar" }, el("a", { class: "brand", href: "#/home", text: "ELEVIA" }),
    el("div", { class: "who" }, el("div", { style: "font-weight:800;color:#1d1d1f", text: me.user.full_name }), el("span", { class: "role", text: me.user.role_label })),
    el("button", { class: "btn small", type: "button", text: "Log out", onClick: logout }));
}

async function logout() {
  try { await api("POST", "/auth/logout"); } catch (e) { /* ignore */ }
  state.me = null; go("#/login");
}

function board(me, ...panels) { show(topbar(me), el("main", { class: "board" }, panels)); }

function panel(heading, ...kids) { return el("section", { class: "panel" }, el("h2", { text: heading }), kids); }

function pill(text, kind) { return el("span", { class: "pill " + kind, text }); }

async function homeView() {
  let me;
  try { me = await api("GET", "/auth/me"); }
  catch (e) { if (e.status === 401) { go("#/login"); return; } show(sheetPage([...title("OOPS"), el("p", { class: "alert bad", text: e.detail })])); return; }
  state.me = me;
  const after = sessionStorage.getItem("elevia_after_login");
  if (after) { sessionStorage.removeItem("elevia_after_login"); const a = JSON.parse(after); if (a.action === "share") return shareAcceptView(a.token); }
  const step = me.next_step;
  if (step === "verify_email") return verifyWaitView(me);
  if (step === "await_parent_consent") return parentWaitView(me);
  if (step === "await_teacher_approval") return teacherWaitView(me);
  if (step === "enrollment_rejected") return board(me, panel("Not added to the class", el("p", { text: "Your teacher didn't approve this class request. Please check with your teacher." })));
  if (step === "suspended") return board(me, panel("Account paused", el("p", { text: "This account is paused. If you're a student, ask your parent or school." })));
  if (step === "parent_home") return parentHome(me);
  if (step === "teacher_home") return teacherHome(me);
  if (step === "admin_home") return adminHome(me);
  if (me.user.role === "learner") return learnerHome(me);
  return studentHome(me);
}

function verifyWaitView(me) {
  const msg = el("p", { class: "hint center", style: "margin:0" });
  show(sheetPage([...title("CHECK YOUR EMAIL", `We sent a confirmation link to ${me.user.email}.`),
    el("p", { class: "hint center", style: "margin:0", text: "Open it to activate your account. The link works for 48 hours." }),
    el("button", { class: "btn", type: "button", text: "Resend the email", onClick: async () => {
      try { await api("POST", "/auth/resend-verification"); msg.textContent = "Sent. Check your inbox."; } catch (e) { msg.textContent = e.detail; }
      const b = demoBanner(); if (b) { root.querySelector(".demo")?.remove(); root.append(b); } } }),
    msg, el("button", { class: "btn small", type: "button", text: "Log out", onClick: logout })]));
}

function parentWaitView(me) {
  const msg = el("p", { class: "hint center", style: "margin:0" });
  const change = onSubmit(el("form", { novalidate: true, hidden: true, style: "display:flex;flex-direction:column;gap:12px" },
    field("Parent's name", "parent_name"), field("Parent's email", "parent_email", { type: "email" }),
    el("button", { class: "btn main", type: "submit", text: "Send to this email" })),
    async (v) => { await api("POST", "/auth/resend-parent-invite", v); homeView(); });
  const cr = me.consent_request;
  show(sheetPage([...title("ALMOST THERE"),
    el("p", { class: "center", style: "margin:0;font-weight:700;font-size:18px", text: cr ? `We've emailed your parent at ${cr.sent_to}` : "We need your parent's OK." }),
    el("p", { class: "hint center", style: "margin:0;font-size:15px", text: "Your account unlocks when they open the link and say yes. The link works for 3 days." }),
    el("button", { class: "btn", type: "button", text: "Resend the email", onClick: async () => {
      try { await api("POST", "/auth/resend-parent-invite", {}); msg.textContent = "Sent again."; homeView(); } catch (e) { msg.textContent = e.detail; } } }),
    el("button", { class: "btn", type: "button", text: "Change parent's email", onClick: () => { change.hidden = false; change.querySelector("input").focus(); } }),
    change, msg, el("button", { class: "btn small", type: "button", text: "Log out", onClick: logout })]));
}

function teacherWaitView(me) {
  const c = me.student.class;
  show(sheetPage([...title("NEARLY IN", `${c.school_name} · Class ${c.grade} ${c.division}`),
    el("p", { class: "hint center", style: "margin:0;font-size:15px", text: "Your teacher needs to approve you for this class. Check back soon." }),
    el("button", { class: "btn", type: "button", text: "Check again", onClick: homeView }),
    el("button", { class: "btn small", type: "button", text: "Log out", onClick: logout })]));
}

function studentHome(me) {
  const c = me.student && me.student.class;
  board(me, panel(`Welcome, ${me.user.full_name.split(" ")[0]}!`,
    el("p", { text: "Your account is ready." }),
    c ? el("p", { text: `You're in ${c.school_name}, Class ${c.grade} ${c.division} (${c.academic_year}).` }) : null,
    el("div", { class: "note", text: "Next step (coming soon): tell ELEVIA your grade, school and subjects, then start your first check-in." })));
}

// ---- independent learner: sharing controls

const SCOPES = { progress: "Progress summary", assessments: "Assessment history", gaps: "Learning gaps", activity: "Recent activity" };

function scopeBoxes(selected, group = "scopes") {
  return el("div", { class: "field", "data-name": "scopes" },
    el("span", { class: "lbl", text: "What they can see" }),
    Object.entries(SCOPES).map(([k, label]) => {
      const i = el("input", { type: "checkbox", name: group + "_" + k, value: k, checked: selected.includes(k) });
      i.dataset.group = "scopes";
      return el("label", { class: "chk" }, i, el("span", { text: label }));
    }), el("span", { class: "err" }));
}

async function learnerHome(me) {
  const data = await api("GET", "/sharing");
  const invite = onSubmit(el("form", { novalidate: true, style: "display:flex;flex-direction:column;gap:12px" },
    field("Their email", "email", { type: "email", placeholder: "parent@example.com or teacher@school.in" }),
    scopeBoxes(["progress"]),
    field("Stop sharing after (days, optional)", "expires_days", { type: "number", min: 1, max: 365, inputmode: "numeric" }),
    el("button", { class: "btn main", type: "submit", text: "Send invitation" })),
    async (v) => {
      await api("POST", "/sharing/invite", { email: v.email, scopes: v.scopes || [], expires_days: v.expires_days ? Number(v.expires_days) : null });
      learnerHome(me);
    });
  const shares = data.shares.filter((s) => ["active", "invited"].includes(s.status));
  board(me,
    panel(`Welcome, ${me.user.full_name.split(" ")[0]}!`, el("p", { text: "Your account is ready. Learning onboarding comes next." }),
      el("p", { class: "hint", text: "Nobody can see your progress unless you share it below." })),
    panel("People who can see your progress",
      shares.length ? el("ul", { class: "list" }, shares.map((s) => shareItem(me, s))) : el("p", { class: "hint", text: "You aren't sharing with anyone." })),
    data.requests.length ? panel("Requests to see your progress", el("ul", { class: "list" }, data.requests.map((r) => requestItem(me, r)))) : null,
    panel("Share with someone", invite),
    panel("Who looked at your shared progress",
      data.access_log.length ? el("ul", { class: "list" }, data.access_log.map((a) => el("li", { class: "item" }, el("span", { class: "grow", text: `${a.viewer} viewed ${a.what}` }), el("span", { class: "hint", text: fmt(a.created_at) }))))
        : el("p", { class: "hint", text: "No views yet." })));
}

function shareItem(me, s) {
  const who = s.grantee_name ? `${s.grantee_name} (${s.grantee_email})` : s.invite_email;
  const form = onSubmit(el("form", { novalidate: true, class: "grow", style: "display:flex;flex-direction:column;gap:8px" },
    el("div", {}, el("strong", { text: who }), pill(s.status === "active" ? "Active" : "Invited", s.status === "active" ? "ok" : "wait"),
      s.expires_at ? el("span", { class: "hint", text: ` · until ${fmt(s.expires_at)}` }) : null),
    scopeBoxes(s.scopes, "g" + s.id),
    el("div", { class: "actions" }, el("button", { class: "btn small", type: "submit", text: "Save changes" }),
      el("button", { class: "btn small danger", type: "button", text: "Stop sharing", onClick: async () => { await api("POST", `/sharing/${s.id}/revoke`); learnerHome(me); } }))),
    async (v) => { await api("PUT", `/sharing/${s.id}/scopes`, { scopes: v.scopes || [] }); learnerHome(me); });
  return el("li", { class: "item" }, form);
}

function requestItem(me, r) {
  const form = onSubmit(el("form", { novalidate: true, class: "grow", style: "display:flex;flex-direction:column;gap:8px" },
    el("strong", { text: `${r.grantee_name} (${r.grantee_role}) wants to see your progress` }),
    scopeBoxes(["progress"], "r" + r.id),
    el("div", { class: "actions" }, el("button", { class: "btn small main", type: "submit", text: "Approve" }),
      el("button", { class: "btn small", type: "button", text: "Reject", onClick: async () => { await api("POST", `/sharing/${r.id}/respond`, { approve: false }); learnerHome(me); } }))),
    async (v) => { await api("POST", `/sharing/${r.id}/respond`, { approve: true, scopes: v.scopes || [] }); learnerHome(me); });
  return el("li", { class: "item" }, form);
}

async function sharedWithMePanel() {
  let rows = [];
  try { rows = await api("GET", "/sharing/with-me"); } catch (e) { /* ignore */ }
  const req = onSubmit(el("form", { novalidate: true, class: "inline-form" },
    field("Ask an adult learner to share (their email)", "learner_email", { type: "email" }),
    el("button", { class: "btn small", type: "submit", text: "Send request" })),
    async (v) => { const r = await api("POST", "/sharing/request", v); req.replaceWith(el("p", { class: "alert good", text: r.message })); });
  return panel("Adult learners sharing with you",
    rows.length ? el("ul", { class: "list" }, rows.map((r) => el("li", { class: "item" }, el("span", { class: "grow", text: r.owner_name }), el("span", { class: "hint", text: r.scopes.join(", ") }))))
      : el("p", { class: "hint", text: "Nobody is sharing with you yet." }), req);
}

// ---- parent

async function parentHome(me) {
  const kids = await api("GET", "/parent/children");
  const perms = { view_progress: "See progress and skills", view_assessments: "See assessment results", view_activity: "See recent learning activity",
    weekly_email: "Weekly progress email", share_with_school_teachers: "Let school teachers see ELEVIA progress" };
  const cards = kids.map((k) => {
    const boxes = Object.entries(perms).map(([key, label]) => {
      const i = el("input", { type: "checkbox", name: "p_" + key, value: key, checked: k.permissions.includes(key) }); i.dataset.group = "permissions";
      return el("label", { class: "chk" }, i, el("span", { text: label }));
    });
    const active = k.link_status === "active";
    const withdraw = el("button", { class: "btn small danger", type: "button", text: "Withdraw consent" });
    let armed = false;
    withdraw.addEventListener("click", async () => {
      if (!armed) { armed = true; withdraw.textContent = "This pauses the account. Tap again to confirm"; return; }
      await api("POST", `/parent/children/${k.student_id}/withdraw-consent`); parentHome(me);
    });
    const form = onSubmit(el("form", { novalidate: true, style: "display:flex;flex-direction:column;gap:8px" }, ...boxes,
      el("div", { class: "actions" }, el("button", { class: "btn small main", type: "submit", text: "Save choices" }), withdraw)),
      async (v) => { await api("PUT", `/parent/children/${k.student_id}/permissions`, { permissions: v.permissions || [] }); parentHome(me); });
    return el("li", { class: "item", style: "flex-direction:column;align-items:stretch" },
      el("div", {}, el("strong", { text: k.full_name }), active ? pill("Consent given", "ok") : pill("Consent withdrawn", "off")),
      active ? form : null,
      el("details", {}, el("summary", { text: "Consent history" }),
        el("ul", {}, k.consent_history.map((h) => el("li", { class: "hint", text: `${fmt(h.created_at)}: ${h.action} (notice ${h.notice_version}, ${h.method})` })))));
  });
  board(me,
    panel("Your children", cards.length ? el("ul", { class: "list" }, cards) : el("p", { class: "hint", text: "No children linked yet. When your child signs up with your email, you'll get a consent request." }),
      el("p", { class: "hint", text: "Detailed progress reports appear here once your child starts learning." })),
    await sharedWithMePanel());
}

// ---- teacher

async function teacherHome(me) {
  const classes = await api("GET", "/school/classes");
  const panels = [];
  for (const c of classes) {
    const roster = await api("GET", `/school/classes/${c.id}/roster`);
    const pending = roster.students.filter((s) => s.status === "pending");
    const approved = roster.students.filter((s) => s.status === "approved");
    panels.push(panel(c.label,
      el("h3", { text: `Waiting for approval (${pending.length})` }),
      pending.length ? el("ul", { class: "list" }, pending.map((s) => el("li", { class: "item" },
        el("span", { class: "grow" }, s.full_name, s.account_status !== "active" ? pill("parent consent pending", "wait") : null),
        el("button", { class: "btn small main", type: "button", text: "Approve", onClick: async () => { await api("POST", `/school/enrollments/${s.enrollment_id}/approve`); teacherHome(me); } }),
        el("button", { class: "btn small", type: "button", text: "Reject", onClick: async () => { await api("POST", `/school/enrollments/${s.enrollment_id}/reject`); teacherHome(me); } }))))
        : el("p", { class: "hint", text: "Nobody waiting." }),
      el("h3", { text: `Students (${approved.length})` }),
      approved.length ? el("ul", { class: "list" }, approved.map((s) => el("li", { class: "item" }, el("span", { class: "grow", text: s.full_name }), pill("approved", "ok"))))
        : el("p", { class: "hint", text: "No students yet. Share a class code to invite them." })));
  }
  let codes = [];
  try { codes = await api("GET", "/school/codes"); } catch (e) { /* ignore */ }
  board(me,
    ...(panels.length ? panels : [panel("Your classes", el("p", { class: "hint", text: "Your school admin hasn't assigned you a class yet." }))]),
    codesPanel(me, classes, codes, () => teacherHome(me)),
    await sharedWithMePanel());
}

function codesPanel(me, classes, codes, refresh) {
  const out = el("div");
  const form = onSubmit(el("form", { novalidate: true, class: "inline-form" },
    el("div", { class: "field", "data-name": "class_id" }, el("label", { text: "Class", for: "codeclass" }),
      el("select", { id: "codeclass", name: "class_id" }, classes.map((c) => el("option", { value: c.id, text: c.label }))), el("span", { class: "err" })),
    field("Valid for (days)", "expires_days", { type: "number", value: 30, min: 1, max: 180 }),
    field("Max students", "max_uses", { type: "number", value: 60, min: 1, max: 500 }),
    el("button", { class: "btn main", type: "submit", text: "Create code" })),
    async (v) => {
      const r = await api("POST", "/school/codes", { class_id: Number(v.class_id), expires_days: Number(v.expires_days), max_uses: Number(v.max_uses) });
      out.replaceChildren(el("p", { class: "hint", text: `Share this code with ${r.class}:` }), el("div", { class: "bigcode", text: r.code }));
      setTimeout(refresh, 4000);
    });
  return panel("Class codes",
    el("p", { class: "hint", text: "Students enter a code to ask to join a class. You approve each one." }),
    classes.length ? form : el("p", { class: "hint", text: "Create a class first." }), out,
    codes.length ? el("ul", { class: "list" }, codes.map((c) => el("li", { class: "item" },
      el("strong", { text: c.code, style: "letter-spacing:.08em" }), el("span", { class: "grow", text: `${c.label} · used ${c.uses}/${c.max_uses} · expires ${fmt(c.expires_at)}` }),
      c.usable ? pill("active", "ok") : pill(c.status === "revoked" ? "revoked" : "expired/full", "off"),
      c.usable ? el("button", { class: "btn small danger", type: "button", text: "Revoke", onClick: async () => { await api("POST", `/school/codes/${c.id}/revoke`); refresh(); } }) : null)))
      : null);
}

// ---- school admin

async function adminHome(me) {
  const [classes, teachersData, codes] = await Promise.all([api("GET", "/school/classes"), api("GET", "/school/teachers"), api("GET", "/school/codes")]);
  const yr = new Date().getMonth() >= 3 ? new Date().getFullYear() : new Date().getFullYear() - 1;
  const newClass = onSubmit(el("form", { novalidate: true, class: "inline-form" },
    el("div", { class: "field", "data-name": "grade" }, el("label", { text: "Grade", for: "grade" }),
      el("select", { id: "grade", name: "grade" }, Array.from({ length: 12 }, (_, i) => el("option", { value: i + 1, text: String(i + 1) }))), el("span", { class: "err" })),
    field("Division", "division", { placeholder: "A", maxlength: 10 }),
    field("Academic year", "academic_year", { value: `${yr}-${String(yr + 1).slice(2)}`, maxlength: 9 }),
    el("button", { class: "btn main", type: "submit", text: "Add class" })),
    async (v) => { await api("POST", "/school/classes", { grade: Number(v.grade), division: v.division, academic_year: v.academic_year }); adminHome(me); });
  const invite = onSubmit(el("form", { novalidate: true, class: "inline-form" },
    field("Teacher's email", "email", { type: "email", placeholder: "teacher@school.in" }),
    el("button", { class: "btn main", type: "submit", text: "Send invitation" })),
    async (v) => { await api("POST", "/school/teachers/invite", v); adminHome(me); });
  const teachers = teachersData.teachers;
  const assign = onSubmit(el("form", { novalidate: true, class: "inline-form" },
    el("div", { class: "field", "data-name": "teacher_id" }, el("label", { text: "Teacher", for: "asgt" }),
      el("select", { id: "asgt", name: "teacher_id" }, teachers.map((t) => el("option", { value: t.id, text: t.full_name }))), el("span", { class: "err" })),
    el("div", { class: "field", "data-name": "class_id" }, el("label", { text: "Class", for: "asgc" }),
      el("select", { id: "asgc", name: "class_id" }, classes.map((c) => el("option", { value: c.id, text: c.label }))), el("span", { class: "err" })),
    check("Can create class codes", "can_create_codes", false),
    el("button", { class: "btn main", type: "submit", text: "Assign" })),
    async (v) => { await api("POST", "/school/assignments", { teacher_id: Number(v.teacher_id), class_id: Number(v.class_id), can_create_codes: !!v.can_create_codes }); adminHome(me); });
  board(me,
    panel("Classes", classes.length ? el("ul", { class: "list" }, classes.map((c) => el("li", { class: "item" },
      el("span", { class: "grow", text: c.label }), el("span", { class: "hint", text: `${c.approved} students · ${c.pending} waiting` })))) : el("p", { class: "hint", text: "No classes yet." }), newClass),
    panel("Teachers",
      teachers.length ? el("ul", { class: "list" }, teachers.map((t) => el("li", { class: "item" },
        el("span", { class: "grow" }, el("strong", { text: t.full_name }), ` · ${t.email}`), el("span", { class: "hint", text: t.classes.length ? t.classes.join("; ") : "No class assigned" }),
        t.can_create_codes ? pill("can create codes", "ok") : null))) : el("p", { class: "hint", text: "No teachers yet." }),
      teachersData.pending_invites.length ? el("p", { class: "hint", text: "Invitation sent to: " + teachersData.pending_invites.join(", ") }) : null,
      invite, teachers.length && classes.length ? assign : null),
    codesPanel(me, classes, codes, () => adminHome(me)),
    panel("Privacy", el("p", { class: "hint", text: "As school admin you manage classes, teachers and codes. You can see the class list, but not students' learning records unless you're also assigned as their teacher." })));
}

// ------------------------------------------------------------------ router

function route() {
  const h = location.hash || "#/";
  if (h === "#/" || h === "#") return accessView();
  if (h === "#/login") return loginView();
  if (h === "#/forgot") return forgotView();
  if (h === "#/student") return studentSignupView(null);
  if (h === "#/school") return schoolCodeView();
  if (h === "#/learner") return learnerSignupView();
  if (h === "#/home") return homeView().catch((e) => show(sheetPage([...title("OOPS"), el("p", { class: "alert bad", text: e.detail || "Something went wrong." })])));
  return accessView();
}

function start() {
  // Links from emails: /?action=<what>&token=<secret>. Read once, then remove from the address bar.
  const q = new URLSearchParams(location.search);
  const action = q.get("action"), token = q.get("token");
  if (action) {
    history.replaceState(null, "", "/" + (action === "sharing" ? "#/home" : "#/"));
    if (action === "consent" && token) return consentView(token);
    if (action === "verify" && token) return verifyView(token);
    if (action === "reset" && token) return resetView(token);
    if (action === "invite" && token) return inviteView(token);
    if (action === "share" && token) return shareAcceptView(token);
    if (action === "sharing") return homeView();
  }
  route();
}

window.addEventListener("hashchange", route);
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
