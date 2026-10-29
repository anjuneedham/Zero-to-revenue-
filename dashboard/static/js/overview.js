(function () {
  const { el, add, pill, btn, card, fmt } = Z;

  Z.pages.overview = {
    title: "Overview", sub: "Cash, payments and alerts at a glance", icon: "home",
    async render(root) {
      const [s, n, t, pay, plan, pt] = await Promise.all([Z.api("/api/status"), Z.api("/api/notifications"), Z.api("/api/payments/overview"), Z.api("/api/payments"),
        fetch("/data/plan.json").then(r => r.json()).catch(() => null), Z.api("/api/plan").catch(() => null)]);
      Z.state.status = s; Z.paintStatus(s);
      const g = el("div", "grid");

      const hero = el("section", "card hero s8");
      add(hero, el("div", "label", "Verified revenue · only confirmed receipts count"), el("div", "big", fmt.usd(s.verified_revenue_usd)),
        el("p", "sub", s.verified_receipts_without_usd_value ? s.verified_receipts_without_usd_value + " verified receipt(s) have no USD price yet, so they are not counted." : "Promised, pending and estimated money never counts here."));
      const tiles = el("div", "tiles");
      [["Payments awaited", s.payments_pending], ["Last verified", s.last_verified_payment ? fmt.ago(s.last_verified_payment) : "none yet"]]
        .forEach(([l, v]) => { const c = el("div", "tile"); add(c, el("div", "label", l), el("div", "stat", v)); tiles.append(c); });
      hero.append(tiles); g.append(hero);

      const ks = card("Kill switch", "Stops every scheduled job. Resuming needs your sign-in."); ks.classList.add("s4");
      ks.append(btn("Red card · pause everything", "red", async () => { await Z.api("/api/pause", "POST"); Z.toast("Paused", "bad"); await Z.rerender(); }, "stop"),
        btn("Resume play", "gold", async () => { await Z.api("/api/resume", "POST"); Z.toast("Play resumed", "ok"); await Z.rerender(); }, "play"));
      g.append(ks);

      if (plan && pt) { const pc = Z.progressCard(plan, pt.ticks); pc.classList.add("s12"); g.append(pc); }

      const owe = card("Payments needing you", "Request a PayPal link or check if one is paid - right here."); owe.classList.add("s6");
      const owl = el("div", "list");
      const outstanding = pay.payments.filter(p => p.status !== "PAYMENT_VERIFIED");
      if (!outstanding.length) owl.append(Z.empty("Nothing pending", "Payments appear here when you create a deal on the Challenge page or add one on Payments."));
      outstanding.slice(0, 5).forEach(p => {
        const it = el("div", "item"); add(it, el("div", "t", p.title || p.id),
          pill((p.expected_amount == null ? "?" : fmt.num(p.expected_amount, 2)) + " " + (p.asset || "") + " expected"));
        if (t.paypal) it.append(Z.paypalForm(p));
        owl.append(it);
      });
      owe.append(owl); g.append(owe);

      const feed = card("Messages", "Every alert the system raised. WhatsApp delivery starts once Twilio is connected."); feed.classList.add("s6");
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
