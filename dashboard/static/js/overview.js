(function () {
  const { el, add, text, pill, btn, card, fmt, nice } = Z;
  const STAGES = [["QUALIFIED", "Qualified"], ["IN_PROGRESS", "Drafted for you"], ["APPROVED", "Approved"], ["AWAITING_PAYMENT", "Submitted, awaiting payment"], ["PAYMENT_VERIFIED", "Paid and verified"], ["REVIEW_REQUIRED", "Needs your review"], ["REJECTED", "Rejected"]];
  const TEAM = [["scout", "11", "Winger", "Finds the chances", "#scout"], ["operator", "8", "Midfield", "Builds the play", "#operator"], ["treasury", "1", "Keeper", "Guards the money", "#treasury"]];

  Z.pages.overview = {
    title: "Overview", sub: "Everything that needs you, at a glance", icon: "home",
    async render(root) {
      const [s, n] = await Promise.all([Z.api("/api/status"), Z.api("/api/notifications")]);
      Z.state.status = s; Z.paintStatus(s);
      const g = el("div", "grid");

      const hero = el("section", "card hero s8");
      add(hero, el("div", "label", "Verified revenue · only confirmed receipts count"), el("div", "big", fmt.usd(s.verified_revenue_usd)),
        el("p", "sub", s.verified_receipts_without_usd_value ? s.verified_receipts_without_usd_value + " verified receipt(s) have no USD price yet, so they are not counted." : "Promised, pending and estimated money never counts here."));
      const tiles = el("div", "tiles");
      [["Payments awaited", s.payments_pending], ["Waiting for you", s.health.operator_waiting_for_you], ["Qualified", s.opportunities.QUALIFIED || 0], ["Found today", s.health.scout_opportunities_today]]
        .forEach(([l, v]) => { const t = el("div", "tile"); add(t, el("div", "label", l), el("div", "stat", v)); tiles.append(t); });
      hero.append(tiles); g.append(hero);

      const ks = card("Kill switch", "Stops every agent and scheduled job. Resuming needs your sign-in."); ks.classList.add("s4");
      ks.append(btn("Red card · pause all agents", "red", async () => { await Z.api("/api/pause", "POST"); Z.toast("All agents paused", "bad"); await Z.rerender(); }, "stop"),
        btn("Resume play", "gold", async () => { await Z.api("/api/resume", "POST"); Z.toast("Play resumed", "ok"); await Z.rerender(); }, "play"));
      g.append(ks);

      const team = card("Team sheet", "Three agents, each with only the permissions its position needs."); team.classList.add("s12");
      const row = el("div", "cols");
      TEAM.forEach(([key, num, pos, role, href]) => {
        const a = s.agents.find(x => x.name === key) || { status: "offline" };
        const c = el("a", "item agent click"); c.href = href;
        add(c, el("div", "shirt", num));
        const h = el("h3", null, key); const dot = el("span", "dot " + (a.status === "online" ? "" : a.status === "error" ? "warn" : "off")); dot.style.display = "inline-block"; dot.style.marginLeft = "8px"; h.append(dot);
        const line = key === "scout" ? "Found today: " + s.health.scout_opportunities_today : key === "operator" ? "Waiting for you: " + s.health.operator_waiting_for_you : "Last wallet check: " + fmt.ago(s.health.treasury_last_check);
        add(c, h, el("div", "label", pos + " · " + role), el("div", "sub", line + " · run " + fmt.ago(a.last_run_at)));
        row.append(c);
      });
      team.append(row); g.append(team);

      const dec = card("Manager's decisions", "Drafts wait here. You review, submit on the platform yourself, then confirm."); dec.classList.add("s6");
      const dl = el("div", "list");
      if (!s.open_user_actions.length) dl.append(Z.empty("No decisions needed", "When the Operator drafts something, it appears here."));
      s.open_user_actions.forEach(a => dl.append(Z.decisionCard(a, () => Z.rerender())));
      dec.append(dl); g.append(dec);

      const pipe = card("Pipeline", "Where every opportunity stands"); pipe.classList.add("s6");
      const total = Object.values(s.opportunities).reduce((a, b) => a + b, 0);
      if (!total) pipe.append(Z.empty("Nothing found yet", "Open the Scout page and run it."));
      STAGES.forEach(([k, label]) => {
        const v = s.opportunities[k] || 0; if (!v) return;
        const r = el("div"); add(r, el("div", "row", null), el("div", "bar"));
        const head = r.firstChild; head.style.justifyContent = "space-between"; add(head, el("span", null, label), el("b", null, v));
        const fill = el("i"); fill.style.width = (100 * v / total) + "%"; r.lastChild.append(fill); pipe.append(r);
      });
      g.append(pipe);

      const feed = card("Dressing-room messages", "Every alert the system raised. WhatsApp delivery starts once Twilio is connected."); feed.classList.add("s12");
      const fl = el("div", "list");
      if (!n.notifications.length) fl.append(Z.empty("No messages yet"));
      const groups = []; n.notifications.forEach(m => { const g0 = groups.find(x => x.title === m.title && x.priority === m.priority); if (g0) g0.count++; else groups.push({ ...m, count: 1 }); });
      groups.slice(0, 6).forEach(m => {
        const it = el("div", "item"); add(it, add(el("div", "meta"), pill(m.priority, m.priority === "CRITICAL" ? "bad" : m.priority === "HIGH" ? "warn" : ""), pill(m.channel), pill(fmt.ago(m.created_at)), m.count > 1 ? pill("x" + m.count, "gold") : null),
          el("div", "t", m.title), el("div", "sub", m.body)); it.lastChild.style.whiteSpace = "pre-wrap"; fl.append(it);
      });
      feed.append(fl); g.append(feed);
      root.append(g);
    },
  };
})();
