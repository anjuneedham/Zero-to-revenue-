// All DOM updates use textContent only: server data is never parsed as HTML.
const $ = id => document.getElementById(id);
const text = (el, t) => { el.textContent = t; };
const KEY = "z2r_token";
const store = {
  get() { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } },
  set(v) { try { localStorage.setItem(KEY, v); } catch (e) {} },
  clear() { try { localStorage.removeItem(KEY); } catch (e) {} },
};
let timer = null;

function show(view) {
  for (const v of ["setup1", "setup2", "setup3", "login", "app"]) $(v).hidden = v !== view;
}
function row(parent, t) { const d = document.createElement("div"); d.textContent = t; parent.appendChild(d); }

async function call(path, method, body, authed) {
  const headers = { "Content-Type": "application/json" };
  if (authed) headers.Authorization = "Bearer " + store.get();
  const r = await fetch(path, { method: method || "GET", headers, body: body ? JSON.stringify(body) : undefined });
  let data = {};
  try { data = await r.json(); } catch (e) {}
  if (authed && r.status === 401) { signedOut("Session ended. Sign in again."); throw new Error("401"); }
  if (!r.ok) throw new Error(data.error || "Request failed (" + r.status + ")");
  return data;
}
function signedOut(m) {
  store.clear(); if (timer) clearInterval(timer);
  text($("msg"), m || ""); show("login");
}
async function refresh() {
  const s = await call("/api/status", "GET", null, true);
  text($("rev"), "$" + Number(s.verified_revenue_usd).toFixed(2));
  text($("state"), s.paused ? "PAUSED - all agents stopped" : "Running (" + s.mode + ")");
  $("agents").replaceChildren();
  s.agents.forEach(a => row($("agents"), a.name.toUpperCase() + " - " + a.status + " [" + a.mode + "] last run: " + (a.last_run_at || "never")));
  $("actions").replaceChildren();
  if (!s.open_user_actions.length) text($("actions"), "None");
  s.open_user_actions.forEach(a => row($("actions"), a.title + " - " + a.exact_action + (a.deadline ? " (by " + a.deadline + ")" : "")));
  loadOpps().catch(() => {});
  text($("counts"), "Tasks: " + JSON.stringify(s.tasks) + " | Opportunities: " + JSON.stringify(s.opportunities) + " | Payments pending: " + s.payments_pending);
}
async function loadOpps() {
  const d = await call("/api/opportunities", "GET", null, true);
  $("opps").replaceChildren();
  if (!d.opportunities.length) { text($("opps"), "None yet. Run Scout."); return; }
  d.opportunities.forEach(o => {
    const el = document.createElement("div"); el.className = "card";
    row(el, "[" + o.status + "] " + o.title);
    row(el, "score " + o.opportunity_score + " | risk " + o.risk_score + " | confidence " + o.confidence +
      " | claimed pay: " + (o.expected_payment == null ? "n/a" : "$" + o.expected_payment) + " (unverified)");
    if (o.scam_indicators) row(el, "flags: " + o.scam_indicators);
    row(el, o.recommended_action || "");
    $("opps").appendChild(el);
  });
}
const guard = fn => async () => { text($("msg"), ""); try { await fn(); } catch (e) { text($("msg"), e.message); } };

$("s_begin").onclick = guard(async () => {
  const d = await call("/api/auth/setup/begin", "POST", { setup_token: $("s_token").value, password: $("s_pw").value });
  text($("s_secret"), d.secret); $("s_pw").value = ""; show("setup2");
});
$("s_confirm").onclick = guard(async () => {
  const d = await call("/api/auth/setup/confirm", "POST", { setup_token: $("s_token").value, code: $("s_code").value.trim() });
  $("s_codes").replaceChildren(); d.recovery_codes.forEach(c => row($("s_codes"), c));
  $("s_token").value = ""; show("setup3");
});
$("s_done").onclick = () => { $("s_codes").replaceChildren(); text($("s_secret"), ""); show("login"); };
$("l_go").onclick = guard(async () => {
  const d = await call("/api/auth/login", "POST", { password: $("l_pw").value, code: $("l_code").value.trim() });
  $("l_pw").value = ""; $("l_code").value = ""; store.set(d.token);
  show("app"); await refresh(); timer = setInterval(() => refresh().catch(() => {}), 30000);
});
$("scout").onclick = guard(async () => {
  text($("scoutmsg"), "Running...");
  const r = await call("/api/scout/run", "POST", null, true);
  text($("scoutmsg"), r.ran ? ("seen " + r.seen + ", new " + r.new + ", qualified " + r.qualified + (r.errors.length ? " | errors: " + r.errors.join("; ") : "")) : ("Not run: " + r.reason));
  await loadOpps(); await refresh();
});
$("pause").onclick = guard(async () => { await call("/api/pause", "POST", null, true); await refresh(); });
$("resume").onclick = guard(async () => { await call("/api/resume", "POST", null, true); await refresh(); });
$("signout").onclick = guard(async () => { await call("/api/auth/logout", "POST", null, true); signedOut(""); });
$("signoutall").onclick = guard(async () => { await call("/api/auth/logout-all", "POST", null, true); signedOut(""); });

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
(async () => {
  try {
    const st = await call("/api/auth/state");
    if (!st.setup_complete) {
      if (!st.setup_enabled) { text($("msg"), "Setup is not enabled yet. Set OWNER_SETUP_TOKEN (20+ random characters) in Vercel, then redeploy."); return; }
      show("setup1"); return;
    }
    if (store.get()) { try { show("app"); await refresh(); timer = setInterval(() => refresh().catch(() => {}), 30000); return; } catch (e) {} }
    show("login");
  } catch (e) { text($("msg"), "Service unavailable: " + e.message); }
})();
