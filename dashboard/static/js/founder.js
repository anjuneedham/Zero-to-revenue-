// Founder Dashboard. All DOM via createElement/textContent (user text is never parsed as HTML).
(function () {
  const { el, add, text, pill, btn, card, fmt, nice } = Z;
  const OVERRIDE = "z2r_focus_override";  // per-device convenience: the task the founder chose instead
  let D = null, filters = { business: "", status: "", urgency: "" };

  const day = d => (d ? new Date(d.length === 10 ? d + "T00:00:00" : d).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }) : "");
  const num = (v, u) => (v == null ? "n/a" : fmt.num(v, 2) + (u ? " " + u : ""));
  const bad = s => s && s.error;
  const sectionErr = (title, retry) => { const c = card(title); c.append(el("p", "err", "This section could not be loaded."), btn("Retry", "small", retry)); return c; };
  const kindOf = s => ({ blocked: "bad", doing: "royal", done: "ok", todo: "" }[s] || "");

  // ---- generic create form in the drawer: posts to the Phase 1 API, /api/founder/businesses/<slug>/<entity> ----
  const bizOpts = () => D.businesses.map(b => [b.slug, b.name]);
  const taskOpts = () => [["", "None"], ...(Array.isArray(D.priorities) ? D.priorities.map(t => [t.id, t.business_name + ": " + t.title]) : [])];
  const goalOpts = () => [["", "None"], ...(Array.isArray(D.goals) ? D.goals.map(g => [g.id, g.business_name + ": " + g.title]) : [])];
  // field = [name, label, type, options, required, defaultChecked]; type "int"/"num" are sent as numbers, empty fields are omitted
  const FORMS = {
    task: { title: "Add a task", entity: "work-tasks", fields: () => [
      ["business", "Business", "select", bizOpts(), true], ["title", "Task", "text", null, true], ["due_date", "Due date", "date"],
      ["impact", "Impact (1-5, optional)", "int"], ["effort_hours", "Effort in hours (optional)", "num"], ["priority", "Your priority (1 = highest, 5 = lowest; default 3)", "int"],
      ["expected_outcome", "Expected outcome (optional)", "text"], ["next_step", "Next concrete step (optional)", "text"],
      ["goal_id", "Goal (optional, same business)", "select", goalOpts()], ["depends_on", "Waits on task (optional, same business)", "select", taskOpts()]] },
    blocker: { title: "Record a blocker", entity: "blockers", fields: () => [
      ["business", "Business", "select", bizOpts(), true], ["description", "What is blocking progress?", "text", null, true],
      ["impact", "Consequence (optional)", "text"], ["suggested_action", "Suggested way out (optional)", "text"], ["work_task_id", "Related task (optional, same business)", "select", taskOpts()]] },
    goal: { title: "Add a goal", entity: "goals", fields: () => [["business", "Business", "select", bizOpts(), true], ["title", "Goal", "text", null, true],
      ["target_metric", "Metric (optional)", "text"], ["target_value", "Target value (optional)", "num"], ["due_date", "Due date", "date"]] },
    kpi: { title: "Add a KPI", entity: "kpis", fields: () => [
      ["business", "Business", "select", bizOpts(), true], ["name", "KPI name", "text", null, true], ["unit", "Unit (e.g. users, $, %)", "text"],
      ["baseline_value", "Baseline (optional)", "num"], ["target_value", "Target (optional)", "num"], ["period", "Reporting period (e.g. weekly)", "text"],
      ["direction", "Better when it goes", "select", [["up", "Up"], ["down", "Down"]]], ["is_primary", "Primary KPI for this business", "checkbox"]] },
    reading: { title: "Record a KPI value", fields: () => [
      ["kpi_id", "KPI", "select", (D.kpis || []).map(k => [k.id, k.business_name + ": " + k.name + (k.unit ? " (" + k.unit + ")" : "")]), true], ["value", "Current value", "num", null, true]] },
    experiment: { title: "Add an experiment", entity: "experiments", fields: () => [
      ["business", "Business", "select", bizOpts(), true], ["hypothesis", "Hypothesis", "text", null, true],
      ["success_metric", "Primary success metric", "text"], ["duration_days", "Duration in days (needed to start)", "int"], ["baseline_value", "Baseline (optional)", "num"], ["target_value", "Target (optional)", "num"],
      ["review_date", "Review date", "date"], ["next_action", "Next action", "text"]] },
    decision: { title: "Record a decision", entity: "decisions", fields: () => [
      ["business", "Business", "select", bizOpts(), true], ["title", "Decision", "text", null, true], ["rationale", "Rationale / evidence", "text"],
      ["status", "Status", "select", [["decided", "Decided"], ["proposed", "Proposed"]]]] },
  };

  // Reusable form dialog (also used by the business workspaces). field = [name, label, type, options, required, defaultChecked];
  // submit(body) gets only the non-empty fields; "int"/"num" are numbers. It throws to show an error, resolves to close + refresh.
  function formDialog(title, fields, submit, preset) {
    const form = el("form", "list"), inputs = {};
    fields.forEach(([id, label, type, opts, req, dflt]) => {
      const wrap = el("label", "f"); wrap.append(document.createTextNode(label + (req ? " *" : "")));
      let inp;
      if (type === "select") { inp = el("select"); opts.forEach(([v, l]) => { const o = el("option", null, l); o.value = v; inp.append(o); }); }
      else if (type === "checkbox") { inp = el("input"); inp.type = "checkbox"; inp.checked = dflt === true; inp.style.width = "auto"; inp.style.minHeight = "0"; }
      else { inp = el("input"); inp.type = type === "date" ? "date" : type === "text" ? "text" : "number"; if (type === "num") inp.step = "any"; if (type === "int") { inp.step = "1"; inp.min = "0"; } if (type === "text") inp.maxLength = 400; }
      if (req && type !== "checkbox") inp.required = true;
      if (preset && preset[id] != null && type !== "checkbox") inp.value = preset[id];
      inp.name = id; inputs[id] = [inp, type]; wrap.append(inp); form.append(wrap);
    });
    const err = el("p", "err"); err.setAttribute("role", "alert");
    const submitBtn = el("button", "btn gold", "Save"); submitBtn.type = "submit";
    form.append(err, submitBtn);
    form.onsubmit = async e => {
      e.preventDefault(); err.textContent = ""; submitBtn.disabled = true;  // disabled while saving: no double submit
      const body = {};
      Object.entries(inputs).forEach(([id, [inp, type]]) => {
        if (type === "checkbox") { body[id] = inp.checked; return; }
        if (inp.value === "") return;
        body[id] = type === "int" || type === "num" ? Number(inp.value) : inp.value;
      });
      try { await submit(body); Z.toast("Saved", "ok"); Z.$("drawer").close(); await Z.rerender(); }
      catch (x) { if (x.message !== "Signed out") err.textContent = x.message; submitBtn.disabled = false; }
    };
    Z.openDrawer(title, form);
  }
  Z.formDialog = formDialog;

  function openForm(name, preset) {
    const f = FORMS[name];
    formDialog(f.title, f.fields(), async body => {
      if (name === "reading") { await Z.api("/api/founder/kpis/" + body.kpi_id + "/readings", "POST", { value: body.value }); return; }
      const slug = body.business; delete body.business;
      await Z.api("/api/founder/businesses/" + slug + "/" + f.entity, "POST", body);
    }, preset);
  }
  Z.openFounderForm = async (name, slug) => { if (!D || !D.businesses) D = await Z.api("/api/founder/dashboard"); openForm(name, { business: slug }); };

  function detail(title, rows) {
    const box = el("div", "list");
    rows.filter(([, v]) => v != null && v !== "").forEach(([k, v]) => { const r = el("div"); add(r, el("div", "label", k), el("div", null, String(v))); box.append(r); });
    Z.openDrawer(title, box);
  }

  async function setStatus(t, status) { await Z.api("/api/founder/work-tasks/" + t.id, "POST", { status }); Z.toast("Task marked " + nice(status).toLowerCase(), "ok"); await Z.rerender(); }

  // ---- task row ----
  function taskRow(t, opts) {
    const it = el("div", "item");
    it.append(el("div", "t", t.title));
    const m = el("div", "meta");
    add(m, pill(t.business_name || "?", "royal"), pill(nice(t.status), kindOf(t.status)));
    if (t.due_date) m.append(pill((t.days_until_due < 0 ? "overdue · " : t.days_until_due === 0 ? "today · " : "due ") + day(t.due_date), t.days_until_due < 0 ? "bad" : t.days_until_due <= 1 ? "warn" : ""));
    if (t.effort_hours != null) m.append(pill(fmt.num(t.effort_hours, 1) + " h"));
    if (t.impact) m.append(pill("impact " + t.impact + "/5"));
    if (t.goal_title) m.append(pill("goal: " + t.goal_title));
    it.append(m);
    if (t.blocked_by.length) it.append(el("p", "flags", "Blocked: " + t.blocked_by.join("; ")));
    it.append(el("p", "sub", (t.eligible ? "Ranked because: " : "Not recommended: ") + (t.why.length ? t.why.join(", ") : "no urgency, impact or effort data recorded") + " (score " + t.score + ")"));
    const row = el("div", "row");
    if (t.status !== "doing") row.append(btn("Start", "small", () => setStatus(t, "doing")));
    row.append(btn("Mark done", "gold small", () => setStatus(t, "done")));
    if (t.status !== "blocked") row.append(btn("Blocked", "ghost small", () => setStatus(t, "blocked")));
    else row.append(btn("Unblock", "ghost small", () => setStatus(t, "todo")));
    row.append(btn("Details", "ghost small", async () => detail(t.title, [["Business", t.business_name], ["Status", nice(t.status)], ["Due", t.due_date && day(t.due_date)], ["Effort", t.effort_hours != null && t.effort_hours + " h"],
      ["Impact", t.impact && t.impact + "/5"], ["Goal", t.goal_title], ["Expected outcome", t.expected_outcome], ["Next step", t.next_step], ["Why ranked", t.why.join(", ")], ["Missing data", t.gaps.join(", ")]])));
    it.append(row); return it;
  }

  // ---- sections ----
  function header(root) {
    const bar = el("section", "card hero");
    const r = D.recommendation;
    add(bar, el("div", "label", new Date(D.today + "T00:00:00").toLocaleDateString([], { weekday: "long", month: "long", day: "numeric", year: "numeric" })));
    const a = D.attention;
    bar.append(el("p", "sub", a ? `${a.overdue} overdue · ${a.due_today} due today · ${a.open_blockers} open blocker(s)` : "Attention summary unavailable"));
    const b = btn("What should I do next?", "gold", async () => { await Z.rerender(); const t = document.getElementById("next-card"); if (t) { t.scrollIntoView({ block: "start" }); t.focus({ preventScroll: true }); } });
    bar.append(Z.add(el("div", "row"), b));
    root.append(bar);
  }

  function recommendation(root) {
    const c = card("What should I do next?", "Deterministic ranking of your recorded tasks - a suggestion, not an order.");
    c.id = "next-card"; c.tabIndex = -1; c.classList.add("hero");
    const r = D.recommendation, ov = Z.store.get(OVERRIDE);
    const pick = Array.isArray(D.priorities) ? D.priorities.find(t => t.id === ov) : null;
    if (!r.action) {
      add(c, el("p", null, r.missing.join(" ")), el("p", "sub", r.hint || ""));
      if (D.businesses.length) c.append(btn("Add a task", "gold", async () => openForm("task")));
      root.append(c); return;
    }
    if (pick) {
      add(c, pill("Your choice (overrides the suggestion)", "gold"), el("div", "t", pick.title), el("p", "sub", pick.business_name + " · suggestion was: " + r.action));
      c.append(Z.add(el("div", "row"), btn("Use the suggestion instead", "ghost small", async () => { Z.store.del(OVERRIDE); await Z.rerender(); })));
      root.append(c); return;
    }
    add(c, el("div", "t", r.action), Z.add(el("div", "meta"), pill(r.business || "", "royal"), pill("evidence: " + r.evidence), r.effort_hours != null ? pill(fmt.num(r.effort_hours, 1) + " h") : null));
    const ul = el("ul", "plain"); r.why.forEach(w => ul.append(el("li", null, w)));
    add(c, el("div", "label", "Why"), ul, el("div", "label", "Expected outcome"), el("p", null, r.expected_outcome), el("div", "label", "Next concrete step"), el("p", null, r.next_step));
    if (r.risks.length) { const rl = el("ul", "plain"); r.risks.forEach(x => rl.append(el("li", null, x))); add(c, el("div", "label", "Dependencies and risks"), rl); }
    const row = el("div", "row");
    row.append(btn("Start this", "gold", async () => { if (r.task_id) await Z.api("/api/founder/work-tasks/" + r.task_id, "POST", { status: "doing" }); await Z.rerender(); }));
    c.append(row);
    if (r.alternatives.length) {
      c.append(el("div", "label", "Prefer something else? Choose it yourself"));
      const alts = el("div", "row");
      r.alternatives.forEach(x => alts.append(btn(x.title.length > 40 ? x.title.slice(0, 40) + "…" : x.title, "ghost small", async () => { Z.store.set(OVERRIDE, x.task_id); await Z.rerender(); })));
      c.append(alts);
    }
    c.append(el("p", "sub", "Score " + r.score + ". Method: business priority + urgency + impact + effort + progress + unblocking, see docs/PHASE_HANDOFF.md."));
    root.append(c);
  }

  function businessCards(root) {
    const c = card("Your four businesses", "In priority order. Only recorded data is shown.");
    if (!D.cards.length) { c.append(Z.empty("No businesses found", "Business records come from the businesses table (Phase 1, migration 007).")); root.append(c); return; }
    const g = el("div", "cols");
    D.cards.forEach(b => {
      const col = el("div", "col");
      col.append(Z.add(el("h3", null, "P" + b.priority + " · " + b.name), pill(nice(b.status), b.status === "active" ? "ok" : "warn")));
      col.append(el("p", "sub", b.objective ? "Objective: " + b.objective : "No goal or objective recorded yet."));
      const k = b.primary_kpi;
      col.append(k ? Z.add(el("div"), el("div", "label", k.name), el("div", "stat", num(k.current, k.unit)), el("p", "sub", (k.target_value != null ? "target " + num(k.target_value, k.unit) + " · " : "") + "updated " + fmt.ago(k.last_updated)))
        : el("p", "sub", "No KPI value recorded."));
      col.append(b.bottleneck ? el("p", "flags", "Blocker: " + b.bottleneck.description) : el("p", "sub", b.open_blockers === 0 ? "No recorded blockers." : "Blockers unavailable."));
      col.append(b.next_action ? el("p", null, "Next: " + b.next_action.title) : el("p", "sub", b.open_tasks ? "All open tasks are blocked." : "No open tasks."));
      col.append(el("p", "sub", b.open_tasks == null ? "Task count unavailable" : `${b.open_tasks} open task(s), ${b.blocked_tasks} blocked`));
      col.append(btn("Show its tasks", "ghost small", async () => { filters.business = b.id; await Z.rerender(); document.getElementById("today-card")?.scrollIntoView(); }));
      if (Z.pages[b.slug]) { const a = el("a", "btn small", "Open workspace"); a.href = "#" + b.slug; col.append(a); }
      g.append(col);
    });
    c.append(g); root.append(c);
  }

  function priorities(root) {
    const c = card("Today's priorities", "Ranked from recorded tasks. Nothing is completed automatically.");
    c.id = "today-card";
    if (bad(D.priorities)) { root.append(sectionErr("Today's priorities", () => Z.rerender())); return; }
    const sel = (label, key, opts) => { const l = el("label", "f", label), s = el("select"); opts.forEach(([v, t]) => { const o = el("option", null, t); o.value = v; s.append(o); }); s.value = filters[key]; s.onchange = () => { filters[key] = s.value; Z.rerender(); }; l.append(s); return l; };
    c.append(Z.add(el("div", "cols"), sel("Business", "business", [["", "All"], ...D.businesses.map(v => [v.id, v.name])]), sel("Status", "status", [["", "Any"], ["todo", "To do"], ["doing", "In progress"], ["blocked", "Blocked"]]),
      sel("Urgency", "urgency", [["", "Any"], ["overdue", "Overdue"], ["soon", "Due within 3 days"], ["none", "No due date"]])));
    let rows = D.priorities.filter(t => (!filters.business || t.business_id === filters.business) && (!filters.status || t.status === filters.status) &&
      (!filters.urgency || (filters.urgency === "overdue" ? t.days_until_due != null && t.days_until_due < 0 : filters.urgency === "soon" ? t.days_until_due != null && t.days_until_due <= 3 : t.days_until_due == null)));
    if (!rows.length) c.append(Z.empty(D.priorities.length ? "No tasks match these filters" : "No open tasks recorded", D.priorities.length ? "Clear a filter to see more." : "Add your first task with the Add a task action."));
    else { const l = el("div", "list"); rows.slice(0, 15).forEach(t => l.append(taskRow(t))); c.append(l); if (rows.length > 15) c.append(el("p", "sub", (rows.length - 15) + " more not shown; filter to narrow.")); }
    if (D.done_today.length) c.append(el("p", "sub", "Done today: " + D.done_today.map(t => t.title).join(", ")));
    root.append(c);
  }

  function blockers(root) {
    if (bad(D.blockers)) { root.append(sectionErr("Bottlenecks and blockers", () => Z.rerender())); return; }
    const c = card("Bottlenecks and blockers", "Recorded blockers are facts you entered; inferred risks are derived from your tasks.");
    if (!D.blockers.length && !D.inferred_risks.length) c.append(Z.empty("No blockers recorded", "Use Record a blocker when something is stopping progress."));
    const l = el("div", "list");
    D.blockers.forEach(b => {
      const it = el("div", "item"); it.append(el("div", "t", b.description));
      it.append(Z.add(el("div", "meta"), pill("recorded", "warn"), pill(b.business_name || "", "royal"), b.days_open != null ? pill("open " + b.days_open + " d") : null));
      if (b.impact) it.append(el("p", "sub", "Consequence: " + b.impact));
      if (b.suggested_action) it.append(el("p", "sub", "Suggested next action (your note): " + b.suggested_action));
      if (b.task_title) it.append(el("p", "sub", "Related task: " + b.task_title));
      it.append(Z.add(el("div", "row"), btn("Mark resolved", "small", async () => { await Z.api("/api/founder/blockers/" + b.id, "POST", { status: "resolved" }); Z.toast("Blocker resolved", "ok"); await Z.rerender(); })));
      l.append(it);
    });
    D.inferred_risks.slice(0, 6).forEach(b => { const it = el("div", "item"); it.append(el("div", "t", b.description)); it.append(Z.add(el("div", "meta"), pill("inferred, not verified"), pill(b.business_name || "", "royal"))); l.append(it); });
    c.append(l); root.append(c);
  }

  function trend(k) {
    if (!k.trend) return "";
    const arrow = k.trend.direction === "up" ? "▲" : k.trend.direction === "down" ? "▼" : "■";
    return arrow + " " + fmt.num(Math.abs(k.trend.delta), 2) + " since " + fmt.ago(k.trend.since);
  }
  function goalsKpis(root) {
    if (bad(D.kpis)) { root.append(sectionErr("Goals and KPIs", () => Z.rerender())); return; }
    const c = card("Goals and KPIs", "Each KPI is shown in its own unit and business; nothing is added up across businesses.");
    if (Array.isArray(D.goals)) D.goals.forEach(g => c.append(el("p", "sub", g.business_name + " goal: " + g.title)));
    if (!D.kpis.length) c.append(Z.empty("No KPIs recorded", "Use Add a KPI, then Record a KPI value."));
    const l = el("div", "list");
    D.kpis.forEach(k => {
      const it = el("div", "item"); it.append(el("div", "t", k.name));
      it.append(Z.add(el("div", "meta"), pill(k.business_name || "", "royal"), k.period ? pill(k.period) : null, k.goal_title ? pill("goal: " + k.goal_title) : null));
      it.append(el("div", "stat", num(k.current, k.unit)));
      it.append(el("p", "sub", [k.target_value != null ? "target " + num(k.target_value, k.unit) : "", k.baseline_value != null ? "baseline " + num(k.baseline_value, k.unit) : "", trend(k), k.last_updated ? "updated " + fmt.ago(k.last_updated) : "no value recorded"].filter(Boolean).join(" · ")));
      if (k.progress_pct != null) { const b = el("div", "bar"); const i = el("i"); i.style.width = k.progress_pct + "%"; b.append(i); b.setAttribute("role", "img"); b.setAttribute("aria-label", k.progress_pct + "% of the way from baseline to target"); it.append(b, el("p", "sub", k.progress_pct + "% from baseline to target")); }
      l.append(it);
    });
    c.append(l); root.append(c);
  }

  function experiments(root) {
    if (bad(D.experiments)) { root.append(sectionErr("Active experiments", () => Z.rerender())); return; }
    const c = card("Active experiments", "Planned and running only.");
    if (!D.experiments.length) c.append(Z.empty("No active experiments", "Use Add an experiment to track one."));
    const l = el("div", "list");
    D.experiments.forEach(e => {
      const it = el("div", "item click"); it.tabIndex = 0; it.setAttribute("role", "button");
      it.append(el("div", "t", e.hypothesis), Z.add(el("div", "meta"), pill(e.business_name, "royal"), pill(nice(e.status), e.status === "running" ? "royal" : ""), e.review_date ? pill("review " + day(e.review_date)) : null));
      if (e.success_metric) it.append(el("p", "sub", "Success metric: " + e.success_metric));
      if (e.next_action) it.append(el("p", null, "Next: " + e.next_action));
      const open = () => detail(e.hypothesis, [["Business", e.business_name], ["Status", nice(e.status)], ["Method", e.method], ["Primary metric", e.success_metric], ["Baseline", e.baseline_value], ["Target", e.target_value], ["Review date", e.review_date && day(e.review_date)], ["Next action", e.next_action]]);
      it.onclick = open; it.onkeydown = ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } };
      l.append(it);
    });
    c.append(l); root.append(c);
  }

  function aiUsage(root) {
    const u = D.ai_usage;
    if (bad(u)) { root.append(sectionErr("AI usage", () => Z.rerender())); return; }
    const c = card("AI usage", "From the recorded request log. Requests, tokens and cost are separate measures.");
    if (!u.available) { c.append(Z.empty("No AI usage recorded this month", "Nothing has called the model yet, or usage logging is off.")); root.append(c); return; }
    const line = (label, m) => el("p", null, `${label}: ${m.requests} request(s) · ${fmt.num(m.input_tokens, 0)} in / ${fmt.num(m.output_tokens, 0)} out tokens · $${fmt.num(m.cost_usd, 4)} recorded cost` + (m.failed ? ` · ${m.failed} failed` : ""));
    u.sources.forEach(src => { add(c, el("div", "label", src.name), line("Today", src.today), line("This month", src.month)); if (src.note) c.append(el("p", "sub", src.note)); });
    if (u.monthly_cap_usd) c.append(el("p", "sub", `Configured monthly cap $${fmt.num(u.monthly_cap_usd, 2)} (Scout's ledger enforces it).`));
    else c.append(el("p", "sub", "No monthly cap configured, so no remaining budget is shown."));
    if (u.by_business.length) u.by_business.forEach(p => c.append(el("p", "sub", `${p.business_name}: ${p.requests} request(s), $${fmt.num(p.cost_usd, 4)}`)));
    else c.append(el("p", "sub", "Scout's log has no business column, so usage is not split by business."));
    root.append(c);
  }

  function decisions(root) {
    if (bad(D.decisions)) { root.append(sectionErr("Recent decisions", () => Z.rerender())); return; }
    const c = card("Recent decisions");
    if (!D.decisions.length) c.append(Z.empty("No decisions recorded", "Use Record a decision to keep a trail of why you chose what you chose."));
    const l = el("div", "list");
    D.decisions.forEach(d => {
      const it = el("div", "item click"); it.tabIndex = 0; it.setAttribute("role", "button");
      it.append(el("div", "t", d.title), Z.add(el("div", "meta"), pill(d.business_name, "royal"), pill(nice(d.status)), pill(day(d.decided_at || d.created_at))));
      if (d.decision || d.rationale) it.append(el("p", "sub", d.decision || d.rationale));
      const open = () => detail(d.title, [["Business", d.business_name], ["Status", nice(d.status)], ["Decided", d.decided_at && day(d.decided_at)], ["Decision", d.decision], ["Context", d.context], ["Rationale", d.rationale], ["Alternatives", d.alternatives]]);
      it.onclick = open; it.onkeydown = ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } };
      l.append(it);
    });
    c.append(l); root.append(c);
  }

  function quick(root) {
    const c = card("Quick actions");
    if (!D.businesses.length) { c.append(Z.empty("Nothing to act on", "No businesses exist yet.")); root.append(c); return; }
    const row = el("div", "row");
    [["task", "Add a task"], ["blocker", "Record a blocker"], ["goal", "Add a goal"], ["kpi", "Add a KPI"], ["experiment", "Add an experiment"], ["decision", "Record a decision"]]
      .forEach(([k, l]) => row.append(btn(l, "ghost small", async () => openForm(k))));
    if (Array.isArray(D.kpis) && D.kpis.length) row.append(btn("Record a KPI value", "ghost small", async () => openForm("reading")));
    c.append(row); root.append(c);
  }

  Z.pages.founder = {
    title: "Founder Dashboard", sub: "What matters, what's blocked, what's next", icon: "founder",
    async render(root) {
      D = await Z.api("/api/founder/dashboard");
      const wrap = el("div", "list");
      header(wrap); recommendation(wrap);
      const g = el("div", "grid"); const put = (cls, fn) => { const h = el("div", cls); fn(h); g.append(h); };
      wrap.append(g);
      put("s12", businessCards); put("s8", priorities); put("s4", blockers); put("s6", goalsKpis); put("s6", experiments);
      put("s6", decisions); put("s6", aiUsage); put("s12", quick);
      root.append(wrap);
    },
  };
})();
