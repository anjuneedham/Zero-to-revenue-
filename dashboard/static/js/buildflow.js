// BuildFlow workspace (Phase 3). One business only: everything here comes from /api/founder/workspace/buildflow.
(function () {
  const { el, add, pill, btn, card, fmt, nice } = Z;
  let SLUG = "buildflow"; const TABS = [["overview", "Overview"], ["content", "Content"], ["feedback", "Feedback"], ["pipeline", "Pipeline"], ["notes", "Notes"]];
  const PLATFORMS = [["youtube_shorts", "YouTube Shorts"], ["tiktok", "TikTok"], ["instagram", "Instagram"], ["facebook", "Facebook"], ["other", "Other"]];
  const plat = v => (PLATFORMS.find(p => p[0] === v) || [0, nice(v)])[1];
  const day = d => (d ? new Date(d.length === 10 ? d + "T00:00:00" : d).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }) : "");
  const bad = s => s && s.error;
  let W = null, tab = Z.store.get("z2r_bf_tab") || "overview";
  const post = (path, body) => Z.api(path, "POST", body || {});
  const secErr = title => { const c = card(title); c.append(el("p", "err", "This section could not be loaded."), btn("Retry", "small", () => Z.rerender())); return c; };
  const none = (t, h) => Z.empty(t, h);

  function tile(label, value, sub) { const t = el("div", "tile"); add(t, el("div", "label", label), el("div", "stat", value), sub ? el("p", "sub", sub) : null); return t; }

  // ---- overview ----
  function overview(root) {
    const g = el("div", "grid");
    const top = Array.isArray(W.tasks) ? W.tasks.find(t => t.eligible) : null;
    const c1 = card(W.business.name + " right now", W.business.description || ""); c1.classList.add("s12");
    const m = el("div", "meta"); add(m, pill("stage: " + nice(W.business.stage), "royal"), pill("priority " + (W.business.priority || "?")));
    c1.append(m);
    if (Array.isArray(W.goals)) W.goals.forEach(x => c1.append(el("p", null, "Objective: " + x.title + (x.target_value != null ? " (target " + fmt.num(x.target_value, 2) + (x.target_metric ? " " + x.target_metric : "") + ")" : ""))));
    if (Array.isArray(W.goals) && !W.goals.length) c1.append(el("p", "sub", "No objective recorded yet."));
    c1.append(top ? Z.add(el("p", null, "Next: " + top.title), el("p", "sub", "Ranked because: " + (top.why.join(", ") || "no urgency, impact or effort recorded"))) : el("p", "sub", "No open tasks to recommend."));
    c1.append(Z.add(el("div", "row"), btn("Add task", "ghost small", async () => Z.openFounderForm("task", SLUG)), btn("Record blocker", "ghost small", async () => Z.openFounderForm("blocker", SLUG)),
      SLUG === "buildflow" ? btn("Import launch plan as tasks", "ghost small", async () => { const r = await post("/api/founder/workspace/buildflow/import-launch-plan"); Z.toast(r.created + " task(s) added, " + r.skipped + " already there", "ok"); await Z.rerender(); }) : null));
    if (SLUG === "buildflow") c1.append(el("p", "sub", "The launch plan is your own list from docs/strategy/BUILDFLOW_LAUNCH_PLAN.md; importing adds each item once."));
    g.append(c1);

    const k = card("KPIs", "Only values you recorded."); k.classList.add("s6");
    if (bad(W.kpis)) g.append(secErr("KPIs")); else {
      if (!W.kpis.length) k.append(none("No KPIs yet", "Add one, then record values (e.g. activated contractors)."));
      W.kpis.forEach(x => { const t = el("div", "item"); add(t, el("div", "t", x.name), el("div", "stat", x.current == null ? "no value" : fmt.num(x.current, 2) + (x.unit ? " " + x.unit : "")),
        el("p", "sub", [x.target_value != null ? "target " + fmt.num(x.target_value, 2) : "", x.trend ? (x.trend.direction === "up" ? "▲ " : x.trend.direction === "down" ? "▼ " : "■ ") + fmt.num(Math.abs(x.trend.delta), 2) : "", x.progress_pct != null ? x.progress_pct + "% to target" : "", x.last_updated ? "updated " + fmt.ago(x.last_updated) : ""].filter(Boolean).join(" · ")));
        k.append(t); });
      k.append(Z.add(el("div", "row"), btn("Add KPI", "ghost small", async () => Z.openFounderForm("kpi", SLUG)), W.kpis.length ? btn("Record value", "ghost small", async () => Z.openFounderForm("reading", SLUG)) : null));
      g.append(k);
    }

    const b = card("Blockers", "Recorded by you."); b.classList.add("s6");
    if (bad(W.blockers)) g.append(secErr("Blockers")); else {
      if (!W.blockers.length) b.append(none("No recorded blockers"));
      W.blockers.forEach(x => { const it = el("div", "item"); add(it, el("div", "t", x.description), x.impact ? el("p", "sub", "Consequence: " + x.impact) : null, x.task_title ? el("p", "sub", "Task: " + x.task_title) : null,
        Z.add(el("div", "row"), btn("Mark resolved", "small", async () => { await post("/api/founder/blockers/" + x.id, { status: "resolved" }); await Z.rerender(); }))); b.append(it); });
      g.append(b);
    }

    const t = card("Open tasks", "Ranked with the same logic as the Founder dashboard."); t.classList.add("s12");
    if (bad(W.tasks)) g.append(secErr("Open tasks")); else {
      if (!W.tasks.length) t.append(none("No open BuildFlow tasks", "Add one, or import your launch plan."));
      const l = el("div", "list");
      W.tasks.slice(0, 12).forEach(x => { const it = el("div", "item"); it.append(el("div", "t", x.title));
        const mm = el("div", "meta"); add(mm, pill(nice(x.status), x.status === "blocked" ? "bad" : x.status === "doing" ? "royal" : ""), x.due_date ? pill("due " + day(x.due_date)) : null, x.impact ? pill("impact " + x.impact + "/5") : null);
        it.append(mm); if (x.blocked_by.length) it.append(el("p", "flags", "Blocked: " + x.blocked_by.join("; ")));
        const set = async s => { await post("/api/founder/work-tasks/" + x.id, { status: s }); await Z.rerender(); };
        it.append(Z.add(el("div", "row"), x.status !== "doing" ? btn("Start", "small", () => set("doing")) : null, btn("Mark done", "gold small", () => set("done")))); l.append(it); });
      t.append(l); if (W.tasks.length > 12) t.append(el("p", "sub", (W.tasks.length - 12) + " more on the Founder dashboard."));
      g.append(t);
    }
    root.append(g);
  }

  // ---- content ----
  const CONTENT_FIELDS = (withStatus) => [["platform", "Platform", "select", PLATFORMS, true], ["topic", "Topic", "text"], ["hook", "Hook (first line)", "text"], ["format", "Format (e.g. talking head, screen recording)", "text"],
    ...(withStatus ? [["status", "Status", "select", [["idea", "Idea"], ["scripted", "Scripted"], ["filmed", "Filmed"], ["posted", "Posted"], ["dropped", "Dropped"]]], ["url", "Post link", "text"], ["views", "Views", "int"], ["likes", "Likes", "int"], ["comments", "Comments", "int"], ["shares", "Shares", "int"], ["signups", "Signups you can attribute", "int"]] : [])];
  function groupLines(title, rows) {
    const box = el("div"); box.append(el("div", "label", title));
    if (!rows.length) box.append(el("p", "sub", "No posted content yet."));
    rows.forEach(r => box.append(el("p", "sub", `${r.name}: ${r.posts} post(s), ${r.with_views} with views` + (r.avg_views != null ? ` · avg ${fmt.num(r.avg_views, 0)} views` : " · no views recorded") + (r.with_signups ? ` · ${r.signups} signup(s)` : ""))));
    return box;
  }
  function content(root) {
    if (bad(W.content)) { root.append(secErr("Content")); return; }
    const s = W.content.summary, c = card("Content", "YouTube Shorts, TikTok, Instagram, Facebook. Numbers are what you recorded, not pulled from the platforms.");
    const tiles = el("div", "tiles"); add(tiles, tile("Posted today", s.posted_today), tile("Posted, last 7 days", s.posted_last_7_days), tile("Posted, no metrics yet", s.posted_missing_metrics), tile("Ideas in the queue", s.by_status.idea + s.by_status.scripted + s.by_status.filmed));
    c.append(tiles, Z.add(el("div", "row"), btn("Add content", "gold small", async () => Z.formDialog("Add content", CONTENT_FIELDS(false), b => post("/api/founder/businesses/" + SLUG + "/content-items", b), { platform: "tiktok" }))));
    c.append(el("p", "sub", s.caveat));
    root.append(c);
    const p = card("What is working (so far)"); p.append(groupLines("By platform", s.by_platform.map(r => ({ ...r, name: plat(r.name) }))), groupLines("By format", s.by_format), groupLines("By topic", s.by_topic)); root.append(p);
    const l = card("Recent content");
    if (!W.content.items.length) l.append(none("Nothing tracked yet", "Add each video idea; update it when posted, then record views."));
    W.content.items.forEach(x => { const it = el("div", "item"); it.append(el("div", "t", x.hook || x.topic || "(untitled)"));
      it.append(Z.add(el("div", "meta"), pill(plat(x.platform), "royal"), pill(nice(x.status), x.status === "posted" ? "ok" : ""), x.format ? pill(x.format) : null, x.views != null ? pill(fmt.num(x.views, 0) + " views") : (x.status === "posted" ? pill("no metrics", "warn") : null), x.signups != null ? pill(x.signups + " signups") : null));
      it.append(Z.add(el("div", "row"), btn("Update", "ghost small", async () => Z.formDialog("Update content", CONTENT_FIELDS(true), b => post("/api/founder/content-items/" + x.id, b), x)), x.url ? Object.assign(el("a", "btn ghost small", "Open post"), { href: x.url, target: "_blank", rel: "noopener noreferrer" }) : null));
      l.append(it); });
    root.append(l);
  }

  // ---- feedback ----
  const KINDS = [["bug", "Bug"], ["feature", "Feature request"], ["pricing", "Pricing"], ["onboarding", "Onboarding"], ["praise", "Praise"], ["other", "Other"]];
  function feedback(root) {
    if (bad(W.feedback)) { root.append(secErr("Feedback")); return; }
    const c = card("Customer feedback", "Log what contractors and customers tell you, then turn it into work.");
    c.append(Z.add(el("div", "row"), btn("Log feedback", "gold small", async () => Z.formDialog("Log feedback", [["body", "What did they say?", "text", null, true], ["kind", "Type", "select", KINDS], ["source", "Where from (e.g. WhatsApp, interview)", "text"], ["contact", "Who (optional)", "text"]],
      b => post("/api/founder/businesses/" + SLUG + "/feedback-items", b)))));
    if (!W.feedback.length) c.append(none("No feedback logged yet"));
    const l = el("div", "list");
    W.feedback.forEach(x => { const it = el("div", "item"); it.append(el("div", "t", x.body));
      it.append(Z.add(el("div", "meta"), pill(nice(x.kind), x.kind === "bug" ? "bad" : ""), pill(nice(x.status), x.status === "actioned" ? "ok" : x.status === "new" ? "warn" : ""), x.source ? pill(x.source) : null, x.contact ? pill(x.contact) : null));
      const row = el("div", "row"), set = async s => { await post("/api/founder/feedback-items/" + x.id, { status: s }); await Z.rerender(); };
      if (!x.work_task_id && x.status !== "dismissed") row.append(btn("Create task", "gold small", async () => { await post("/api/founder/feedback-items/" + x.id + "/to-task"); Z.toast("Task created", "ok"); await Z.rerender(); }));
      if (x.work_task_id) row.append(el("span", "sub", "Task created"));
      if (x.status === "new") row.append(btn("Triaged", "ghost small", () => set("triaged")));
      if (x.status !== "dismissed" && !x.work_task_id) row.append(btn("Dismiss", "ghost small", () => set("dismissed")));
      it.append(row); l.append(it); });
    c.append(l); root.append(c);
  }

  // ---- pipeline ----
  function pipeline(root) {
    const p = W.pipeline;
    if (bad(p)) { root.append(secErr("Pipeline")); return; }
    const c = card("Outreach pipeline", p.source);
    const tiles = el("div", "tiles"); Object.entries(p.counts).forEach(([k, v]) => tiles.append(tile(nice(k), v))); if (!p.total) c.append(none("No leads yet", "Import them from the Operator page."));
    else c.append(tiles);
    c.append(el("p", "sub", "This is the outreach list only. There is no contractor or customer CRM yet, so no conversion numbers are shown."));
    p.recent.forEach(x => c.append(el("p", "sub", (x.business || x.name || "(unnamed)") + " · " + nice(x.status) + " · " + day(x.created_at))));
    c.append(Object.assign(el("a", "btn ghost small", "Open Operator"), { href: "#operator" }));
    root.append(c);
  }

  // ---- notes: decisions, experiments, knowledge/constraints ----
  function notes(root) {
    const d = card("Decisions");
    d.append(Z.add(el("div", "row"), btn("Record decision", "ghost small", async () => Z.openFounderForm("decision", SLUG))));
    if (bad(W.decisions)) d.append(el("p", "err", "Could not load.")); else if (!W.decisions.length) d.append(none("No BuildFlow decisions recorded"));
    else W.decisions.forEach(x => d.append(Z.add(el("div", "item"), el("div", "t", x.title), el("p", "sub", nice(x.status) + (x.decided_at ? " · " + day(x.decided_at) : "") + (x.rationale ? " · " + x.rationale : "")))));
    root.append(d);
    const e = card("Experiments");
    e.append(Z.add(el("div", "row"), btn("Add experiment", "ghost small", async () => Z.openFounderForm("experiment", SLUG))));
    if (bad(W.experiments)) e.append(el("p", "err", "Could not load.")); else if (!W.experiments.length) e.append(none("No experiments yet"));
    else W.experiments.forEach(x => e.append(Z.add(el("div", "item"), el("div", "t", x.hypothesis), Z.add(el("div", "meta"), pill(nice(x.status), x.status === "running" ? "royal" : ""), x.review_date ? pill("review " + day(x.review_date)) : null),
      x.success_metric ? el("p", "sub", "Metric: " + x.success_metric) : null, x.result ? el("p", "sub", "Result: " + x.result) : null)));
    root.append(e);
    const k = card("Knowledge and constraints", "Tag a note \"constraint\" for hard limits, or \"partner-hypothesis\" for unvalidated partner claims.");
    k.append(Z.add(el("div", "row"), btn("Add note", "ghost small", async () => Z.formDialog("Add knowledge or constraint", [["title", "Title", "text", null, true], ["body", "Details", "text", null, true], ["tags", "Tags (comma separated, e.g. constraint)", "text"], ["source_url", "Source link", "text"]],
      b => post("/api/founder/businesses/" + SLUG + "/knowledge", b)))));
    if (bad(W.knowledge)) k.append(el("p", "err", "Could not load.")); else if (!W.knowledge.length) k.append(none("Nothing recorded yet"));
    else W.knowledge.forEach(x => k.append(Z.add(el("div", "item"), el("div", "t", x.title), x.tags ? Z.add(el("div", "meta"), ...x.tags.split(",").map(t => pill(t.trim() === "partner-hypothesis" ? "HYPOTHESIS, not validated" : t.trim(), ["constraint", "partner-hypothesis"].includes(t.trim()) ? "warn" : ""))) : null, el("p", "sub", x.body))));
    root.append(k);
  }

  Z.ws = { overview: (root, w, slug) => { W = w; SLUG = slug; overview(root); }, notes: (root, w, slug) => { W = w; SLUG = slug; notes(root); }, content: (root, w, slug) => { W = w; SLUG = slug; content(root); }, feedback: (root, w, slug) => { W = w; SLUG = slug; feedback(root); }, tile, secErr, day, none, post };

  Z.pages.buildflow = {
    title: "BuildFlow", sub: "Priority 1 · product, growth, content, feedback", icon: "plan",
    async render(root) {
      SLUG = "buildflow"; W = await Z.api("/api/founder/workspace/" + SLUG);
      const wrap = el("div", "list"), tabs = el("div", "tabs"); tabs.setAttribute("role", "tablist");
      TABS.forEach(([k, label]) => { const b = el("button", null, label); b.type = "button"; b.setAttribute("role", "tab"); b.setAttribute("aria-selected", String(k === tab)); b.onclick = () => { tab = k; Z.store.set("z2r_bf_tab", k); Z.rerender(); }; tabs.append(b); });
      wrap.append(tabs);
      ({ overview, content, feedback, pipeline, notes }[tab] || overview)(wrap);
      root.append(wrap);
    },
  };
})();
