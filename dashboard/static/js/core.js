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
    treasury: "M3 7h18v12H3zM3 7l3-3h12l3 3M16 13h2",
    plan: "M5 3h14v18l-7-4-7 4z",
    target: "M12 3a9 9 0 100 18 9 9 0 000-18zm0 5a4 4 0 100 8 4 4 0 000-8z",
    founder: "M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.5 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z",
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
  // One roll-up of every tracked step in the OS: build phases, master-plan steps, and every checklist.
  Z.progress = (plan, ticks) => {
    const pc = (items, ok) => { const done = items.filter(ok).length; return { done, total: items.length, pct: items.length ? Math.round(100 * done / items.length) : 0 }; };
    const t = i => !!ticks[i.id];
    const week = plan.week.days.flatMap(d => d.items);
    const areas = [
      ["Build phases", pc(plan.phases.map(p => ({ id: p[0], st: p[3] })), i => i.st === "done")],
      ["Master plan", pc(plan.master, t)],
      ["BuildFlow launch", pc(plan.buildflow, t)],
      ["Your setup", pc(plan.system, t)],
      ["This week", pc(week, t)],
    ];
    const done = areas.reduce((a, [, x]) => a + x.done, 0), total = areas.reduce((a, [, x]) => a + x.total, 0);
    return { areas, done, total, pct: total ? Math.round(100 * done / total) : 0 };
  };
  Z.progressCard = (plan, ticks) => {
    const pr = Z.progress(plan, ticks), c = Z.card("OS progress: " + pr.pct + "%", pr.done + " of " + pr.total + " tracked steps done");
    const bar = Z.el("div", "bar gold"), f = Z.el("i"); f.style.width = pr.pct + "%"; bar.append(f); c.append(bar);
    pr.areas.forEach(([name, x]) => {
      const r = Z.el("div"), h = Z.el("div", "row"); h.style.justifyContent = "space-between";
      Z.add(h, Z.el("span", null, name), Z.el("b", null, x.done + "/" + x.total));
      const b = Z.el("div", "bar"), i = Z.el("i"); i.style.width = x.pct + "%"; b.append(i); Z.add(r, h, b); c.append(r);
    });
    return c;
  };
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

})();
