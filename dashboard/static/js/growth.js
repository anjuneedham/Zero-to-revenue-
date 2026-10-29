// Growth (Phase 9): experiments with a real lifecycle (start, conclude, abandon), funnels computed from recorded rows, KPI trends.
// All DOM via createElement/textContent. Nothing here runs an experiment or calls a model: a founder starts and concludes.
(function () {
  const { el, add, pill, btn, card, nice } = Z;
  const post = (path, body) => Z.api(path, "POST", body || {});
  const STATUS_KIND = { running: "royal", succeeded: "ok", failed: "bad", abandoned: "", proposed: "warn" };
  let slug = Z.store.get("z2r_growth_biz") || "buildflow";
  const day = t => (t ? new Date(t).toLocaleDateString([], { month: "short", day: "numeric" }) : "");
  const val = v => (v === null || v === undefined ? "not recorded" : String(Number(v)));

  function act(label, kind, fn) { return btn(label, kind, async () => { try { await fn(); await Z.rerender(); } catch (x) { Z.toast(x.message, "bad"); } }); }

  function experiment(e) {
    const it = el("div", "item");
    add(it, el("div", "t", e.hypothesis), Z.add(el("div", "meta"), pill(nice(e.status), STATUS_KIND[e.status]),
      e.duration_days ? pill(e.duration_days + " days") : pill("no duration", "warn"), e.success_metric ? pill("metric: " + e.success_metric) : null,
      e.started_at ? pill("started " + day(e.started_at)) : null, e.status === "running" && e.ends_at ? pill((e.overdue ? "review overdue since " : "review by ") + day(e.ends_at), e.overdue ? "bad" : "") : null,
      e.decision ? pill("decision: " + e.decision, "ok") : null));
    if (e.baseline_value !== null || e.target_value !== null || e.result_value !== null) it.append(el("p", "sub", "Baseline " + val(e.baseline_value) + " · target " + val(e.target_value) + (e.status !== "proposed" && e.status !== "running" ? " · result " + val(e.result_value) + (e.result_source === "kpi" ? " (from the KPI's current value)" : "") : "")));
    if (e.result) it.append(el("p", null, e.result));
    if (e.learnings) it.append(el("p", "sub", "Learning (recorded as assumed unless you attached a source): " + e.learnings));
    const row = el("div", "row");
    if (e.status === "proposed") row.append(act("Start", "gold small", () => post("/api/growth/experiments/" + e.id + "/start")),
      btn("Set metric and duration", "ghost small", () => Z.formDialog("Set up experiment", [["success_metric", "Success metric", "text"], ["duration_days", "Duration (days)", "int", null, true], ["target_value", "Target (optional)", "num"]], b => post("/api/founder/experiments/" + e.id, b), { success_metric: e.success_metric || "", duration_days: e.duration_days || "" })));
    if (e.status === "running") row.append(btn("Conclude", "gold small", () => conclude(e)));
    if (e.status === "proposed" || e.status === "running") row.append(btn("Abandon", "ghost small", () => Z.formDialog("Abandon experiment", [["reason", "Why", "text", null, true]], b => post("/api/growth/experiments/" + e.id + "/abandon", b))));
    if (row.children.length) it.append(row);
    return it;
  }

  function conclude(e) {
    Z.formDialog("Conclude experiment", [
      ["outcome", "Did it work?", "select", [["succeeded", "Succeeded"], ["failed", "Failed"]], true], ["result", "What happened (the facts)", "text", null, true],
      ["result_value", "Result value for the metric (blank = use the KPI's current value if one is linked)", "num"],
      ["learnings", "What you learned", "text", null, true], ["decision", "Decision", "select", [["adopt", "Adopt it"], ["iterate", "Iterate / test again"], ["stop", "Stop"]], true],
      ["decision_rationale", "Why", "text"]],
      async b => { const r = await post("/api/growth/experiments/" + e.id + "/conclude", b); Z.toast("Saved as a decision and a " + r.evidence_label + " knowledge note", "ok"); });
  }

  function funnel(f) {
    const c = card(f.name, f.note);
    f.steps.forEach(s => c.append(Z.add(el("div", "item"), Z.add(el("div", "meta"), pill(s.label), pill(String(s.count), s.count ? "ok" : ""), s.rate_from_previous !== null && s.rate_from_previous !== undefined ? pill(Math.round(s.rate_from_previous * 100) + "% of previous step") : null))));
    if (f.dropped) c.append(el("p", "sub", f.dropped + " dropped/churned/cancelled, not counted in later steps."));
    if (f.totals) c.append(el("p", "sub", Object.entries(f.totals).map(([k, v]) => nice(k) + ": " + val(v)).join(" · ")));
    if (f.coverage) c.append(el("p", "sub", "Of " + f.coverage.posted + " posted: " + f.coverage.posts_with_views + " have views entered, " + f.coverage.posts_with_signups + " have signups entered."));
    return c;
  }

  Z.pages.growth = {
    title: "Growth", sub: "Experiments and funnels from your real data", icon: "plan",
    async render(root) {
      const G = await Z.api("/api/growth/" + slug), wrap = el("div", "list");
      const sel = el("select"); sel.setAttribute("aria-label", "Business");
      [["buildflow", "BuildFlow"], ["agriloop", "Agriloop"], ["fashion", "Fashion"], ["trading", "Trading"]].forEach(([v, l]) => { const o = el("option", null, l); o.value = v; o.selected = v === slug; sel.append(o); });
      sel.onchange = () => { slug = sel.value; Z.store.set("z2r_growth_biz", slug); Z.rerender(); };
      const top = card("Experiments", "Write the hypothesis, metric and duration, then start it. Concluding records a decision and a knowledge note; the learning stays 'assumed' unless you attach a source. Nothing runs automatically.");
      top.append(Z.add(el("div", "row"), sel, btn("New experiment", "gold small", () => Z.formDialog("New experiment", [["hypothesis", "Hypothesis", "text", null, true], ["success_metric", "Success metric", "text"], ["duration_days", "Duration (days)", "int"],
        ["baseline_value", "Baseline (optional)", "num"], ["target_value", "Target (optional)", "num"], ["metric_kpi_id", "Linked KPI (optional)", "select", [["", "None"], ...G.kpis.map(k => [k.id, k.name])]]], b => post("/api/founder/businesses/" + slug + "/experiments", b)))));
      if (G.overdue.length) top.append(el("p", "err", G.overdue.length + " running experiment(s) are past their duration: conclude or abandon them."));
      top.append(Z.add(el("div", "meta"), ...Object.entries(G.by_status).map(([k, n]) => pill(nice(k) + ": " + n, STATUS_KIND[k]))));
      wrap.append(top);
      if (!G.experiments.length) wrap.append(Z.none("No experiments yet", "Add one with a clear hypothesis and a number you can check."));
      G.experiments.forEach(e => wrap.append(experiment(e)));
      const fc = card("Funnels", "Computed from rows you have recorded. Unentered numbers are not counted as zero.");
      wrap.append(fc);
      if (!G.funnels.length) fc.append(el("p", "sub", "No funnel data for this business yet."));
      G.funnels.forEach(f => wrap.append(funnel(f)));
      const kc = card("KPI trends", "Last 12 recorded readings per KPI.");
      if (!G.kpis.length) kc.append(el("p", "sub", "No KPIs yet."));
      G.kpis.forEach(k => kc.append(Z.add(el("div", "item"), el("div", "t", k.name + (k.unit ? " (" + k.unit + ")" : "")), Z.add(el("div", "meta"), pill("current " + val(k.current_value)), pill("target " + val(k.target_value)),
        pill(k.readings.length + " readings"), k.change !== null ? pill("change " + Number(k.change), "") : pill("need 2+ readings")))));
      wrap.append(kc);
      root.append(wrap);
    },
  };
})();
