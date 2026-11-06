// Sales execution: shared helpers, Today (command centre), Pipeline, Prospect. All DOM via createElement/textContent.
(function () {
  const { el, add, text, pill, btn, card, fmt } = Z;
  const S = (window.Sales = { meta: null });
  let uid = 0;

  S.load = async () => { if (!S.meta) S.meta = await Z.api("/api/sales/meta"); return S.meta; };
  S.api = (path, body) => Z.api("/api/sales/" + path, body === undefined ? "GET" : "POST", body === undefined ? undefined : body);
  S.label = id => { const m = S.meta || {}; const all = [].concat(m.stages || [], m.closed || [], m.parked || []); const f = all.find(s => s.id === id); return f ? f.label : Z.nice(id); };
  S.stageKind = id => (id === "won" ? "ok" : ["lost", "not_interested", "not_qualified", "no_response", "unreachable"].includes(id) ? "bad" : ["future_opportunity", "follow_up_later"].includes(id) ? "warn" : ["meeting_booked", "proposal", "negotiation"].includes(id) ? "gold" : "");
  S.who = p => p.business || p.name || "Unnamed prospect";
  S.money = (v, cur) => (v == null ? "" : (cur || "USD") + " " + Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }));
  S.go = hash => { location.hash = hash; };
  S.day = d => { try { return new Date(d + "T12:00:00").toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" }); } catch (e) { return d || ""; } };
  const isoPlus = n => { const d = new Date(); d.setDate(d.getDate() + n); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); };
  S.isoPlus = isoPlus;

  // ---- form builder: fields -> <form>. Validates required fields, shows the server's message inline. ----
  S.form = (fields, submitLabel, onSubmit, cancel) => {
    const f = el("form", "sform"); f.noValidate = true; const ins = {}; const id = ++uid;
    fields.forEach(d => {
      let inp;
      if (d.type === "textarea") { inp = el("textarea"); inp.rows = d.rows || 3; }
      else if (d.type === "select") { inp = el("select"); (d.options || []).forEach(([v, l]) => { const o = el("option", null, l); o.value = v; inp.append(o); }); }
      else { inp = el("input"); inp.type = d.type || "text"; if (d.type === "number") { inp.min = 0; inp.step = "any"; inp.inputMode = "decimal"; } }
      inp.name = d.name; inp.id = `f${id}_${d.name}`; if (d.placeholder) inp.placeholder = d.placeholder;
      if (d.type === "checkbox") inp.checked = !!d.value; else if (d.value != null) inp.value = d.value;
      if (d.required) inp.setAttribute("aria-required", "true");
      const lab = el("label", "f" + (d.wide || d.type === "textarea" ? " wide" : "")); lab.append(el("span", null, d.label + (d.required ? " *" : "")), inp);
      if (d.hint) lab.append(el("small", "hint", d.hint));
      ins[d.name] = inp; f.append(lab);
    });
    const err = el("p", "err wide"); err.setAttribute("role", "alert");
    const row = el("div", "row wide"); const go = el("button", "btn gold", submitLabel); go.type = "submit"; row.append(go);
    if (cancel) { const c = el("button", "btn ghost", "Cancel"); c.type = "button"; c.onclick = cancel; row.append(c); }
    f.append(err, row);
    f.onsubmit = async e => {
      e.preventDefault(); text(err, "");
      const vals = {};
      for (const d of fields) {
        const i = ins[d.name]; i.removeAttribute("aria-invalid");
        const v = d.type === "checkbox" ? i.checked : i.value.trim();
        if (d.required && !v) { i.setAttribute("aria-invalid", "true"); text(err, d.label + " is required."); i.focus(); return; }
        vals[d.name] = v;
      }
      go.disabled = true; const label = go.textContent; go.textContent = "Saving…";
      try { await onSubmit(vals); } catch (x) { if (x.message !== "Signed out") text(err, x.message); } finally { go.disabled = false; go.textContent = label; }
    };
    return f;
  };
  const opts = (arr, blank) => (blank ? [["", blank]] : []).concat(arr.map(x => (Array.isArray(x) ? x : [x, Z.nice(x)])));

  // ---- one activity event as a list item (used by prospect timeline, Today, and Insights) ----
  const KIND_PILL = { deal_won: "ok", deal_lost: "bad", response_received: "gold", message_sent: "royal", meeting_booked: "gold", proposal_delivered: "gold", outcome_recorded: "warn" };
  S.eventItem = (e, showWho) => {
    const it = el("div", "item ev"); const d = e.detail || {};
    const head = el("div", "row");
    add(head, pill(Z.nice(e.kind), KIND_PILL[e.kind] || ""), el("span", "t", e.summary));
    it.append(head);
    const meta = el("div", "sub"); let when = "Happened " + fmt.when(e.occurred_at);
    if (Math.abs(new Date(e.at) - new Date(e.occurred_at)) > 36e5 * 24) when += " (recorded " + fmt.when(e.at) + ")";
    text(meta, when + (showWho && (e.business || e.name) ? " · " + (e.business || e.name) : "") + (d.stage_after && e.lead_id ? " · stage: " + S.label(d.stage_after) : "")); it.append(meta);
    const body = d.text || d.notes || d.reasons || d.reason || d.note;
    if (body) it.append(el("p", "evbody", body));
    if (d.changes) it.append(el("p", "evbody", Object.entries(d.changes).map(([k, v]) => v.changed ? k + ": changed" : k + ": " + (v.from == null ? "(empty)" : v.from) + " → " + (v.to == null ? "(empty)" : v.to)).join("; ")));
    if (d.channel || d.angle) it.append(el("div", "sub", [d.channel && "Channel: " + d.channel, d.angle && "Approach: " + d.angle].filter(Boolean).join(" · ")));
    if (d.next_recommended) it.append(el("div", "sub", "Next recommended: " + d.next_recommended));
    return it;
  };

  const addForm = () => {
    const c = card("Add a prospect", "Only a business or contact name is needed. Add the rest later.");
    c.append(S.form([
      { name: "business", label: "Business name", placeholder: "e.g. Smith Roofing" },
      { name: "name", label: "…or contact name", placeholder: "if there is no business name yet" },
      { name: "industry", label: "Type of business", placeholder: "optional" },
      { name: "source_channel", label: "Where did you find them?", placeholder: "referral, Instagram, walk-in…" }],
      "Add prospect", async v => {
        if (!v.business && !v.name) throw new Error("Enter a business name or a contact name.");
        const r = await S.api("prospects", v); Z.toast("Added " + S.who(r.prospect), "ok"); S.go("prospect/" + r.prospect.id);
      }));
    return c;
  };

  // ================================================================ TODAY ===========================================
  Z.pages.today = {
    title: "Today", sub: "What to do, who to contact, and what happened", icon: "today",
    async render(root) {
      await S.load();
      const t = await S.api("today");
      const g = el("div", "grid");

      const head = card("Today · " + S.day(t.date), "Timezone: " + t.timezone + ". Progress counts what happened today, including backdated entries only on their real date.");
      head.classList.add("s8");
      const list = el("div", "list");
      if (!t.targets.length) list.append(Z.empty("No daily targets set", "Set them below."));
      t.targets.forEach(x => {
        const row = el("div", "target" + (x.met ? " met" : ""));
        const bar = el("div", "bar" + (x.met ? "" : " gold")); const fill = el("i"); fill.style.width = Math.min(100, Math.round(100 * x.done / Math.max(1, x.target))) + "%"; bar.append(fill);
        add(row, el("span", "tcheck", x.met ? "✓" : "○"), el("div", null, x.label), el("b", null, x.done + " / " + x.target), bar);
        row.setAttribute("role", "group"); row.setAttribute("aria-label", `${x.label}: ${x.done} of ${x.target}${x.met ? ", done" : ""}`);
        list.append(row);
      });
      const rv = el("div", "target" + (t.review_done ? " met" : ""));
      add(rv, el("span", "tcheck", t.review_done ? "✓" : "○"), el("div", null, "Review today's performance"));
      if (!t.review_done) rv.append(btn("Complete review", "small ghost", async () => { await S.api("review", {}); Z.toast("Review recorded", "ok"); await Z.rerender(); }));
      list.append(rv);
      head.append(list); g.append(head);

      const rec = card("Recommended next actions", "Rule-based suggestions from your recorded activity. Not AI."); rec.classList.add("s4");
      const rl = el("div", "list");
      if (!t.recommendations.length) rl.append(Z.empty("Nothing pressing", "Targets are met and nothing is overdue."));
      t.recommendations.forEach(r => rl.append(add(el("div", "item"), el("div", "t", r.text), el("div", "sub", "Why: " + r.why))));
      rec.append(rl); g.append(rec);

      const fu = card("Follow-ups due", "Due today or overdue"); fu.classList.add("s6");
      const fl = el("div", "list");
      if (!t.followups_due.length) fl.append(Z.empty("No follow-ups due", "When you record a message, schedule the next follow-up so nothing slips."));
      t.followups_due.forEach(k => fl.append(S.taskItem(k)));
      fu.append(fl); g.append(fu);

      const tk = card("Tasks", "Playbook steps and other tasks due"); tk.classList.add("s6");
      const tl = el("div", "list");
      if (!t.tasks.length) tl.append(Z.empty("No tasks due", "Start a playbook on a prospect and its next step shows up here."));
      t.tasks.forEach(k => tl.append(S.taskItem(k)));
      tk.append(tl); g.append(tk);

      const at = card("Needs attention", "Prospects where a recorded fact suggests an action"); at.classList.add("s6");
      const al = el("div", "list");
      if (!t.attention.length) al.append(Z.empty("Nobody needs attention", "Nothing stuck right now."));
      t.attention.forEach(a => { const it = el("div", "item click"); it.tabIndex = 0; it.setAttribute("role", "link");
        add(it, el("div", "t", a.business), el("div", "sub", a.reason), pill(a.suggestion, "warn")); const open = () => S.go("prospect/" + a.lead_id);
        it.onclick = open; it.onkeydown = e => { if (e.key === "Enter") open(); }; al.append(it); });
      at.append(al); g.append(at);

      const op = card("Active opportunities", "Responded or further"); op.classList.add("s6");
      const ol = el("div", "list");
      if (!t.active_opportunities.length) ol.append(Z.empty("No active opportunities yet", "A prospect appears here once they respond."));
      t.active_opportunities.forEach(p => { const it = el("div", "item click"); it.tabIndex = 0; it.setAttribute("role", "link");
        add(it, el("div", "t", S.who(p)), add(el("div", "meta"), pill(S.label(p.stage), S.stageKind(p.stage)), p.deal_value ? pill(S.money(p.deal_value, p.currency) + " (estimate)") : null));
        const open = () => S.go("prospect/" + p.id); it.onclick = open; it.onkeydown = e => { if (e.key === "Enter") open(); }; ol.append(it); });
      op.append(ol); g.append(op);

      const mt = card("Meetings", "Next 7 days"); mt.classList.add("s4");
      const ml = el("div", "list");
      if (!t.meetings.length) ml.append(Z.empty("No meetings booked"));
      t.meetings.forEach(k => ml.append(S.taskItem(k)));
      mt.append(ml); g.append(mt);

      const pipe = card("Pipeline", t.pipeline.total + " prospect(s). Values are your estimates, not revenue."); pipe.classList.add("s8");
      const chips = el("div", "chips");
      S.meta.stages.forEach(s => { const n = t.pipeline.by_stage[s.id] || 0; const b = el("button", null, s.label + " (" + n + ")"); b.type = "button"; b.onclick = () => S.go("pipeline"); chips.append(b); });
      pipe.append(chips);
      const vals = Object.entries(t.pipeline.open_value); if (vals.length) pipe.append(el("p", "sub", "Open pipeline value (estimates): " + vals.map(([c, v]) => S.money(v, c)).join(" · ")));
      g.append(pipe);

      g.append(Object.assign(addForm(), { className: "card s6" }));
      g.append(S.targetsCard(t));

      const ra = card("Recent activity", "Latest recorded events"); ra.classList.add("s12");
      const rl2 = el("div", "list");
      if (!t.recent_activity.length) rl2.append(Z.empty("Nothing recorded yet", "Everything you do in the pipeline is logged here."));
      t.recent_activity.forEach(e => rl2.append(S.eventItem(e, true)));
      ra.append(rl2); g.append(ra);
      root.append(g);
    },
  };

  S.taskItem = k => {
    const it = el("div", "item");
    const head = el("div", "row"); add(head, pill(k.priority === 1 ? "high" : k.priority === 3 ? "low" : "normal", k.priority === 1 ? "bad" : ""), el("span", "t", k.title));
    it.append(head);
    const bits = [k.lead_business || k.lead_name, "due " + S.day(k.due_date), k.overdue_days > 0 ? k.overdue_days + " day(s) overdue" : null, k.playbook_name ? "playbook: " + k.playbook_name : null].filter(Boolean);
    it.append(el("div", "sub", bits.join(" · ")));
    if (k.detail) it.append(el("p", "evbody", k.detail));
    const row = el("div", "row");
    if (k.lead_id) { const a = el("a", "btn small ghost", "Open prospect"); a.href = "#prospect/" + k.lead_id; row.append(a); }
    row.append(btn("Done", "small", async () => { await S.api(`tasks/${k.id}/complete`, {}); Z.toast("Done", "ok"); await Z.rerender(); }, "check"),
      btn("Skip", "small ghost", async () => { await S.api(`tasks/${k.id}/skip`, {}); await Z.rerender(); }));
    it.append(row); return it;
  };

  S.targetsCard = t => {
    const c = card("Daily targets", "Change what a good day looks like. 0 turns a target off."); c.classList.add("s6");
    const fields = (S.meta.targets || []).map(x => ({ name: x.id, label: x.label, type: "number", value: x.target }));
    fields.push({ name: "timezone", label: "Your timezone", value: t.timezone, hint: "Decides what 'today' means, e.g. America/Jamaica" });
    c.append(S.form(fields, "Save targets", async v => {
      const targets = {}; (S.meta.targets || []).forEach(x => { targets[x.id] = parseInt(v[x.id], 10); if (isNaN(targets[x.id])) throw new Error(x.label + " must be a whole number."); });
      await S.api("targets", { targets, timezone: v.timezone }); S.meta = null; Z.toast("Targets saved", "ok"); await Z.rerender();
    }));
    return c;
  };

  // ================================================================ PIPELINE ========================================
  Z.pages.pipeline = {
    title: "Pipeline", sub: "Every prospect, by stage", icon: "pipeline",
    async render(root) {
      await S.load();
      const { prospects } = await S.api("prospects");
      let filter = "active", q = "";
      const g = el("div", "grid");
      g.append(Object.assign(addForm(), { className: "card s12" }));
      const list = card("Prospects", prospects.length + " total"); list.classList.add("s12");
      const search = el("input"); search.type = "search"; search.placeholder = "Search by name"; search.setAttribute("aria-label", "Search prospects");
      const chips = el("div", "chips"); const body = el("div", "list");
      const groups = [["active", "Active"]].concat(S.meta.stages.map(s => [s.id, s.label]), [["parked", "Parked"], ["closed", "Closed"]]);
      const match = (p, k) => k === "active" ? p.stage in RANKS : k === "parked" ? S.meta.parked.some(s => s.id === p.stage) : k === "closed" ? S.meta.closed.some(s => s.id === p.stage) : p.stage === k;
      const RANKS = Object.fromEntries(S.meta.stages.map(s => [s.id, 1]));
      const draw = () => {
        chips.replaceChildren(...groups.map(([k, l]) => { const n = prospects.filter(p => match(p, k)).length; const b = el("button", null, l + " (" + n + ")"); b.type = "button"; b.setAttribute("aria-pressed", filter === k); b.onclick = () => { filter = k; draw(); }; return b; }));
        const rows = prospects.filter(p => match(p, filter) && (!q || S.who(p).toLowerCase().includes(q)));
        body.replaceChildren();
        if (!rows.length) body.append(Z.empty(prospects.length ? "Nothing in this view" : "No prospects yet", prospects.length ? "Try another stage." : "Add your first prospect above. Only a name is needed."));
        rows.forEach(p => {
          const it = el("div", "item click"); it.tabIndex = 0; it.setAttribute("role", "link");
          const meta = el("div", "meta"); add(meta, pill(S.label(p.stage), S.stageKind(p.stage)), p.qualification !== "unqualified" ? pill(Z.nice(p.qualification), p.qualification === "qualified" ? "ok" : "") : null,
            p.industry ? pill(p.industry) : null, p.deal_value ? pill(S.money(p.deal_value, p.currency) + " est.") : null, p.next_followup_at ? pill("follow-up " + S.day(p.next_followup_at), p.next_followup_at < S.isoPlus(0) ? "bad" : "") : null);
          add(it, el("div", "t", S.who(p)), meta);
          const open = () => S.go("prospect/" + p.id); it.onclick = open; it.onkeydown = e => { if (e.key === "Enter") open(); };
          body.append(it);
        });
      };
      search.oninput = () => { q = search.value.trim().toLowerCase(); draw(); };
      add(list, search, chips, body); draw(); g.append(list); root.append(g);
    },
  };

  // ================================================================ PROSPECT ========================================
  Z.pages.prospect = {
    title: "Prospect", sub: "", icon: "pipeline", navKey: "pipeline",
    async render(root, id) {
      await S.load();
      let v;
      try { v = await S.api("prospects/" + encodeURIComponent(id || "")); } catch (e) {
        const c = card("Prospect not found", "It may have been deleted. Its history is kept."); c.append(Z.btn("Back to pipeline", "gold", async () => S.go("pipeline"))); root.append(c); return;
      }
      const p = v.prospect;
      text(Z.$("page-title"), S.who(p)); text(Z.$("page-sub"), S.label(p.stage));
      document.title = S.who(p) + " · Zero-to-Revenue";
      const g = el("div", "grid");

      const top = card(S.who(p), [p.industry, p.location].filter(Boolean).join(" · ") || "Add details below"); top.classList.add("s12");
      const meta = el("div", "meta");
      add(meta, pill(S.label(p.stage), S.stageKind(p.stage)), pill("Qualification: " + Z.nice(p.qualification), p.qualification === "qualified" ? "ok" : ""),
        p.deal_value ? pill("Deal value: " + S.money(p.deal_value, p.currency) + " (estimate)") : null,
        p.revenue_won != null ? pill("Won: " + S.money(p.revenue_won, p.currency) + " (owner-recorded, not verified)", "ok") : null,
        p.last_contact_at ? pill("Last contact " + fmt.ago(p.last_contact_at)) : null,
        p.next_followup_at ? pill("Next follow-up " + S.day(p.next_followup_at), p.next_followup_at < S.isoPlus(0) ? "bad" : "gold") : null);
      top.append(meta);
      const cur = v.tasks[0];
      top.append(el("p", "sub", cur ? "Current task: " + cur.title + " (due " + S.day(cur.due_date) + ")" : "No open task. Record what happens next below."));
      const panel = el("div", "panelhold");
      const show = (title, form) => { const c = card(title); c.append(form); panel.replaceChildren(c); c.scrollIntoView({ block: "nearest", behavior: "smooth" }); form.querySelector("input,textarea,select") && form.querySelector("input,textarea,select").focus({ preventScroll: true }); };
      const done = msg => async () => { Z.toast(msg, "ok"); await Z.rerender(); };
      const A = (label, title, fields, path, submit, extra) => { const b = el("button", "btn small ghost", label); b.type = "button";
        b.onclick = () => show(title, S.form(fields, submit || "Save", async x => { await S.api(`prospects/${p.id}/${path}`, extra ? extra(x) : x); await done("Saved")(); }, () => panel.replaceChildren())); return b; };
      const when = { name: "occurred_at", label: "When did this happen?", type: "date", hint: "Leave blank for now. Pick a past date to back-fill." };
      const ch = (req) => ({ name: "channel", label: "Channel", type: "select", options: opts(S.meta.channels, req ? "Choose…" : "Not stated"), required: !!req });
      const bar = el("div", "row actionbar");
      add(bar,
        A("Log research", "Research completed", [{ name: "notes", label: "What did you find?", type: "textarea", required: true, value: p.research_notes || "" }, when], "research"),
        A("Qualify", "Qualification decision", [{ name: "decision", label: "Decision", type: "select", required: true, options: [["", "Choose…"], ["qualified", "Qualified"], ["maybe", "Maybe"], ["not_qualified", "Not qualified (closes this prospect)"]] }, { name: "reasons", label: "Why?", type: "textarea" }, when], "qualify"),
        A("Prepare message", "Message prepared", [ch(true), { name: "angle", label: "Approach label", placeholder: "short name so results can be compared" }, { name: "text", label: "Message", type: "textarea", rows: 5 }, when], "prepare"),
        A("Log message sent", "Record a message you sent", [ch(true), { name: "angle", label: "Approach label", placeholder: "e.g. quote-page idea" }, { name: "text", label: "What you sent", type: "textarea", rows: 5 },
          { name: "followup_in_days", label: "Follow up in (days)", type: "number", value: 3, hint: "Creates a follow-up task. 0 for none." }, when], "outreach", "Record sent",
          x => ({ ...x, followup_in_days: parseInt(x.followup_in_days, 10) || 0 })),
        A("Log response", "Record a response", [{ name: "sentiment", label: "How did it read?", type: "select", options: [["positive", "Positive"], ["neutral", "Neutral"], ["negative", "Negative"]] }, ch(false), { name: "text", label: "What they said", type: "textarea" }, when], "response"),
        A("Schedule follow-up", "Schedule a follow-up", [{ name: "due_date", label: "Due date", type: "date", required: true, value: S.isoPlus(3) }, { name: "priority", label: "Priority", type: "select", options: [["normal", "Normal"], ["high", "High"], ["low", "Low"]] }, { name: "note", label: "Note", type: "textarea", rows: 2 }], "followup"),
        A("Meeting", "Record a meeting", [{ name: "when", label: "Meeting date", type: "date", required: true, value: S.isoPlus(1) }, { name: "held", label: "Status", type: "select", options: [["", "Booked (upcoming)"], ["1", "Already held"]] }, { name: "notes", label: "Notes", type: "textarea" }], "meeting", "Save", x => ({ ...x, held: x.held === "1" })),
        A("Proposal", "Record a proposal", [{ name: "value", label: "Proposal value (" + p.currency + ")", type: "number" }, { name: "notes", label: "Notes", type: "textarea", rows: 2 }, when], "proposal"),
        A("Add note", "Add a note", [{ name: "text", label: "Note", type: "textarea", required: true }], "note"),
        A("Move stage", "Move to a stage", [{ name: "to", label: "New stage", type: "select", required: true, options: [["", "Choose…"]].concat(S.meta.stages.map(s => [s.id, s.label])), value: "" }, { name: "note", label: "Why?", type: "textarea", rows: 2 }], "stage"),
        A("Win / lose / park", "Record an outcome", [{ name: "outcome", label: "Outcome", type: "select", required: true, options: [["", "Choose…"], ["won", "Customer won"], ["lost", "Lost"], ["not_interested", "Not interested"], ["not_qualified", "Not qualified"], ["no_response", "No response"], ["unreachable", "Unreachable"], ["future_opportunity", "Future opportunity"], ["follow_up_later", "Follow up later (needs a date)"]] },
          { name: "reason", label: "Reason", type: "textarea", rows: 2 }, { name: "revenue", label: "Revenue (" + p.currency + ", if won)", type: "number", hint: "Owner-recorded. It counts as verified revenue only after Treasury verifies the payment." }, { name: "resume_date", label: "Follow-up date (if parking)", type: "date" }, when], "close"));
      top.append(bar, panel); g.append(top);

      // playbook run
      const pb = card("Playbook", v.active_run ? v.active_run.playbook_name + " · " + v.active_run.done_count + " of " + v.active_run.steps.length + " steps" : "Assign a playbook to get step-by-step instructions");
      pb.classList.add("s6");
      if (v.active_run) pb.append(await S.runView(v.active_run)); else {
        const { playbooks } = await S.api("playbooks"); const live = playbooks.filter(x => !x.archived);
        pb.append(S.form([{ name: "playbook_id", label: "Playbook", type: "select", required: true, options: [["", "Choose…"]].concat(live.map(x => [x.id, x.name])) }], "Start playbook",
          async x => { await S.api(`prospects/${p.id}/playbook`, x); await done("Playbook started")(); }));
        const past = v.runs.filter(r => r.status !== "in_progress");
        if (past.length) pb.append(el("p", "sub", "Previous: " + past.map(r => `${r.playbook_name} (${r.status}, ${r.done_count}/${r.steps.length})`).join("; ")));
      }
      g.append(pb);

      // details
      const dt = card("Details", "Edit anything. Changes are logged; old values stay in the history."); dt.classList.add("s6");
      const fld = (name, label, extra) => Object.assign({ name, label, value: p[name] == null ? "" : p[name] }, extra || {});
      dt.append(S.form([fld("business", "Business name"), fld("name", "Contact name"), fld("email", "Email", { type: "email" }), fld("phone", "Phone"), fld("contact_other", "Other contact (WhatsApp, handle…)"),
        fld("website", "Website"), fld("industry", "Industry"), fld("location", "Location"), fld("source_channel", "Source"), fld("offer", "Offer"),
        fld("deal_value", "Potential deal value", { type: "number" }), fld("currency", "Currency"), fld("research_notes", "Research notes", { type: "textarea", rows: 4 }), fld("notes", "Notes", { type: "textarea", rows: 3 })],
        "Save details", async x => { await S.api(`prospects/${p.id}/update`, x); await done("Details saved")(); }));
      g.append(dt);

      // tasks
      const tk = card("Open tasks"); tk.classList.add("s12");
      const tl = el("div", "list"); if (!v.tasks.length) tl.append(Z.empty("No open tasks")); v.tasks.forEach(k => tl.append(S.taskItem(k))); tk.append(tl); g.append(tk);

      // timeline + playback
      g.append(S.playback(v.timeline));
      const tlc = card("Timeline", "Every recorded event in order. Earlier entries are never edited."); tlc.classList.add("s12");
      const evl = el("div", "list"); if (!v.timeline.length) evl.append(Z.empty("No events yet"));
      v.timeline.forEach(e => evl.append(S.eventItem(e, false)));
      tlc.append(evl); g.append(tlc);

      const danger = card("Remove prospect", "Deletes the record and open tasks. The activity history is kept."); danger.classList.add("s12");
      danger.append(Z.btn("Delete prospect", "red small", async () => {
        if (!confirm("Delete " + S.who(p) + "? The activity history is kept, the record is not.")) return;
        await S.api(`prospects/${p.id}/delete`, {}); Z.toast("Deleted", "ok"); S.go("pipeline");
      }));
      g.append(danger);
      root.append(g);
    },
  };

  // ---- playbook run: checkable steps with notes; progress is saved on every tick ----
  S.runView = async run => {
    const box = el("div", "list");
    run.steps.forEach((s, i) => {
      const doneAt = run.progress[s.id]; const row = el("div", "check" + (doneAt ? " done" : "")); const cb = el("input"); cb.type = "checkbox"; cb.checked = !!doneAt; cb.setAttribute("aria-label", "Step " + (i + 1) + ": " + s.title);
      const note = el("input"); note.type = "text"; note.placeholder = "Optional note"; note.value = (doneAt && doneAt.note) || ""; note.setAttribute("aria-label", "Note for " + s.title);
      const mid = el("div"); add(mid, el("b", null, (i + 1) + ". " + s.title), el("p", null, s.instruction), note);
      cb.onchange = async () => { cb.disabled = true; try { await S.api(`runs/${run.id}/step`, { step_id: s.id, done: cb.checked, note: note.value }); await Z.rerender(); } catch (e) { Z.toast(e.message, "bad"); cb.checked = !cb.checked; cb.disabled = false; } };
      add(row, cb, mid); box.append(row);
    });
    box.append(Z.btn("Abandon this run", "ghost small", async () => { if (!confirm("Abandon this playbook run? Progress is kept in the history.")) return; await S.api(`runs/${run.id}/abandon`, {}); await Z.rerender(); }));
    const pbd = await S.api("playbooks/" + run.playbook_id).catch(() => null);
    if (pbd) box.append(S.guide(pbd.playbook));
    return box;
  };
  S.guide = pb => {
    const d = el("details", "guide"); d.append(el("summary", null, "Playbook guide: examples and common mistakes"));
    const sec = (t, arr) => { if (arr && arr.length) { d.append(el("h3", "gh", t)); const ul = el("ul", "plain"); arr.forEach(x => ul.append(el("li", null, x))); d.append(ul); } };
    if (pb.objective) d.append(el("p", null, "Objective: " + pb.objective));
    sec("Example messages (adapt them, they are not facts about you)", pb.example_messages); sec("Recommended actions", pb.recommended_actions); sec("Common mistakes", pb.common_mistakes);
    if (pb.completion_criteria) d.append(el("p", "sub", "Done when: " + pb.completion_criteria));
    if (pb.next_recommended) d.append(el("p", "sub", "Next: " + pb.next_recommended));
    return d;
  };

  // ---- playback: step through recorded events; shows the stage at each moment. Not a video or screen replay. ----
  S.playback = events => {
    const c = card("Playback", "Step through the recorded events in order. This is a review of your records, not a video."); c.classList.add("s12");
    if (events.length < 2) { c.append(Z.empty("Not enough history yet", "Playback needs at least two events.")); return c; }
    let i = 0, timer = null;
    const track = el("div", "stagetrack"); const view = el("div", "list"); const label = el("div", "label");
    const slider = el("input"); slider.type = "range"; slider.min = 0; slider.max = events.length - 1; slider.value = 0; slider.setAttribute("aria-label", "Event position");
    const stages = S.meta.stages.map(s => s.id);
    const draw = () => {
      const e = events[i], st = (e.detail && e.detail.stage_after) || ""; slider.value = i;
      text(label, `Event ${i + 1} of ${events.length}`);
      track.replaceChildren(...stages.map(s => { const sp = el("span", "stg" + (s === st ? " now" : stages.indexOf(s) < stages.indexOf(st) ? " past" : ""), S.label(s)); if (s === st) sp.setAttribute("aria-current", "step"); return sp; }));
      if (st && !stages.includes(st)) track.append(el("span", "stg now", S.label(st)));
      view.replaceChildren(S.eventItem(e, false));
    };
    const stop = () => { clearInterval(timer); timer = null; play.textContent = "Play"; };
    const play = el("button", "btn small", "Play"); play.type = "button";
    play.onclick = () => { if (timer) return stop(); if (i >= events.length - 1) i = 0; draw(); play.textContent = "Pause"; timer = setInterval(() => { if (i >= events.length - 1) return stop(); i++; draw(); }, 1400); };
    const prev = el("button", "btn small ghost", "Previous"); prev.type = "button"; prev.onclick = () => { stop(); i = Math.max(0, i - 1); draw(); };
    const next = el("button", "btn small ghost", "Next"); next.type = "button"; next.onclick = () => { stop(); i = Math.min(events.length - 1, i + 1); draw(); };
    slider.oninput = () => { stop(); i = parseInt(slider.value, 10); draw(); };
    add(c, track, add(el("div", "row"), prev, play, next, label), slider, view); draw(); return c;
  };
})();
