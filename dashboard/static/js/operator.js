(function () {
  const { el, add, pill, btn, card, fmt, nice } = Z;
  const COLS = [["QUEUED", "Queued"], ["WAITING_FOR_USER", "Waiting for you"], ["AWAITING_PAYMENT", "Awaiting payment"], ["COMPLETED", "Done"], ["STOPPED", "Stopped"]];

  Z.pages.operator = {
    title: "Operator", sub: "Turns qualified opportunities into drafts. Never submits anything.", icon: "operator",
    async render(root) {
      const [s, b] = await Promise.all([Z.api("/api/status"), Z.api("/api/operator/board")]);
      Z.state.status = s; Z.paintStatus(s);
      const g = el("div", "grid");

      const top = el("section", "card hero s8");
      const head = el("div", "agent"); const a = s.agents.find(x => x.name === "operator") || {};
      add(head, el("div", "shirt", "8"), el("h3", null, "Operator"), el("div", "label", "Midfield · builds the play"), el("div", "sub", "Last run " + fmt.ago(a.last_run_at) + " · " + (a.status || "offline")));
      add(top, head, el("p", "sub", "Reads each qualified opportunity, writes a plan and a draft with placeholders for anything only you know, then waits for you. It cannot send, sign, pay or contact anyone."),
        btn("Run Operator", "gold", async () => {
          const r = await Z.api("/api/operator/run", "POST"); const n = r.steps.filter(x => x.task).length;
          Z.toast(r.steps[0] && r.steps[0].ran === false ? "Not run: " + r.steps[0].reason : n ? n + " draft(s) prepared" : "Nothing queued", "ok"); await Z.rerender();
        }, "play"));
      g.append(top);

      const rules = card("Boundaries", "Fixed in code, not settings."); rules.classList.add("s4");
      const ul = el("ul", "plain can"); b.can.forEach(t => ul.append(add(el("li"), el("span", null, "Can: " + t)))); const ul2 = el("ul", "plain cannot"); b.cannot.forEach(t => ul2.append(add(el("li"), el("span", null, "Never: " + t))));
      add(rules, ul, ul2); g.append(rules);

      const dec = card("Decisions waiting for you", "Review the draft, submit on the platform yourself, then confirm here."); dec.classList.add("s12");
      const dl = el("div", "cols"); if (!s.open_user_actions.length) dl.append(Z.empty("Nothing waiting", "Run Scout, then Run Operator."));
      s.open_user_actions.forEach(x => dl.append(Z.decisionCard(x, () => Z.rerender()))); dec.append(dl); g.append(dec);

      const leads = card("Leads (outreach)", "Paste a CSV of businesses YOU found (name,business,email,phone,notes). Nothing is scraped and nothing sends itself."); leads.classList.add("s12");
      const ta = el("textarea"); ta.rows = 4; ta.placeholder = "name,business,email,phone,notes\nJane Doe,Doe Contracting,jane@example.com,+1876...,met at trade fair";
      ta.setAttribute("aria-label", "Leads CSV");
      const impRow = el("div", "row");
      impRow.append(btn("Import leads", "ghost small", async () => {
        const r = await Z.api("/api/leads/import", "POST", { csv: ta.value });
        Z.toast(`${r.added} added, ${r.skipped_duplicates} already had that email`, "ok"); ta.value = ""; await Z.rerender();
      }), btn("Draft outreach for up to 15 new leads", "gold small", async () => {
        const r = await Z.api("/api/leads/draft", "POST", { count: 15 });
        Z.toast(r.drafted ? r.drafted + " draft(s) added to your decisions above" : "No new leads to draft", "ok"); await Z.rerender();
      }));
      const leadList = el("div", "list");
      const ld = await Z.api("/api/leads");
      if (!ld.leads.length) leadList.append(Z.empty("No leads yet", "Import a CSV of businesses you found yourself."));
      ld.leads.slice(0, 30).forEach(l => { const it = el("div", "item"); add(it, el("div", "t", l.business || l.name || l.email),
        add(el("div", "meta"), pill(l.email), pill(nice(l.status), l.status === "SENT" ? "ok" : l.status === "DRAFTED" ? "gold" : "")), l.phone ? el("div", "sub", l.phone) : null); leadList.append(it); });
      add(leads, ta, impRow, leadList); g.append(leads);

      const board = card("Task board", "Every task the Operator has touched"); board.classList.add("s12");
      const cols = el("div", "cols");
      COLS.forEach(([k, label]) => {
        const items = b.tasks.filter(t => (k === "STOPPED" ? ["FAILED", "CANCELLED", "SECURITY_HOLD"].includes(t.status) : t.status === k));
        const col = el("div", "col"); col.append(add(el("h3"), el("span", null, label), el("span", null, items.length)));
        if (!items.length) col.append(el("div", "sub", "Empty"));
        items.slice(0, 12).forEach(t => {
          const it = el("div", "item"); add(it, el("div", "t", t.title || Z.nice(t.kind)), add(el("div", "meta"), pill(nice(t.status), Z.statusKind(t.status)),
            t.expected_payment ? pill("$" + fmt.num(t.expected_payment, 0) + " claimed") : null, pill("try " + t.attempts + "/" + t.max_attempts), pill(fmt.ago(t.updated_at))));
          if (t.blocked_reason) it.append(el("div", "sub", "Blocked: " + t.blocked_reason)); if (t.next_action) it.append(el("div", "sub", "Next: " + t.next_action));
          col.append(it);
        });
        cols.append(col);
      });
      board.append(cols); g.append(board);

      const act = card("Activity", "Latest task events"); act.classList.add("s12");
      if (!b.events.length) act.append(Z.empty("No activity yet"));
      else { const t = el("div", "tablewrap"), tb = el("table"); const hr = el("tr"); ["When", "Event", "Task", "Detail"].forEach(h => hr.append(el("th", null, h))); tb.append(hr);
        b.events.slice(0, 20).forEach(e => { const tr = el("tr"); add(tr, el("td", null, fmt.when(e.created_at)), el("td", null, e.event), el("td", null, (e.title || "").slice(0, 60)), el("td", null, e.detail || "")); tb.append(tr); });
        t.append(tb); act.append(t); }
      g.append(act); root.append(g);
    },
  };
})();
