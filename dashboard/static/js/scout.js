(function () {
  const { el, add, text, pill, btn, card, fmt, nice } = Z;
  let filter = "ALL", query = "";
  const FILTERS = [["ALL", "All"], ["QUALIFIED", "Qualified"], ["REVIEW_REQUIRED", "Needs review"], ["IN_PROGRESS", "Drafted"], ["OTHER", "Other"]];

  function detail(o) {
    const w = el("div", "list");
    add(w, add(el("div", "meta"), pill(nice(o.status), Z.statusKind(o.status)), pill("score " + o.opportunity_score), pill("risk " + o.risk_score, o.risk_score > 35 ? "bad" : "ok"), pill("confidence " + o.confidence)));
    const rows = [["Organization", o.organization || "unknown"], ["Claimed payment (unverified)", o.expected_payment == null ? "not stated" : "$" + fmt.num(o.expected_payment, 2)],
      ["Required capital", o.required_capital == null ? "unknown (not assumed zero)" : "$" + fmt.num(o.required_capital, 2)], ["Deadline", o.deadline ? o.deadline.slice(0, 10) : "not stated"]];
    const t = el("div", "tablewrap"), tb = el("table"); rows.forEach(([k, v]) => { const r = el("tr"); add(r, el("th", null, k), el("td", null, v)); tb.append(r); }); t.append(tb); w.append(t);
    if (o.scam_indicators) w.append(add(el("div", "item"), el("div", "label", "Flags"), el("div", "flags", o.scam_indicators)));
    if (o.missing_information) w.append(add(el("div", "item"), el("div", "label", "Missing information"), el("div", "sub", o.missing_information)));
    w.append(add(el("div", "item"), el("div", "label", "Recommended action"), el("div", null, o.recommended_action || "")));
    if (o.source_url && /^https:/.test(o.source_url)) { const a = el("a", null, "Open the source page"); a.href = o.source_url; a.target = "_blank"; a.rel = "noopener noreferrer"; w.append(a); }
    return w;
  }

  Z.pages.scout = {
    title: "Scout", sub: "Finds and scores opportunities. Read-only research.", icon: "scout",
    async render(root) {
      const [ov, od] = await Promise.all([Z.api("/api/scout/overview"), Z.api("/api/opportunities")]);
      const g = el("div", "grid");

      const top = el("section", "card hero s8");
      const head = el("div", "agent"); add(head, el("div", "shirt", "11"), el("h3", null, "Scout"), el("div", "label", "Winger · finds the chances"),
        el("div", "sub", ov.runs.length ? "Last run " + fmt.ago(ov.runs[0].started_at) + " · " + (ov.runs[0].outcome || "running") : "Has not run yet"));
      const result = el("p", "sub", "Searches Superteam Earn and GitHub, scores every result, and queues only well-documented ones for the Operator.");
      const run = btn("Run Scout now", "gold", async () => {
        const r = await Z.api("/api/scout/run", "POST");
        Z.toast(r.ran ? `Scout: ${r.new} new, ${r.qualified} qualified` + (r.errors.length ? ", with problems" : "") : "Not run: " + r.reason, r.errors && r.errors.length ? "bad" : "ok");
        await Z.rerender();
      }, "scout");
      add(top, head, result, run);
      if (ov.skills.length) top.append(add(el("div", "chips"), ov.skills.map(s => pill(s, "gold"))));
      else top.append(el("p", "sub", "Skills are not set, so skill fit is neutral."));
      g.append(top);

      const ai = card("Claude helper", "Optional extra opinion on each new opportunity. It can add caution, never remove it."); ai.classList.add("s4");
      const pct = ov.ai.monthly_cap_usd ? Math.min(100, 100 * ov.ai.spent_usd / ov.ai.monthly_cap_usd) : 0;
      add(ai, add(el("div", "meta"), pill(ov.ai.enabled ? "On" : "Off", ov.ai.enabled ? "ok" : "warn")),
        el("div", "stat", fmt.usd(ov.ai.spent_usd)), el("p", "sub", "spent this month of " + fmt.usd(ov.ai.monthly_cap_usd) + " hard cap"));
      const b = el("div", "bar gold"); const f = el("i"); f.style.width = pct + "%"; b.append(f); ai.append(b);
      if (ov.ai.missing.length) ai.append(el("p", "sub", "Still needed in Vercel: " + ov.ai.missing.join(", ")));
      g.append(ai);

      const src = card("Sources", "Where Scout looks. Quality varies a lot."); src.classList.add("s12");
      const sc = el("div", "cols");
      ov.sources.forEach(s => { const it = el("div", "item"); add(it, el("div", "t", s.label), el("div", "sub", s.note), add(el("div", "meta"), pill(s.found + " found"), pill("last " + fmt.ago(s.last_seen)))); sc.append(it); });
      src.append(sc); g.append(src);

      const list = card("Opportunities", "Click one for the full picture. Claimed pay is never revenue."); list.classList.add("s12");
      const chips = el("div", "chips"); const search = el("input"); search.placeholder = "Search titles and organizations"; search.id = "opp-search"; search.setAttribute("aria-label", "Search"); search.value = query;
      const body = el("div", "list");
      const known = ["QUALIFIED", "REVIEW_REQUIRED", "IN_PROGRESS"];
      const draw = () => {
        chips.replaceChildren(...FILTERS.map(([k, l]) => {
          const n = od.opportunities.filter(o => k === "ALL" || (k === "OTHER" ? !known.includes(o.status) : o.status === k)).length;
          const b = el("button", null, l + " (" + n + ")"); b.type = "button"; b.setAttribute("aria-pressed", filter === k); b.onclick = () => { filter = k; draw(); }; return b;
        }));
        const q = query.toLowerCase();
        const rows = od.opportunities.filter(o => (filter === "ALL" || (filter === "OTHER" ? !known.includes(o.status) : o.status === filter)) && (!q || (o.title + " " + (o.organization || "")).toLowerCase().includes(q)));
        body.replaceChildren();
        if (!rows.length) body.append(Z.empty(od.opportunities.length ? "Nothing matches" : "No opportunities yet", od.opportunities.length ? "Try another filter." : "Run Scout to look for some."));
        rows.slice(0, 60).forEach(o => {
          const it = el("div", "item click"); it.tabIndex = 0; it.setAttribute("role", "button");
          add(it, el("div", "t", o.title), add(el("div", "meta"), pill(nice(o.status), Z.statusKind(o.status)), pill("score " + o.opportunity_score), pill("risk " + o.risk_score, o.risk_score > 35 ? "bad" : ""),
            pill(o.expected_payment == null ? "pay n/a" : "$" + fmt.num(o.expected_payment, 0) + " claimed"), o.organization ? pill(o.organization) : null));
          if (o.scam_indicators) it.append(el("div", "flags", "Flags: " + o.scam_indicators));
          const open = () => Z.openDrawer(o.title.slice(0, 80), detail(o)); it.onclick = open; it.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } };
          body.append(it);
        });
      };
      search.oninput = () => { query = search.value; draw(); };
      add(list, search, chips, body); draw(); g.append(list);

      const runs = card("Run history", "Every pass Scout has made"); runs.classList.add("s12");
      if (!ov.runs.length) runs.append(Z.empty("No runs yet"));
      else {
        const t = el("div", "tablewrap"), tb = el("table"); const hr = el("tr"); ["When", "Outcome", "Problems"].forEach(h => hr.append(el("th", null, h))); tb.append(hr);
        ov.runs.forEach(r => { const tr = el("tr"); add(tr, el("td", null, fmt.when(r.started_at)), (() => { const td = el("td"); td.append(pill(r.outcome || "running", r.outcome === "ok" ? "ok" : r.outcome ? "warn" : "")); return td; })(), el("td", null, r.error || "none")); tb.append(tr); });
        t.append(tb); runs.append(t);
      }
      g.append(runs); root.append(g);
    },
  };
})();
