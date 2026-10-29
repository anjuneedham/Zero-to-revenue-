// Growth (Phase 9): funnel from recorded data and the experiment lifecycle. Records only: nothing here runs an experiment.
(function () {
  const { el, add, pill, btn, card, nice, fmt } = Z;
  const post = (path, body) => Z.api(path, "POST", body || {});
  let slug = Z.store.get("z2r_growth_biz") || "buildflow", G = null;
  const STATUS_KIND = { proposed: "", running: "royal", succeeded: "ok", failed: "bad", inconclusive: "warn", abandoned: "" };
  const num = v => (v == null ? "not tracked" : fmt.num(v, 2));

  function funnel(root) {
    const f = G.funnel, c = card("Funnel from recorded data", "Built only from records you entered. A stage with no data says not tracked, never 0.");
    if (!f.stages) { c.append(Z.none("No growth funnel", f.reason)); root.append(c); return; }
    f.stages.forEach(s => c.append(Z.add(el("div", "item"), el("p", null, s.label), Z.add(el("div", "meta"), pill(num(s.value), s.value == null ? "warn" : "ok")), s.note ? el("p", "sub", s.note) : null)));
    f.rates.forEach(r => c.append(Z.add(el("div", "item"), el("p", null, r.label), Z.add(el("div", "meta"), pill(r.rate_pct == null ? "n/a" : r.rate_pct + "%", r.rate_pct == null ? "warn" : ""), r.small_sample ? pill("small sample (" + r.sample + "): noise", "bad") : null), r.note ? el("p", "sub", r.note) : null)));
    f.caveats.forEach(t => c.append(el("p", "sub", t)));
    root.append(c);
  }

  const act = (label, fn) => btn(label, "gold small", async () => { try { await fn(); await Z.rerender(); } catch (x) { Z.toast(x.message, "bad"); } });

  function experiment(root, e) {
    const c = card(e.hypothesis, [e.success_metric && "Metric: " + e.success_metric, e.kpi_name && "KPI: " + e.kpi_name].filter(Boolean).join(" · "));
    c.append(Z.add(el("div", "meta"), pill(nice(e.status), STATUS_KIND[e.status]), e.duration_days ? pill(e.duration_days + " days") : null, e.baseline_value != null ? pill("baseline " + fmt.num(e.baseline_value, 2)) : null,
      e.target_value != null ? pill("target " + fmt.num(e.target_value, 2)) : null, e.ends_on ? pill("ends " + e.ends_on, e.ready_to_conclude ? "warn" : "") : null, e.decision ? pill("decision: " + e.decision, "royal") : null));
    if (e.ready_to_conclude) c.append(el("p", "flags", "The planned duration is over: record the result."));
    if (e.evaluation) { c.append(el("p", null, e.evaluation.verdict)); e.evaluation.warnings.forEach(w => c.append(el("p", "sub", w))); }
    if (e.result) c.append(el("p", "sub", "Result: " + e.result));
    if (e.learnings) c.append(el("p", "sub", "Learned: " + e.learnings));
    if (e.abandon_reason) c.append(el("p", "sub", "Abandoned: " + e.abandon_reason));
    if (e.learning_knowledge_id) c.append(el("p", "sub", "Written to this business's knowledge as an ASSUMED note. Verify it with a source in the Lab before treating it as fact."));
    const row = el("div", "row");
    if (e.status === "proposed") row.append(act("Start", () => post("/api/growth/experiments/" + e.id + "/start")),
      btn("Edit plan", "ghost small", () => Z.formDialog("Edit plan", [["hypothesis", "Hypothesis", "text", null, true], ["success_metric", "Success metric", "text"], ["duration_days", "Duration (days)", "int"], ["min_sample", "Minimum sample", "int"], ["baseline_value", "Baseline", "num"], ["target_value", "Target", "num"]], b => post("/api/founder/experiments/" + e.id, b), e)));
    if (e.status === "running") row.append(btn("Record result", "gold small", () => Z.formDialog("Conclude: the result is fixed once saved", [
      ["outcome", "Outcome", "select", [["succeeded", "Succeeded"], ["failed", "Failed"], ["inconclusive", "Inconclusive"]], true], ["result_value", "Result (number)", "num"], ["result", "Result (what happened)", "text"],
      ["sample_size", "Sample size (people/visits/orders)", "int"], ["learnings", "What did you learn?", "text", null, true], ["decision", "Decision", "select", [["iterate", "Iterate"], ["stop", "Stop"], ["scale", "Scale (needs Succeeded)"]], true], ["decision_note", "Decision note", "text"]],
      b => post("/api/growth/experiments/" + e.id + "/conclude", b))));
    if (e.status === "proposed" || e.status === "running") row.append(btn("Abandon", "ghost small", () => Z.formDialog("Abandon experiment", [["reason", "Why?", "text", null, true]], b => post("/api/growth/experiments/" + e.id + "/abandon", b))));
    if (row.children.length) c.append(row);
    root.append(c);
  }

  Z.pages.growth = {
    title: "Growth", sub: "Experiments and funnels from your recorded data", icon: "plan",
    async render(root) {
      G = await Z.api("/api/growth/" + slug);
      const wrap = el("div", "list"), top = card("Experiments", "Each is a record: hypothesis, metric, duration, result and decision. You run them; this only keeps score honestly.");
      const sel = el("select"); sel.setAttribute("aria-label", "Business");
      [["buildflow", "BuildFlow"], ["agriloop", "Agriloop"], ["fashion", "Fashion"], ["trading", "Trading"]].forEach(([v, l]) => { const o = el("option", null, l); o.value = v; o.selected = v === slug; sel.append(o); });
      sel.onchange = () => { slug = sel.value; Z.store.set("z2r_growth_biz", slug); Z.rerender(); };
      add(top, sel, Z.add(el("div", "meta"), ...Object.entries(G.counts).filter(([, n]) => n).map(([k, n]) => pill(k + ": " + n, STATUS_KIND[k]))),
        Z.add(el("div", "row"), btn("Add experiment", "gold small", () => Z.formDialog("Add experiment", [["hypothesis", "Hypothesis", "text", null, true], ["success_metric", "Success metric", "text"], ["duration_days", "Duration (days)", "int"], ["min_sample", "Minimum sample (optional)", "int"], ["baseline_value", "Baseline (optional)", "num"], ["target_value", "Target (optional)", "num"]], b => post("/api/founder/businesses/" + slug + "/experiments", b)))));
      wrap.append(top);
      funnel(wrap);
      if (!G.experiments.length) wrap.append(Z.none("No experiments yet", "Write the hypothesis, metric and duration before you run anything."));
      G.experiments.forEach(e => experiment(wrap, e));
      root.append(wrap);
    },
  };
})();
