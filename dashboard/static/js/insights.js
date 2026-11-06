// Insights: performance (counts first), learning (facts / hypotheses / suggestions kept visibly separate), business timeline.
(function () {
  const { el, add, text, pill, card, fmt } = Z;
  const S = window.Sales;
  const table = (heads, rows) => {
    const w = el("div", "tablewrap compact"), t = el("table"), hr = el("tr"); heads.forEach(h => hr.append(el("th", null, h))); t.append(hr);
    rows.forEach(r => { const tr = el("tr"); r.forEach(c => tr.append(el("td", null, c == null ? "n/a" : c))); t.append(tr); }); w.append(t); return w;
  };

  Z.pages.insights = {
    title: "Insights", sub: "What actually happened, and what it might mean", icon: "chart",
    async render(root) {
      await S.load();
      const [perf, learn, act] = await Promise.all([S.api("insights/performance"), S.api("insights/learning"), S.api("activity")]);
      const g = el("div", "grid");
      const c = perf.counts;
      const pc = card("Performance · recorded facts", perf.sample_note); pc.classList.add("s12");
      const tiles = el("div", "tiles");
      [["Prospects discovered", c.prospects_discovered], ["Researched", c.prospects_researched], ["Qualified", c.prospects_qualified], ["Initial messages sent", c.initial_messages_sent],
       ["Follow-ups sent", c.followup_messages_sent], ["Follow-ups completed", c.followups_completed], ["Responses", c.responses_received], ["Positive responses", c.positive_responses],
       ["Meetings booked", c.meetings_booked], ["Proposals sent", c.proposals_sent], ["Customers won", c.customers_won], ["Customers lost", c.customers_lost],
       ["Follow-ups outstanding", c.followups_outstanding], ["…of which overdue", c.followups_overdue]]
        .forEach(([l, v]) => { const t = el("div", "tile"); add(t, el("div", "label", l), el("div", "stat", v)); tiles.append(t); });
      pc.append(tiles);
      const rev = Object.entries(perf.revenue_recorded);
      pc.append(el("p", "sub", "Revenue recorded: " + (rev.length ? rev.map(([k, v]) => S.money(v, k)).join(" · ") : "none yet") + ". " + perf.revenue_note));
      g.append(pc);

      const cv = card("Conversion", "Counts first. A percentage appears only once the sample is large enough."); cv.classList.add("s6");
      cv.append(table(["Step", "Count", "Rate"], perf.conversion.map(r => [r.step, r.label, r.pct == null ? "too few to read" : r.pct + "%"])));
      g.append(cv);
      const tm = card("Time between stages", "From when things happened, not when recorded"); tm.classList.add("s6");
      tm.append(table(["Step", "Prospects", "Median days", "Range"], perf.timing.map(r => [r.step, r.n, r.median_days, r.n ? r.min_days + "–" + r.max_days : "n/a"])));
      g.append(tm);

      const lc = card("What you've learned", "Three kinds of statement, labelled so they are never confused."); lc.classList.add("s12");
      const legend = el("div", "row"); add(legend, pill("Recorded fact", "ok"), pill("Hypothesis", "warn"), pill("Rule-based suggestion", "gold")); lc.append(legend);
      const sec = (title, kind, kindLabel, items, empty) => {
        const b = el("div", "list"); b.append(el("h3", "gh", title));
        if (!items.length) b.append(Z.empty(empty)); items.forEach(i => { const it = el("div", "item"); add(it, add(el("div", "row"), pill(kindLabel, kind)), el("div", null, i.text)); if (i.why) it.append(el("div", "sub", "Why: " + i.why)); b.append(it); });
        lc.append(b);
      };
      sec("Facts", "ok", "Recorded fact", learn.facts, "No facts yet. Record outreach with a channel and an approach label.");
      sec("Hypotheses", "warn", "Hypothesis", learn.hypotheses, "Nothing to suggest yet. A pattern needs at least 5 prospects per approach.");
      sec("Suggestions", "gold", "Rule-based suggestion", learn.recommendations, "No suggestions.");
      g.append(lc);

      const T = learn.tables;
      [["By channel", T.by_channel], ["By approach", T.by_angle], ["By industry", T.by_industry], ["By prospect source", T.by_source]].forEach(([title, rows]) => {
        const cc = card(title); cc.classList.add("s6");
        cc.append(rows.length ? table(["Name", "Messaged", "Responded", "Positive", "Meetings", "Won"], rows.map(r => [r.name, r.prospects, r.responded, r.positive, r.meetings, r.won])) : Z.empty("No data yet"));
        g.append(cc);
      });
      const pb = card("Playbook usage"); pb.classList.add("s6");
      pb.append(T.playbooks.length ? table(["Playbook", "Runs", "Completed", "Abandoned", "Often stops before"], T.playbooks.map(r => [r.name, r.runs, r.completed, r.abandoned, r.most_common_stop || "n/a"])) : Z.empty("No playbook runs yet"));
      g.append(pb);
      const cons = card("Consistency", "Research, qualification, messages and follow-ups per day, last 14 days"); cons.classList.add("s6");
      const max = Math.max(1, ...T.activity_last_14_days.map(d => d.actions));
      T.activity_last_14_days.forEach(d => { const r = el("div", "yr"); const bar = el("i"); bar.style.width = Math.round(100 * d.actions / max) + "%"; add(r, el("span", null, d.date.slice(5)), bar, el("b", null, d.actions + " action(s)")); cons.append(r); });
      g.append(cons);

      const tl = card("Business timeline", "Everything recorded, newest first"); tl.classList.add("s12");
      const list = el("div", "list"); if (!act.events.length) list.append(Z.empty("Nothing recorded yet"));
      let last = null;
      const draw = evs => evs.forEach(e => { list.append(S.eventItem(e, true)); last = e.id; });
      draw(act.events); tl.append(list);
      if (act.events.length >= 100) tl.append(Z.btn("Load older", "ghost small", async () => { const r = await S.api("activity/before/" + last); draw(r.events); }));
      g.append(tl);
      root.append(g);
    },
  };
})();
