// Matchday control room. All DOM updates use textContent / createElement only:
// server data (much of it scraped from the internet) is never parsed as HTML.
const $ = id => document.getElementById(id);
const text = (el, t) => { el.textContent = t; };
const KEY = "z2r_token";
const store = {
  get() { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } },
  set(v) { try { localStorage.setItem(KEY, v); } catch (e) {} },
  clear() { try { localStorage.removeItem(KEY); } catch (e) {} },
};
const CHAINS = { 1: "Ethereum", 56: "BNB Chain", 204: "opBNB", 324: "ZKsync Era", 8453: "Base", 42161: "Arbitrum One", 59144: "Linea" };
let timer = null;

// ---------- kick-off loading screen ----------
const KO = ["Walking out of the tunnel", "Checking the pitch", "Reading the team sheet", "Warming up the agents"];
let koI = 0;
const koTimer = setInterval(() => { koI = (koI + 1) % KO.length; text($("ko-msg"), KO[koI]); }, 700);
const started = Date.now();
function kickoffDone() {
  const wait = Math.max(0, 900 - (Date.now() - started)); // let the walk-out play briefly
  setTimeout(() => { clearInterval(koTimer); $("kickoff").classList.add("out"); setTimeout(() => { $("kickoff").hidden = true; }, 500); }, wait);
}

// ---------- helpers ----------
function el(tag, cls, t) { const e = document.createElement(tag); if (cls) e.className = cls; if (t != null) e.textContent = t; return e; }
function pill(t, cls) { return el("span", "pill " + (cls || ""), t); }
function show(view) {
  for (const v of ["setup1", "setup2", "setup3", "login", "app"]) $(v).hidden = v !== view;
  $("topbtns").hidden = view !== "app";
}
async function call(path, method, body, authed) {
  const headers = { "Content-Type": "application/json" };
  if (authed) headers.Authorization = "Bearer " + store.get();
  const r = await fetch(path, { method: method || "GET", headers, body: body ? JSON.stringify(body) : undefined });
  let data = {};
  try { data = await r.json(); } catch (e) {}
  if (authed && r.status === 401) { signedOut("Session ended. Sign in again."); throw new Error("Signed out"); }
  if (!r.ok) throw new Error(data.error || "Request failed (" + r.status + ")");
  return data;
}
function signedOut(m) { store.clear(); if (timer) clearInterval(timer); text($("msg"), m || ""); show("login"); }
const busy = (btn, fn) => async () => {
  text($("msg"), "");
  const label = btn.textContent; btn.disabled = true; btn.replaceChildren(el("span", "spin"), document.createTextNode(label));
  try { await fn(); } catch (e) { text($("msg"), e.message); } finally { btn.disabled = false; text(btn, label); }
};
const fmtTime = t => t ? new Date(t).toLocaleString() : "never";

// ---------- renderers ----------
const POSITIONS = {
  scout: ["11", "Winger · finds chances", s => "Opportunities today: " + s.health.scout_opportunities_today],
  operator: ["8", "Midfield · builds the play", s => "Waiting for you: " + s.health.operator_waiting_for_you + " · failed: " + s.health.operator_failed],
  treasury: ["1", "Keeper · guards the money", s => "Last wallet check: " + fmtTime(s.health.treasury_last_check)],
};
function renderStatus(s) {
  text($("rev"), "$" + Number(s.verified_revenue_usd).toFixed(2));
  text($("state"), s.paused ? "Paused · red card shown" : "In play (" + s.mode + ")");
  $("statedot").className = "dot" + (s.paused ? " paused" : "");
  text($("unvalued"), s.verified_receipts_without_usd_value ? s.verified_receipts_without_usd_value + " verified receipt(s) without a USD price" : "Payments pending: " + s.payments_pending);
  const team = $("team"); team.replaceChildren();
  s.agents.forEach(a => {
    const [num, pos, stat] = POSITIONS[a.name] || ["?", "", () => ""];
    const p = el("div", "player");
    p.append(el("div", "shirt", num));
    const h = el("h3", null, a.name); const dot = el("span", "dot " + (a.status === "online" ? "" : a.status === "error" ? "err" : "off"));
    dot.style.display = "inline-block"; dot.style.marginLeft = "8px"; h.append(dot);
    p.append(h, el("div", "pos", pos + " · " + a.status), el("div", "stat", stat(s) + " · last run " + fmtTime(a.last_run_at)));
    team.append(p);
  });
  const box = $("actions"); box.replaceChildren();
  if (!s.open_user_actions.length) box.append(el("div", "empty", "No decisions needed right now."));
  s.open_user_actions.forEach(a => {
    const it = el("div", "item");
    it.append(el("div", "t", a.title));
    const m = el("div", "meta"); m.append(pill(a.status, a.status === "APPROVED" ? "g" : "r"), pill("risk " + (a.risk || "?"), a.risk === "HIGH" ? "x" : "q"));
    if (a.deadline) m.append(pill("due " + a.deadline.slice(0, 10)));
    it.append(m, el("div", "sub", a.why_required));
    if (a.verified_url) { const l = el("a", null, "Open source page ↗"); l.href = a.verified_url; l.target = "_blank"; l.rel = "noopener noreferrer"; it.append(l); }
    const row = el("div", "row");
    const view = el("button", "ghost", "View draft");
    view.onclick = busy(view, async () => { const d = await call("/api/actions/" + a.action_id + "/draft", "GET", null, true); text($("drafttext"), d.draft || "No draft."); $("draftdlg").showModal(); });
    row.append(view);
    if (a.status === "OPEN") {
      const ok = el("button", null, "Approve"); ok.onclick = busy(ok, async () => { await call("/api/actions/" + a.action_id + "/approve", "POST", {}, true); await refresh(); });
      const no = el("button", "ghost", "Reject"); no.onclick = busy(no, async () => { await call("/api/actions/" + a.action_id + "/reject", "POST", {}, true); await refresh(); });
      row.append(ok, no);
    } else if (a.status === "APPROVED") {
      const inp = el("input"); inp.placeholder = "Link to your submission (optional, https)"; inp.id = "proof-" + a.action_id;
      const done = el("button", "gold", "I submitted it");
      done.onclick = busy(done, async () => { await call("/api/actions/" + a.action_id + "/submitted", "POST", { proof_url: inp.value.trim() }, true); await refresh(); });
      const no = el("button", "ghost", "Reject"); no.onclick = busy(no, async () => { await call("/api/actions/" + a.action_id + "/reject", "POST", {}, true); await refresh(); });
      it.append(inp); row.append(done, no);
    }
    it.append(row); box.append(it);
  });
}
async function loadOpps() {
  const d = await call("/api/opportunities", "GET", null, true);
  const box = $("opps"); box.replaceChildren();
  if (!d.opportunities.length) { box.append(el("div", "empty", "No opportunities yet. Run Scout.")); return; }
  d.opportunities.forEach(o => {
    const it = el("div", "item");
    it.append(el("div", "t", o.title));
    const m = el("div", "meta");
    m.append(pill(o.status, o.status === "QUALIFIED" ? "q" : o.status === "REVIEW_REQUIRED" ? "r" : "g"),
      pill("score " + o.opportunity_score), pill("risk " + o.risk_score, o.risk_score > 35 ? "x" : ""),
      pill(o.expected_payment == null ? "pay n/a" : "$" + o.expected_payment + " claimed"));
    it.append(m);
    if (o.scam_indicators) it.append(el("div", "flags", "Flags: " + o.scam_indicators));
    it.append(el("div", "sub", o.recommended_action || ""));
    box.append(it);
  });
}
async function loadPayments() {
  const d = await call("/api/payments", "GET", null, true);
  const box = $("payments"); box.replaceChildren();
  if (!d.payments.length) { box.append(el("div", "empty", "No payments expected yet. They appear after you mark work as submitted.")); return; }
  d.payments.forEach(p => {
    const it = el("div", "item");
    it.append(el("div", "t", p.title || p.id));
    const m = el("div", "meta");
    m.append(pill(p.status, p.status === "PAYMENT_VERIFIED" ? "q" : "r"), pill((p.expected_amount == null ? "?" : p.expected_amount) + " " + (p.asset || "") + " expected"));
    if (p.tx_hash) m.append(pill(CHAINS[p.chain_id] || p.chain_id), pill(p.tx_hash.slice(0, 10) + "…"));
    it.append(m);
    if (p.status !== "PAYMENT_VERIFIED") {
      const f = el("div", "form");
      const l1 = el("label", "f", "Chain"); const sel = el("select"); sel.id = "chain-" + p.id;
      Object.entries(CHAINS).forEach(([id, n]) => { const o = el("option", null, n); o.value = id; sel.append(o); }); sel.value = "56"; l1.append(sel);
      const l2 = el("label", "f", "Transaction hash"); const tx = el("input"); tx.id = "tx-" + p.id; tx.placeholder = "0x…"; l2.append(tx);
      const b = el("button", "gold", "Verify on-chain");
      b.onclick = busy(b, async () => { const r = await call("/api/payments/" + p.id + "/verify", "POST", { chain_id: sel.value, tx_hash: tx.value.trim() }, true); text($("msg"), ""); await refresh(); celebrate(r); });
      f.append(l1, l2, b); it.append(f);
    }
    box.append(it);
  });
}
function celebrate(r) {
  const s = $("ko-msg"); text(s, "Goal! " + r.amount + " " + r.asset + " verified");
  $("kickoff").hidden = false; $("kickoff").classList.remove("out");
  setTimeout(() => { $("kickoff").classList.add("out"); setTimeout(() => { $("kickoff").hidden = true; }, 500); }, 1600);
}
async function loadFeed() {
  const d = await call("/api/notifications", "GET", null, true);
  const box = $("feed"); box.replaceChildren();
  if (!d.notifications.length) { box.append(el("div", "empty", "No messages yet.")); return; }
  d.notifications.forEach(n => {
    const it = el("div", "item");
    it.append(pill(n.priority, n.priority === "CRITICAL" ? "x" : n.priority === "HIGH" ? "r" : ""));
    const body = el("div"); body.append(el("div", "t", n.title), el("div", "sub", n.body), el("div", "sub", n.channel + " · " + n.status + " · " + fmtTime(n.created_at)));
    body.querySelectorAll(".sub").forEach(x => { x.style.whiteSpace = "pre-wrap"; });
    it.append(body); box.append(it);
  });
}
async function refresh() {
  const s = await call("/api/status", "GET", null, true);
  renderStatus(s);
  await Promise.all([loadOpps(), loadPayments(), loadFeed()]).catch(e => text($("msg"), e.message));
}
function startApp() { show("app"); return refresh().then(() => { timer = setInterval(() => refresh().catch(() => {}), 30000); }); }

// ---------- buttons ----------
$("s_begin").onclick = busy($("s_begin"), async () => {
  const d = await call("/api/auth/setup/begin", "POST", { setup_token: $("s_token").value, password: $("s_pw").value });
  text($("s_secret"), d.secret); $("s_pw").value = ""; show("setup2");
});
$("s_confirm").onclick = busy($("s_confirm"), async () => {
  const d = await call("/api/auth/setup/confirm", "POST", { setup_token: $("s_token").value, code: $("s_code").value.trim() });
  $("s_codes").replaceChildren(); d.recovery_codes.forEach(c => $("s_codes").append(el("code", "key", c)));
  $("s_token").value = ""; show("setup3");
});
$("s_done").onclick = () => { $("s_codes").replaceChildren(); text($("s_secret"), ""); show("login"); };
$("l_go").onclick = busy($("l_go"), async () => {
  const d = await call("/api/auth/login", "POST", { password: $("l_pw").value, code: $("l_code").value.trim() });
  $("l_pw").value = ""; $("l_code").value = ""; store.set(d.token); await startApp();
});
$("pause").onclick = busy($("pause"), async () => { await call("/api/pause", "POST", null, true); await refresh(); });
$("resume").onclick = busy($("resume"), async () => { await call("/api/resume", "POST", null, true); await refresh(); });
$("scout").onclick = busy($("scout"), async () => {
  const r = await call("/api/scout/run", "POST", null, true);
  text($("scoutmsg"), r.ran ? ("Seen " + r.seen + ", new " + r.new + ", qualified " + r.qualified + (r.errors.length ? " · problems: " + r.errors.join("; ") : "")) : ("Not run: " + r.reason));
  await refresh();
});
$("operator").onclick = busy($("operator"), async () => {
  const r = await call("/api/operator/run", "POST", null, true);
  const done = r.steps.filter(x => x.task).length;
  text($("scoutmsg"), r.steps[0] && !r.steps[0].ran ? "Not run: " + r.steps[0].reason : (done ? done + " draft(s) prepared. See Manager's decisions." : "Nothing queued for the Operator."));
  await refresh();
});
$("treasury").onclick = busy($("treasury"), async () => {
  const r = await call("/api/treasury/run", "POST", null, true);
  const box = $("balances"); box.replaceChildren();
  if (!r.ran) { box.append(el("div", "empty", "Not run: " + r.reason)); return; }
  Object.entries(r.balances).forEach(([c, b]) => { const it = el("div", "item"); it.append(el("div", "t", c), el("div", "sub", b + " (native coin)")); box.append(it); });
  if (r.errors.length) box.append(el("div", "flags", "Could not read: " + r.errors.join(", ")));
});
$("closedlg").onclick = () => $("draftdlg").close();
$("signout").onclick = busy($("signout"), async () => { await call("/api/auth/logout", "POST", null, true); signedOut(""); });
$("signoutall").onclick = busy($("signoutall"), async () => { await call("/api/auth/logout-all", "POST", null, true); signedOut(""); });

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
(async () => {
  try {
    const st = await call("/api/auth/state");
    if (!st.setup_complete) {
      if (!st.setup_enabled) { text($("msg"), "Setup is not enabled yet. Set OWNER_SETUP_TOKEN (20+ characters) in Vercel, then redeploy."); return; }
      show("setup1"); return;
    }
    if (store.get()) { try { await startApp(); return; } catch (e) {} }
    show("login");
  } catch (e) { text($("msg"), "Service unavailable: " + e.message); }
  finally { kickoffDone(); }
})();
