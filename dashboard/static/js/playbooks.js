// Playbooks: list, create, edit (steps can be added/removed/reordered), duplicate, archive, start, review past runs.
(function () {
  const { el, add, text, pill, btn, card, fmt } = Z;
  const S = window.Sales;
  const lines = v => (v || []).join("\n");
  const unlines = s => s.split("\n").map(x => x.trim()).filter(Boolean);

  Z.pages.playbooks = {
    title: "Playbooks", sub: "Repeatable processes you can edit", icon: "book",
    async render(root) {
      await S.load();
      const { playbooks } = await S.api("playbooks");
      const g = el("div", "grid");
      const mk = card("New playbook", "Start from scratch, or duplicate one below and change it."); mk.classList.add("s12");
      mk.append(S.form([{ name: "name", label: "Name", required: true, placeholder: "e.g. Roofers: initial outreach" }, { name: "objective", label: "Objective", type: "textarea", rows: 2 }], "Create playbook",
        async v => { const r = await S.api("playbooks", v); S.go("playbook/" + r.playbook.id); }));
      g.append(mk);
      const live = playbooks.filter(p => !p.archived), old = playbooks.filter(p => p.archived);
      const lc = card("Your playbooks", live.length + " active · every one is editable"); lc.classList.add("s12");
      const l = el("div", "list");
      live.forEach(p => {
        const it = el("div", "item click"); it.tabIndex = 0; it.setAttribute("role", "link");
        add(it, el("div", "t", p.name), el("div", "sub", p.objective), add(el("div", "meta"), pill(p.steps.length + " steps"), pill(p.runs + " run(s), " + p.runs_completed + " completed"), pill("v" + p.version), p.builtin_slug ? pill("built-in") : pill("custom", "gold")));
        const open = () => S.go("playbook/" + p.id); it.onclick = open; it.onkeydown = e => { if (e.key === "Enter") open(); }; l.append(it);
      });
      lc.append(l); g.append(lc);
      if (old.length) { const ac = card("Archived"); ac.classList.add("s12"); old.forEach(p => { const row = el("div", "row"); row.append(el("span", null, p.name), btn("Restore", "small ghost", async () => { await S.api(`playbooks/${p.id}/unarchive`, {}); await Z.rerender(); })); ac.append(row); }); g.append(ac); }
      root.append(g);
    },
  };

  Z.pages.playbook = {
    title: "Playbook", sub: "", icon: "book", navKey: "playbooks",
    async render(root, id) {
      await S.load();
      let pb;
      try { pb = (await S.api("playbooks/" + encodeURIComponent(id || ""))).playbook; } catch (e) { const c = card("Playbook not found"); c.append(Z.btn("Back", "gold", async () => S.go("playbooks"))); root.append(c); return; }
      text(Z.$("page-title"), pb.name); text(Z.$("page-sub"), "Version " + pb.version + (pb.archived ? " · archived" : ""));
      const g = el("div", "grid");
      const ed = card("Edit playbook", "Saving creates a new version. Past runs keep the steps they started with."); ed.classList.add("s12");
      let steps = pb.steps.map(s => ({ ...s }));
      const stepBox = el("div", "list");
      const drawSteps = () => {
        stepBox.replaceChildren();
        steps.forEach((s, i) => {
          const row = el("div", "stepedit"); const t = el("input"); t.value = s.title; t.placeholder = "Step title"; t.setAttribute("aria-label", "Step " + (i + 1) + " title"); t.oninput = () => { s.title = t.value; };
          const ins = el("textarea"); ins.rows = 2; ins.value = s.instruction || ""; ins.placeholder = "What to do"; ins.setAttribute("aria-label", "Step " + (i + 1) + " instructions"); ins.oninput = () => { s.instruction = ins.value; };
          const ctl = el("div", "row");
          const mv = (d) => () => { const j = i + d; if (j < 0 || j >= steps.length) return; [steps[i], steps[j]] = [steps[j], steps[i]]; drawSteps(); };
          const up = el("button", "btn small ghost", "Up"), dn = el("button", "btn small ghost", "Down"), rm = el("button", "btn small ghost", "Remove");
          [up, dn, rm].forEach(b => { b.type = "button"; }); up.onclick = mv(-1); dn.onclick = mv(1); up.disabled = i === 0; dn.disabled = i === steps.length - 1;
          rm.onclick = () => { if (steps.length === 1) return Z.toast("A playbook needs at least one step", "bad"); steps.splice(i, 1); drawSteps(); };
          ctl.append(up, dn, rm); add(row, el("b", null, "Step " + (i + 1)), t, ins, ctl); stepBox.append(row);
        });
      };
      const form = S.form([
        { name: "name", label: "Name", required: true, value: pb.name }, { name: "intended_user", label: "Intended user", value: pb.intended_user },
        { name: "objective", label: "Objective", type: "textarea", rows: 2, value: pb.objective }, { name: "when_to_use", label: "When to use it", type: "textarea", rows: 2, value: pb.when_to_use },
        { name: "prerequisites", label: "Prerequisites (one per line)", type: "textarea", rows: 3, value: lines(pb.prerequisites) },
        { name: "recommended_actions", label: "Recommended actions (one per line)", type: "textarea", rows: 3, value: lines(pb.recommended_actions) },
        { name: "example_messages", label: "Example messages (one per line)", type: "textarea", rows: 4, value: lines(pb.example_messages) },
        { name: "expected_outcome", label: "Expected outcome", type: "textarea", rows: 2, value: pb.expected_outcome }, { name: "completion_criteria", label: "Completion criteria", type: "textarea", rows: 2, value: pb.completion_criteria },
        { name: "common_mistakes", label: "Common mistakes (one per line)", type: "textarea", rows: 3, value: lines(pb.common_mistakes) }, { name: "next_recommended", label: "Next recommended action", value: pb.next_recommended }],
        "Save new version", async v => {
          await S.api(`playbooks/${pb.id}/update`, { ...v, prerequisites: unlines(v.prerequisites), recommended_actions: unlines(v.recommended_actions), example_messages: unlines(v.example_messages), common_mistakes: unlines(v.common_mistakes), steps });
          Z.toast("Saved", "ok"); await Z.rerender();
        });
      const stepsHead = el("div", "row wide"); stepsHead.append(el("h3", "gh", "Steps"));
      const addStep = el("button", "btn small ghost", "Add step"); addStep.type = "button"; addStep.onclick = () => { steps.push({ title: "", instruction: "" }); drawSteps(); };
      const holder = el("div", "wide list"); add(holder, stepsHead, stepBox, addStep);
      form.insertBefore(holder, form.querySelector("p.err")); drawSteps();
      ed.append(form); g.append(ed);

      const act = card("Use it"); act.classList.add("s6");
      act.append(S.form([{ name: "lead_id", label: "Start on a prospect (optional)", type: "select", options: [["", "No prospect (just track the steps)"]].concat((await S.api("prospects")).prospects.filter(p => !p.playbook_run_id).map(p => [p.id, S.who(p)])) }], "Start this playbook",
        async v => { const r = await S.api(`playbooks/${pb.id}/start`, v); S.go(v.lead_id ? "prospect/" + v.lead_id : "playbook/" + pb.id); Z.toast("Started", "ok"); }));
      const row = el("div", "row");
      row.append(btn("Duplicate", "small", async () => { const r = await S.api(`playbooks/${pb.id}/duplicate`, {}); Z.toast("Duplicated", "ok"); S.go("playbook/" + r.playbook.id); }),
        btn(pb.archived ? "Restore" : "Archive", "small ghost", async () => { await S.api(`playbooks/${pb.id}/${pb.archived ? "unarchive" : "archive"}`, {}); S.go("playbooks"); }));
      act.append(row); g.append(act);

      const { runs } = await S.api(`playbooks/${pb.id}/runs`);
      const rc = card("Previous executions", runs.length + " run(s)"); rc.classList.add("s6");
      const rl = el("div", "list"); if (!runs.length) rl.append(Z.empty("Not used yet"));
      runs.forEach(r => { const it = el("div", "item"); add(it, el("div", "t", r.lead_business || r.lead_name || "No prospect"), add(el("div", "meta"), pill(r.status, r.status === "completed" ? "ok" : r.status === "abandoned" ? "bad" : "gold"), pill(r.done_count + "/" + r.steps.length + " steps"), pill("v" + r.playbook_version), pill(fmt.when(r.started_at))));
        if (r.outcome_note) it.append(el("div", "sub", r.outcome_note)); if (r.lead_id) { const a = el("a", null, "Open prospect"); a.href = "#prospect/" + r.lead_id; it.append(a); } rl.append(it); });
      rc.append(rl); g.append(rc);
      root.append(g);
    },
  };
})();
