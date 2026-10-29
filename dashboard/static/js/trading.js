// Trading workspace (Phase 6): RESEARCH AND PAPER TRADING RECORDS ONLY. There is no live mode and nothing here places orders.
(function () {
  const { el, add, pill, btn, card, fmt, nice } = Z;
  const SLUG = "trading", TABS = [["overview", "Overview"], ["strategies", "Strategies"], ["notes", "Notes"]];
  const post = (path, body) => Z.api("/api/founder/" + path, "POST", body || {});
  const bad = s => s && s.error;
  let W = null, tab = Z.store.get("z2r_tr_tab") || "overview";
  const MODES = [["backtest", "Backtest (in-sample)"], ["out_of_sample", "Out-of-sample"], ["walk_forward", "Walk-forward"], ["paper", "Paper trading"]];
  const STATUS = [["idea", "Idea"], ["researching", "Researching"], ["backtesting", "Backtesting"], ["validating", "Validating"], ["paper", "Paper trading"], ["rejected", "Rejected"], ["retired", "Retired"]];
  const STRATEGY = () => [["name", "Strategy", "text", null, true], ["hypothesis", "Hypothesis (why should this work?)", "text"], ["instrument", "Instrument / market", "text"], ["status", "Stage", "select", STATUS],
    ["data_notes", "Data source and data-quality notes", "text"], ["risk_notes", "Risk notes (position size, exposure)", "text"], ["failure_conditions", "Explicit failure conditions (when do you stop?)", "text"],
    ["max_drawdown_limit_pct", "Max drawdown limit % (a breach flags the strategy)", "num"], ["min_trades", "Minimum trades for a result to count (default 30)", "int"]];
  const RUN = () => [["mode", "Mode", "select", MODES, true], ["period_start", "Period start", "date"], ["period_end", "Period end", "date"], ["trades", "Number of trades", "int"], ["net_return_pct", "Net return %", "num"],
    ["max_drawdown_pct", "Max drawdown %", "num"], ["costs_included", "Fees/costs included in this result", "checkbox"], ["cost_bps", "Cost assumed (bps)", "num"], ["slippage_bps", "Slippage assumed (bps)", "num"],
    ["data_source", "Data source", "text"], ["params", "Parameters used", "text"], ["notes", "Notes", "text"]];

  function banner(root) {
    const c = el("section", "card"); c.setAttribute("role", "note");
    add(c, el("h2", null, "Research only"), el("p", null, "Backtests, out-of-sample tests and paper trading records. There is no live trading in this system and nothing here places orders. A backtest does not predict future results; nothing on this page implies profitability."));
    root.append(c);
  }

  function overview(root) {
    banner(root); Z.ws.overview(root, W, SLUG);
  }

  function strategies(root) {
    banner(root);
    const L = W.research_lab; if (bad(L)) { root.append(Z.ws.secErr("Strategies")); return; }
    const c = card("Strategies", "Each is judged on the evidence you recorded, shown as what is still missing, never as a score.");
    c.append(Z.add(el("div", "row"), btn("Add strategy", "gold small", async () => Z.formDialog("Add strategy", STRATEGY(), b => post("businesses/trading/trading-strategies", b)))));
    if (!L.strategies.length) c.append(Z.empty("No strategies yet", "Write the hypothesis and your failure conditions BEFORE running any test."));
    root.append(c);
    L.strategies.forEach(st => {
      const e = st.evaluation, sc = card(st.name, [st.instrument, st.hypothesis].filter(Boolean).join(" · "));
      sc.append(Z.add(el("div", "meta"), pill(nice(st.status), st.status === "rejected" ? "bad" : "royal"), ...Object.entries(e.counts).map(([k, v]) => pill(k.replace("_", "-") + ": " + v))));
      if (e.breaches.length) { const b = el("div", "item"); e.breaches.forEach(x => b.append(el("p", "err", x))); sc.append(b); }
      sc.append(el("p", e.breaches.length ? "err" : "sub", e.verdict));
      const ul = el("ul", "plain"); e.checklist.forEach(x => ul.append(el("li", null, (x.done ? "✔ " : "✘ ") + x.item))); sc.append(el("div", "label", "Research checklist"), ul);
      sc.append(Z.add(el("div", "row"), btn("Record a result", "gold small", async () => Z.formDialog("Record a result (cannot be edited later)", RUN(), b => post("businesses/trading/trading-runs", { ...b, strategy_id: st.id }), { mode: "backtest" })),
        btn("Edit strategy", "ghost small", async () => Z.formDialog("Edit strategy", STRATEGY(), b => post("trading-strategies/" + st.id, b), st))));
      sc.append(el("p", "sub", "Results are append-only: to correct one, record a new result and explain in its notes."));
      st.runs.forEach(r => { const it = el("div", "item"); add(it, Z.add(el("div", "meta"), pill(r.mode_label, r.mode === "paper" ? "ok" : r.mode === "backtest" ? "warn" : "royal"), r.period_start ? pill(r.period_start + " → " + (r.period_end || "?")) : null),
        el("p", null, `${r.trades != null ? r.trades + " trades" : "trades n/a"} · return ${r.net_return_pct != null ? fmt.num(r.net_return_pct, 2) + "%" : "n/a"} · max drawdown ${r.max_drawdown_pct != null ? fmt.num(r.max_drawdown_pct, 2) + "%" : "n/a"}`),
        ...r.warnings.map(w => el("p", "flags", w))); sc.append(it); });
      root.append(sc);
    });
  }

  Z.pages.trading = {
    title: "Trading", sub: "Priority 4 · research and paper trading only", icon: "plan",
    async render(root) {
      W = await Z.api("/api/founder/workspace/" + SLUG);
      const wrap = el("div", "list"), tabs = el("div", "tabs"); tabs.setAttribute("role", "tablist");
      TABS.forEach(([k, label]) => { const b = el("button", null, label); b.type = "button"; b.setAttribute("role", "tab"); b.setAttribute("aria-selected", String(k === tab)); b.onclick = () => { tab = k; Z.store.set("z2r_tr_tab", k); Z.rerender(); }; tabs.append(b); });
      wrap.append(tabs);
      if (tab === "notes") { banner(wrap); Z.ws.notes(wrap, W, SLUG); } else ({ overview, strategies }[tab] || overview)(wrap);
      root.append(wrap);
    },
  };
})();
