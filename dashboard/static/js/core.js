// Shared helpers. All DOM is built with createElement/textContent: server data (much of it scraped
// from the internet) is never parsed as HTML.
(function () {
  const Z = (window.Z = { pages: {}, state: { status: null, mode: "LOCAL" } });
  Z.$ = id => document.getElementById(id);
  Z.text = (e, t) => { e.textContent = t == null ? "" : String(t); };
  Z.el = (tag, cls, t) => { const e = document.createElement(tag); if (cls) e.className = cls; if (t != null) e.textContent = t; return e; };
  Z.add = (parent, ...kids) => { kids.flat().forEach(k => k && parent.append(k)); return parent; };

  const NS = "http://www.w3.org/2000/svg";
  const ICONS = {
    home: "M3 11l9-8 9 8v9a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1z",
    scout: "M11 4a7 7 0 100 14 7 7 0 000-14zm9 16l-4.2-4.2",
    operator: "M4 6h16M4 12h16M4 18h10",
    treasury: "M3 7h18v12H3zM3 7l3-3h12l3 3M16 13h2",
    plan: "M5 3h14v18l-7-4-7 4z",
    target: "M12 3a9 9 0 100 18 9 9 0 000-18zm0 5a4 4 0 100 8 4 4 0 000-8z",
    play: "M8 5v14l11-7z",
    check: "M5 12l5 5L20 7",
    copy: "M9 9h11v11H9zM5 15V4h11",
    link: "M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1",
    stop: "M6 6h12v12H6z",
  };
  Z.icon = name => {
    const s = document.createElementNS(NS, "svg");
    s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("fill", "none"); s.setAttribute("stroke", "currentColor");
    s.setAttribute("stroke-width", "2"); s.setAttribute("stroke-linecap", "round"); s.setAttribute("stroke-linejoin", "round");
    s.setAttribute("aria-hidden", "true");
    const p = document.createElementNS(NS, "path"); p.setAttribute("d", ICONS[name] || ""); s.append(p); return s;
  };

  // ---- storage (per device convenience only) ----
  const TOKEN = "z2r_token";
  Z.store = {
    get(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    del(k) { try { localStorage.removeItem(k); } catch (e) {} },
  };
  Z.token = () => Z.store.get(TOKEN);
  Z.setToken = t => Z.store.set(TOKEN, t);

  // ---- API ----
  Z.api = async (path, method, body, authed = true) => {
    const headers = { "Content-Type": "application/json" };
    if (authed) headers.Authorization = "Bearer " + Z.token();
    const r = await fetch(path, { method: method || "GET", headers, body: body ? JSON.stringify(body) : undefined });
    let data = {};
    try { data = await r.json(); } catch (e) {}
    if (authed && r.status === 401) { Z.onSignedOut && Z.onSignedOut("Session ended. Sign in again."); throw new Error("Signed out"); }
    if (!r.ok) throw new Error(data.error || "Request failed (" + r.status + ")");
    return data;
  };

  // ---- feedback ----
  Z.toast = (msg, kind) => {
    const t = Z.el("div", "toast " + (kind || ""), msg); Z.$("toasts").append(t);
    setTimeout(() => t.remove(), 4200);
  };
  Z.busy = (btn, fn) => async () => {
    const label = btn.textContent; btn.disabled = true; btn.replaceChildren(Z.el("span", "spin"), document.createTextNode(" " + label));
    try { await fn(); } catch (e) { if (e.message !== "Signed out") Z.toast(e.message, "bad"); } finally { btn.disabled = false; btn.textContent = label; }
  };
  Z.skeleton = (n = 3) => Z.add(Z.el("div", "list"), Array.from({ length: n }, () => Z.el("div", "skel")));
  Z.empty = (title, hint) => Z.add(Z.el("div", "empty"), Z.el("b", null, title), hint ? Z.el("span", null, hint) : null);

  // ---- bits ----
  Z.pill = (t, kind) => Z.el("span", "pill " + (kind || ""), t);
  Z.btn = (label, cls, onClick, icon) => {
    const b = Z.el("button", "btn " + (cls || "")); b.type = "button";
    if (icon) b.append(Z.icon(icon)); b.append(document.createTextNode(label)); if (onClick) b.onclick = Z.busy(b, onClick); return b;
  };
  Z.card = (title, sub, ...actions) => {
    const c = Z.el("section", "card"); const h = Z.el("header");
    const left = Z.el("div"); left.append(Z.el("h2", null, title)); if (sub) left.append(Z.el("p", "sub", sub));
    h.append(left); if (actions.length) h.append(Z.add(Z.el("div", "row"), actions)); c.append(h); return c;
  };
  Z.statusKind = s => ({ QUALIFIED: "ok", APPROVED: "gold", IN_PROGRESS: "royal", AWAITING_PAYMENT: "gold", PAYMENT_VERIFIED: "ok", COMPLETED: "ok",
    REVIEW_REQUIRED: "warn", WAITING_FOR_USER: "warn", QUEUED: "", FAILED: "bad", REJECTED: "bad", CANCELLED: "bad", OPEN: "warn" }[s] || "");
  Z.nice = s => String(s || "").replace(/_/g, " ").toLowerCase().replace(/^./, c => c.toUpperCase());

  Z.fmt = {
    usd: v => "$" + Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    when: t => (t ? new Date(t).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "never"),
    ago: t => {
      if (!t) return "never"; const s = Math.max(0, (Date.now() - new Date(t)) / 1000);
      if (s < 60) return "just now"; if (s < 3600) return Math.floor(s / 60) + " min ago";
      if (s < 86400) return Math.floor(s / 3600) + " h ago"; return Math.floor(s / 86400) + " d ago";
    },
    addr: a => (a ? a.slice(0, 6) + "…" + a.slice(-4) : ""),
    num: (v, d = 4) => (v == null ? "n/a" : Number(v).toLocaleString(undefined, { maximumFractionDigits: d })),
  };
  Z.copy = async (t, what) => {
    try { await navigator.clipboard.writeText(t); Z.toast((what || "Copied") + " copied", "ok"); } catch (e) { Z.toast("Copy failed; select the text instead", "bad"); }
  };

  // Sparkline: points [{v}], one scale for x and y, end point marked.
  Z.spark = pts => {
    const w = 220, h = 46, svg = document.createElementNS(NS, "svg"); svg.setAttribute("viewBox", `0 0 ${w} ${h}`); svg.setAttribute("class", "spark");
    svg.setAttribute("role", "img"); svg.setAttribute("aria-label", "Balance history");
    if (!pts || pts.length < 2) { return Z.el("div", "sub", pts && pts.length ? "One reading so far" : "No readings yet"); }
    const vs = pts.map(p => p.v), lo = Math.min(...vs), hi = Math.max(...vs), span = hi - lo || 1;
    const X = i => 4 + (i * (w - 8)) / (pts.length - 1), Y = v => h - 6 - ((v - lo) / span) * (h - 14);
    const d = pts.map((p, i) => (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(p.v).toFixed(1)).join(" ");
    const area = document.createElementNS(NS, "path"); area.setAttribute("class", "area"); area.setAttribute("d", d + ` L${X(pts.length - 1)} ${h} L${X(0)} ${h} Z`);
    const line = document.createElementNS(NS, "path"); line.setAttribute("class", "line"); line.setAttribute("d", d);
    const c = document.createElementNS(NS, "circle"); c.setAttribute("cx", X(pts.length - 1)); c.setAttribute("cy", Y(vs[vs.length - 1])); c.setAttribute("r", 3.5);
    svg.append(area, line, c); return svg;
  };

  Z.openDrawer = (title, node) => {
    Z.text(Z.$("drawer-title"), title); const b = Z.$("drawer-body"); b.replaceChildren(node); Z.$("drawer").showModal();
  };

  Z.decisionCard = (a, refresh) => {
    const isOutreach = a.kind === "send_outreach";
    const it = Z.el("div", "item");
    it.append(Z.el("div", "t", a.title));
    it.append(Z.add(Z.el("div", "meta"), Z.pill(Z.nice(a.status), a.status === "APPROVED" ? "gold" : "warn"),
      Z.pill("risk " + (a.risk || "?"), a.risk === "HIGH" ? "bad" : "ok"), a.deadline ? Z.pill("due " + a.deadline.slice(0, 10)) : null,
      isOutreach ? Z.pill("outreach") : null));
    it.append(Z.el("p", "sub", a.why_required));
    if (a.verified_url) { const l = Z.el("a", null, "Open the source page"); l.href = a.verified_url; l.target = "_blank"; l.rel = "noopener noreferrer"; it.append(l); }
    const row = Z.el("div", "row");
    const done = async (path, body, msg) => { await Z.api("/api/actions/" + a.action_id + "/" + path, "POST", body); Z.toast(msg, "ok"); await refresh(); };
    if (isOutreach) {
      const ta = Z.el("textarea", "draft"); ta.rows = 10; ta.placeholder = "Loading draft…"; ta.disabled = true;
      Z.api("/api/actions/" + a.action_id + "/draft").then(d => { ta.value = d.draft || ""; ta.disabled = false; });
      it.append(ta);
      if (a.status === "OPEN") {
        row.append(Z.btn("Approve", "small", () => done("approve", {}, "Approved. Edit above if you like, then send from here or confirm you sent it elsewhere.")),
          Z.btn("Reject", "ghost small", () => done("reject", {}, "Rejected")));
      } else if (a.status === "APPROVED") {
        row.append(
          Z.btn("Send via Gmail", "gold small", async () => {
            try { const r = await Z.api("/api/actions/" + a.action_id + "/send", "POST", { edited_body: ta.value }); Z.goal("Email sent (id " + r.message_id.slice(0, 8) + "…)"); await refresh(); }
            catch (e) { Z.toast(e.message, "bad"); }
          }),
          Z.btn("I sent it another way", "ghost small", () => done("sent", {}, "Marked sent.")),
          Z.btn("Reject", "ghost small", () => done("reject", {}, "Rejected")));
      }
      it.append(row); return it;
    }
    row.append(Z.btn("View draft", "ghost small", async () => {
      const d = await Z.api("/api/actions/" + a.action_id + "/draft"); const pre = Z.el("pre", "draft", d.draft || "No draft."); Z.openDrawer("Draft submission", pre);
    }));
    if (a.status === "OPEN") {
      row.append(Z.btn("Approve", "small", () => done("approve", {}, "Approved. Submit it yourself, then confirm.")),
        Z.btn("Reject", "ghost small", () => done("reject", {}, "Rejected")));
    } else if (a.status === "APPROVED") {
      const inp = Z.el("input"); inp.placeholder = "Link to your submission (optional, https)"; inp.id = "proof-" + a.action_id; inp.setAttribute("aria-label", "Proof link");
      const mail = Z.el("input"); mail.placeholder = "Or: contact's email, to submit via Gmail"; mail.type = "email"; mail.setAttribute("aria-label", "Recipient email");
      it.append(inp, mail);
      row.append(
        Z.btn("I submitted it", "gold small", () => done("submitted", { proof_url: inp.value.trim() }, "Marked submitted. Waiting for payment.")),
        Z.btn("Submit via email", "gold small", async () => {
          if (!mail.value.trim()) { Z.toast("Enter the contact's email first", "bad"); return; }
          try { const r = await Z.api("/api/actions/" + a.action_id + "/submit-email", "POST", { to_email: mail.value.trim() }); Z.goal("Submitted by email (id " + r.message_id.slice(0, 8) + "…)"); await refresh(); }
          catch (e) { Z.toast(e.message, "bad"); }
        }),
        Z.btn("Reject", "ghost small", () => done("reject", {}, "Rejected")));
    }
    it.append(row); return it;
  };
})();
