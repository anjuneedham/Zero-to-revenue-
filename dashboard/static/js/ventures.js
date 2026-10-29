(function () {
  const { el, add, pill, btn, card, nice } = Z;
  const input = (ph, type) => { const i = el("input"); i.placeholder = ph || ""; if (type) i.type = type; i.setAttribute("aria-label", ph || "field"); return i; };
  const select = opts => { const s = el("select"); opts.forEach(([v, t]) => { const o = el("option", null, t); o.value = v; s.append(o); }); return s; };
  const field = (label, node) => { const l = el("label", "f", label); l.append(node); return l; };
  const PRI = { high: "gold", normal: "", low: "" };
  const post = async (path, body, msg, refresh) => { try { await Z.api(path, "POST", body); Z.toast(msg, "ok"); Z.$("drawer").close(); await refresh(); } catch (e) { Z.toast(e.message, "bad"); } };

  Z.pages.ventures = {
    title: "Ventures", sub: "Tasks, decisions and experiments for each venture", icon: "target",
    async render(root) {
      const d = await Z.api("/api/ventures");
      const refresh = () => Z.rerender();
      const g = el("div", "grid");

      const open = card("Decisions waiting on you", "Write the call you made so it is not re-argued next week.");
      open.classList.add("s12");
      const decisionRow = x => {
        const it = el("div", "item click"); add(it, add(el("div", "meta"), x.venture_id ? pill(nice(x.venture_id)) : pill("Whole OS")), el("div", "t", x.title), x.context ? el("div", "sub", x.context) : null);
        it.onclick = () => {
          const f = el("div", "form"), t = el("textarea"); t.rows = 4; t.placeholder = "What did you decide, and why?";
          add(f, el("p", "sub", x.title), t,
            btn("Mark decided", "gold small", () => post("/api/ventures/decision/decide", { id: x.id, decision: t.value, status: "decided" }, "Decision recorded", refresh)));
          Z.openDrawer("Decide", f);
        };
        return it;
      };
      const dl = el("div", "list");
      const allOpen = [...d.shared_decisions, ...d.ventures.flatMap(v => v.decisions)];
      if (!allOpen.length) dl.append(Z.empty("No open decisions", "Add one when you are stuck choosing between two things."));
      allOpen.forEach(x => dl.append(decisionRow(x)));
      add(open, dl, btn("Add a decision", "ghost small", async () => {
        const f = el("div", "form"), v = select([["", "Whole OS"], ...d.ventures.map(x => [x.id, x.name])]), t = input("The decision to make"), c = input("Context (optional)");
        add(f, field("Applies to", v), t, c, btn("Add", "gold small", () => post("/api/ventures/decision", { venture_id: v.value, title: t.value, context: c.value }, "Decision added", refresh)));
        Z.openDrawer("Add a decision", f);
      }));
      g.append(open);

      d.ventures.forEach(v => {
        const c = card(v.name, (v.plan_day ? "Rhythm: " + v.plan_day + (v.plan_day.split(", ").includes(d.weekday) ? " · today" : "") : "") + (v.status !== "active" ? " · " + v.status : ""));
        c.classList.add("s6");
        c.append(el("h3", null, "Tasks"));
        if (!v.tasks.length) c.append(el("p", "sub", "No open tasks."));
        v.tasks.forEach(t => {
          const row = el("div", "row"), st = select([["todo", "To do"], ["doing", "Doing"], ["blocked", "Blocked"], ["done", "Done"]]); st.value = t.status;
          st.onchange = async () => { try { await Z.api("/api/ventures/task/status", "POST", { id: t.id, status: st.value }); Z.toast("Saved", "ok"); await refresh(); } catch (e) { Z.toast(e.message, "bad"); } };
          add(row, el("b", null, t.title), t.priority === "high" ? pill("High", "gold") : null, t.due_date ? pill("Due " + t.due_date) : null, st); c.append(row);
        });
        c.append(btn("Add task", "gold small", async () => {
          const f = el("div", "form"), t = input("Task"), p = select([["normal", "Normal"], ["high", "High"], ["low", "Low"]]), due = input("Due", "date");
          add(f, t, field("Priority", p), field("Due (optional)", due), btn("Add", "gold small", () => post("/api/ventures/task", { venture_id: v.id, title: t.value, priority: p.value, due_date: due.value }, "Task added", refresh)));
          Z.openDrawer("Add a task to " + v.name, f);
        }));
        c.append(el("h3", null, "Experiments running"));
        if (!v.experiments.length) c.append(el("p", "sub", "None. Test one thing at a time and say how you will judge it."));
        v.experiments.forEach(x => {
          const it = el("div", "item click"); add(it, el("div", "t", x.hypothesis), el("div", "sub", "Judged by: " + x.metric));
          it.onclick = () => {
            const f = el("div", "form"), r = select([["won", "Worked"], ["lost", "Did not work"], ["inconclusive", "Inconclusive"], ["stopped", "Stopped"]]), t = el("textarea"); t.rows = 3; t.placeholder = "What did you count? Real numbers only.";
            add(f, el("p", "sub", x.hypothesis), field("Outcome", r), t, btn("Close experiment", "gold small", () => post("/api/ventures/experiment/close", { id: x.id, status: r.value, result: t.value }, "Experiment closed", refresh)));
            Z.openDrawer("Close experiment", f);
          };
          c.append(it);
        });
        c.append(btn("Start an experiment", "ghost small", async () => {
          const f = el("div", "form"), h = input("We believe that... (one change)"), m = input("We will count... (e.g. replies per 20 messages)");
          add(f, h, m, btn("Start", "gold small", () => post("/api/ventures/experiment", { venture_id: v.id, hypothesis: h.value, metric: m.value }, "Experiment started", refresh)));
          Z.openDrawer("New experiment for " + v.name, f);
        }));
        g.append(c);
      });

      if (d.recent_decisions.length) {
        const rc = card("Recent decisions", "What you already settled."); rc.classList.add("s12");
        d.recent_decisions.forEach(x => rc.append(add(el("div", "item"), add(el("div", "meta"), pill(x.venture_id ? nice(x.venture_id) : "Whole OS"), pill(nice(x.status))), el("div", "t", x.title), el("div", "sub", x.decision || ""))));
        g.append(rc);
      }
      root.append(g);
    },
  };
})();
