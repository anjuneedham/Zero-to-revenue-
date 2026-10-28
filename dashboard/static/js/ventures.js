(function () {
  const { el, add, pill, btn, card } = Z;
  const DAYS = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const STAGE_KIND = { KILLED: "bad", SCALE: "ok", SELL: "gold", VALIDATE: "royal" };
  const TASK_NEXT = { OPEN: "DOING", DOING: "DONE", BLOCKED: "DOING", DONE: "OPEN" };
  let open = "";

  const input = (ph, type) => { const i = el("input"); i.placeholder = ph; if (type) i.type = type; i.setAttribute("aria-label", ph); return i; };
  const metricText = m => m.name.replace(/_/g, " ") + ": " + (Number.isInteger(m.value) ? m.value : m.value.toFixed(2));

  function taskRow(t, redo) {
    const row = el("div", "item"); const done = t.status === "DONE" || t.status === "DROPPED";
    const title = el("div", "t", t.title); if (done) title.style.textDecoration = "line-through";
    const meta = add(el("div", "row"), pill(t.status, t.status === "BLOCKED" ? "bad" : t.status === "DONE" ? "ok" : ""), pill(t.owner), t.due_at ? pill("due " + t.due_at) : null);
    add(row, title, meta); if (t.note) row.append(el("small", null, t.note));
    const acts = el("div", "row");
    acts.append(btn(t.status === "DONE" ? "Reopen" : t.status === "DOING" ? "Mark done" : "Start", "small", async () => { await Z.api("/api/tasks/" + t.id, "POST", { status: TASK_NEXT[t.status] || "DOING" }); redo(); }));
    if (!done && t.status !== "BLOCKED") acts.append(btn("Blocked", "small ghost", async () => {
      const why = prompt("What is it blocked on?"); if (!why) return; await Z.api("/api/tasks/" + t.id, "POST", { status: "BLOCKED", note: why }); redo(); }));
    row.append(acts); return row;
  }

  async function detail(vid, box) {
    const d = await Z.api("/api/ventures/" + vid); const redo = () => draw(box);
    const c = card(d.venture.name, "Stage " + d.venture.stage + " · kill criterion: " + (d.venture.kill_criterion || "none set"));
    const tasks = el("div", "list"); d.tasks.forEach(t => tasks.append(taskRow(t, redo))); if (!d.tasks.length) tasks.append(Z.empty("No tasks yet", "Add the first one below."));
    const t1 = input("New task"); const t2 = input("Due (YYYY-MM-DD, optional)");
    const addT = btn("Add task", "gold", async () => { await Z.api("/api/ventures/" + vid + "/tasks", "POST", { title: t1.value, due_at: t2.value }); redo(); });
    c.append(tasks, add(el("div", "row"), t1, t2, addT));

    const ex = card("Experiments", "Every test has a metric and a threshold; closing one records what was learned.");
    d.experiments.forEach(e => {
      const r = el("div", "item"); add(r, el("div", "t", e.hypothesis), add(el("div", "row"), pill(e.status), e.metric ? pill(e.metric) : null, e.success_threshold ? pill("goal " + e.success_threshold) : null));
      if (e.result) r.append(el("small", null, e.result));
      if (e.status === "PLANNED") r.append(btn("Start", "small", async () => { await Z.api("/api/experiments/" + e.id, "POST", { status: "RUNNING" }); redo(); }));
      if (e.status === "RUNNING") r.append(add(el("div", "row"), ...["SUCCEEDED", "FAILED", "ABANDONED"].map(s => btn(Z.nice(s), "small ghost", async () => {
        const res = prompt("What did you learn?"); if (!res) return; await Z.api("/api/experiments/" + e.id, "POST", { status: s, result: res }); redo(); }))));
      ex.append(r);
    });
    const e1 = input("Hypothesis"), e2 = input("Metric"), e3 = input("Success threshold");
    ex.append(add(el("div", "row"), e1, e2, e3, btn("Add experiment", "gold", async () => { await Z.api("/api/ventures/" + vid + "/experiments", "POST", { hypothesis: e1.value, metric: e2.value, success_threshold: e3.value }); redo(); })));

    const mt = card("Metrics and effort", "Owner-entered. These are never counted as revenue.");
    const latest = {}; d.metrics.forEach(m => { if (!latest[m.name]) latest[m.name] = m; });
    const chips = el("div", "row"); Object.values(latest).forEach(m => chips.append(pill(metricText(m)))); if (!chips.childNodes.length) chips.append(el("small", null, "No metrics yet."));
    const m1 = input("metric_name"), m2 = input("Value", "number");
    const h1 = input("Hours today", "number"), h2 = input("Claude sessions today", "number");
    mt.append(chips, add(el("div", "row"), m1, m2, btn("Record metric", "gold", async () => { await Z.api("/api/ventures/" + vid + "/metrics", "POST", { name: m1.value, value: Number(m2.value) }); redo(); })),
      add(el("div", "row"), h1, h2, btn("Log effort", "gold", async () => { await Z.api("/api/ventures/" + vid + "/effort", "POST", { hours: Number(h1.value || 0), claude_sessions: Number(h2.value || 0) }); redo(); })));

    const dc = card("Decisions");
    d.decisions.forEach(x => { const r = el("div", "item"); add(r, el("div", "t", x.question), add(el("div", "row"), pill(x.status, x.status === "OPEN" ? "warn" : "ok")));
      if (x.decision) r.append(el("small", null, x.decision + (x.rationale ? " - " + x.rationale : "")));
      if (x.status === "OPEN") r.append(btn("Decide", "small", async () => { const ans = prompt(x.question); if (!ans) return; await Z.api("/api/decisions/" + x.id, "POST", { decision: ans }); redo(); }));
      dc.append(r); });
    const q = input("Question to decide"); dc.append(add(el("div", "row"), q, btn("Log question", "gold", async () => { await Z.api("/api/decisions", "POST", { venture_id: vid, question: q.value }); redo(); })));
    return [c, ex, mt, dc];
  }

  async function draw(box) {
    const d = await Z.api("/api/ventures"); box.replaceChildren();
    const plan = card("This week", "Planned focus per day (today highlighted). Effort and Claude usage are self-reported.");
    const wk = el("div", "chips");
    for (let day = 1; day <= 7; day++) { const a = d.allocation.filter(x => x.weekday === day).map(x => x.name + " (" + x.focus + ")").join(", ") || "OS review";
      const p = pill(DAYS[day] + ": " + a, day === d.today_weekday ? "gold" : ""); wk.append(p); }
    plan.append(wk); box.append(plan);
    if (d.open_decisions.length) { const c = card("Decisions waiting on you", d.open_decisions.length + " open"); d.open_decisions.forEach(x => c.append(el("div", "item", x.question))); box.append(c); }
    const grid = el("div", "list");
    d.ventures.forEach(v => {
      const it = el("div", "item click"); const done = v.tasks.DONE || 0, all = Object.values(v.tasks).reduce((a, b) => a + b, 0);
      add(it, el("div", "t", "P" + v.priority + " · " + v.name), add(el("div", "row"), pill(v.stage, STAGE_KIND[v.stage]), pill(done + "/" + all + " tasks"),
        v.open_decisions ? pill(v.open_decisions + " decision(s)", "warn") : null, v.running_experiments ? pill(v.running_experiments + " experiment(s)", "royal") : null));
      if (v.metrics.length) it.append(el("small", null, v.metrics.map(metricText).join(" · ")));
      it.onclick = () => { open = open === v.id ? "" : v.id; draw(box); }; grid.append(it);
      if (open === v.id) { const slot = el("div", "list"); grid.append(slot); detail(v.id, box).then(cs => { slot.replaceChildren(...cs); }).catch(e => Z.toast(e.message, "bad")); }
    });
    box.append(grid); box.append(el("small", null, d.note));
  }

  Z.pages.ventures = { title: "Ventures", sub: "One OS, four ventures, one at a time", icon: "plan", render: async box => { const root = el("div", "list"); box.append(root); await draw(root); } };
})();
