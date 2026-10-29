(function () {
  const { el, add, pill, btn, card, fmt, nice } = Z;
  const VENT = { buildflow: "BuildFlow", agriloop: "AgriLoop" };
  const STAGES = [["new", "New"], ["contacted", "Contacted"], ["replied", "Replied"], ["onboarding_booked", "Onboarding booked"], ["trial", "Trial"], ["paying", "Paying"], ["lost", "Lost"]];
  const CHANNELS = ["email", "whatsapp", "instagram", "facebook", "call", "in_person", "other"];
  const usd0 = v => "$" + Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
  const leadName = l => l.business || l.name || l.email || l.phone || "Unnamed";
  const field = (label, node) => { const l = el("label", "f", label); l.append(node); return l; };
  const input = (ph, type) => { const i = el("input"); i.placeholder = ph || ""; if (type) i.type = type; i.setAttribute("aria-label", ph || "field"); return i; };
  const select = (opts, val) => { const s = el("select"); opts.forEach(o => { const [v, t] = Array.isArray(o) ? o : [o, nice(o)]; const op = el("option", null, t); op.value = v; s.append(op); }); if (val) s.value = val; return s; };

  // ---- draft + log drawer for one lead ----
  async function openLead(l, refresh, plans) {
    const box = el("div", "list");
    const ch = select(CHANNELS, l.email ? "email" : l.phone ? "whatsapp" : "instagram");
    const ta = el("textarea", "draft"); ta.rows = 12;
    const load = async followUp => { const d = await Z.api("/api/challenge/draft", "POST", { lead_id: l.id, channel: ch.value, follow_up: followUp }); ta.value = d.draft; };
    ch.onchange = () => load(l.stage !== "new").catch(e => Z.toast(e.message, "bad"));
    add(box, add(el("div", "meta"), pill(VENT[l.venture]), pill(nice(l.stage), "gold"), l.segment ? pill(l.segment) : null, l.location ? pill(l.location) : null),
      el("div", "sub", [l.name, l.email, l.phone].filter(Boolean).join(" · ")), l.notes ? el("p", "sub", l.notes) : null,
      field("Channel", ch), ta,
      el("p", "sub", "Fill every [OWNER TO FILL] before sending. Nothing is sent from here: copy it, send it yourself (or send email through the Operator), then log it."));
    const row = el("div", "row");
    add(row,
      btn("Copy", "ghost small", () => Z.copy(ta.value, "Message"), "copy"),
      btn("I sent it - log it", "gold small", async () => { await Z.api("/api/challenge/touch", "POST", { lead_id: l.id, channel: ch.value, outcome: "sent", body: ta.value }); Z.toast("Logged. Follow-up in 3 days.", "ok"); Z.$("drawer").close(); await refresh(); }),
      btn("They replied", "small", async () => { await Z.api("/api/challenge/touch", "POST", { lead_id: l.id, channel: ch.value, direction: "in", outcome: "replied" }); Z.toast("Marked replied", "ok"); Z.$("drawer").close(); await refresh(); }),
      btn("Onboarding booked", "small", async () => { await Z.api("/api/challenge/touch", "POST", { lead_id: l.id, channel: ch.value, outcome: "booked" }); Z.toast("Onboarding booked", "ok"); Z.$("drawer").close(); await refresh(); }));
    box.append(row);
    const row2 = el("div", "row");
    const lp = plans.filter(p => p.venture === l.venture); const seg = (l.segment || "").toLowerCase();
    const planSel = select([["", lp.length > 1 ? "Choose plan…" : lp[0].label], ...(lp.length > 1 ? lp.map(p => [p.key, `${p.label} ${usd0(p.annual_usd)}/yr`]) : [])]);
    const hint = lp.find(p => (p.key.startsWith("farmer") && seg.includes("farm")) || (p.key.startsWith("buyer") && seg.includes("buy"))); if (hint) planSel.value = hint.key;
    planSel.hidden = lp.length < 2;
    const reason = input("Why lost? (optional)");
    add(row2, planSel, btn("They said yes - create the deal", "gold small", async () => { const r = await Z.api("/api/challenge/deal", "POST", { lead_id: l.id, plan: planSel.value }); Z.toast(r.plan + " deal: " + usd0(r.amount_usd) + ". Tap Copy PayPal message on the deal card.", "ok"); Z.$("drawer").close(); await refresh(); }),
      reason, btn("Not interested / opt-out", "ghost small", async () => { await Z.api("/api/challenge/stage", "POST", { lead_id: l.id, stage: "lost", reason: reason.value }); Z.toast("Marked lost. Will not be drafted again.", "ok"); Z.$("drawer").close(); await refresh(); }));
    box.append(row2);
    Z.openDrawer(leadName(l), box);
    load(l.stage !== "new").catch(e => Z.toast(e.message, "bad"));
  }

  function addLeadForm(refresh) {
    const f = el("div", "form");
    const v = select([["buildflow", "BuildFlow"], ["agriloop", "AgriLoop"]]);
    const name = input("Contact name"), biz = input("Business / farm"), email = input("Email (optional)", "email"), phone = input("Phone / WhatsApp"),
      seg = input("Trade or crop"), loc = input("Parish / town"), ch = select(CHANNELS, "whatsapp"), notes = input("Notes");
    add(f, field("Venture", v), name, biz, email, phone, seg, loc, field("Found them via", ch), notes,
      btn("Add lead", "gold small", async () => {
        await Z.api("/api/challenge/leads", "POST", { venture: v.value, name: name.value, business: biz.value, email: email.value, phone: phone.value, segment: seg.value, location: loc.value, channel: ch.value, notes: notes.value });
        Z.toast("Lead added", "ok"); await refresh();
      }));
    return f;
  }

  function importForm(refresh) {
    const f = el("div", "form");
    const v = select([["buildflow", "BuildFlow"], ["agriloop", "AgriLoop"]]);
    const ta = el("textarea"); ta.rows = 5; ta.placeholder = "name,business,email,phone,notes\nJane Doe,Doe Tiling,jane@example.com,876-555-0100,saw her Instagram";
    add(f, field("Paste CSV for", v), ta, btn("Import", "small", async () => {
      const r = await Z.api("/api/leads/import", "POST", { csv: ta.value, venture: v.value });
      Z.toast(`Added ${r.added}, skipped ${r.skipped_duplicates} duplicates`, "ok"); await refresh();
    }));
    return f;
  }

  // ---- screenshot / pasted text -> candidates the owner reviews; nothing is created or sent until "Add lead" ----
  const readAsDataURL = f => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = () => rej(new Error("Could not read that file")); r.readAsDataURL(f); });
  async function downscale(file) {
    const url = await readAsDataURL(file);
    const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error("That is not an image")); i.src = url; });
    const k = Math.min(1, 1600 / Math.max(img.width, img.height)), cv = document.createElement("canvas");
    cv.width = Math.round(img.width * k); cv.height = Math.round(img.height * k);
    cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height);
    return cv.toDataURL("image/jpeg", 0.85).split(",")[1];
  }

  function ingestForm(ing, refresh) {
    const f = el("div", "form"), out = el("div", "list");
    const v = select([["buildflow", "BuildFlow"], ["agriloop", "AgriLoop"]]);
    const ta = el("textarea"); ta.rows = 5; ta.placeholder = "Paste a profile bio, a chat or a contact list here. You can also paste a screenshot (Ctrl/Cmd+V) or choose one below.";
    const file = el("input"); file.type = "file"; file.accept = "image/png,image/jpeg,image/webp"; file.setAttribute("aria-label", "Screenshot");
    let image = null;
    const setImage = async fl => { try { image = await downscale(fl); Z.toast("Screenshot ready", "ok"); } catch (e) { image = null; Z.toast(e.message, "bad"); } };
    file.onchange = () => file.files[0] && setImage(file.files[0]);
    ta.addEventListener("paste", e => { const it = [...(e.clipboardData ? e.clipboardData.items : [])].find(x => x.type.startsWith("image/")); if (it) { e.preventDefault(); setImage(it.getAsFile()); } });
    add(f, el("p", "sub", ing.images ? "Screenshots are read by AI within your monthly budget. The image is not stored. Review every field before adding: it may contain mistakes." : "Screenshot reading is off until ANTHROPIC_API_KEY and the LLM budget settings are set. Pasted text still works (emails, phone numbers and @handles are picked out without AI)."),
      field("Add to", v), ta, field("Screenshot", file));
    const show = res => {
      out.replaceChildren();
      if (res.notes) out.append(el("p", "sub", res.notes));
      res.candidates.forEach(c => {
        const box = el("div", "item"), g = {};
        if (c.flags.length) box.append(pill("Contains instruction-like text - ignore it", "bad"));
        [["name", "Name"], ["business", "Business / farm"], ["phone", "Phone / WhatsApp"], ["email", "Email"], ["instagram", "Instagram handle"], ["segment", "Trade or crop"], ["location", "Parish / town"], ["notes", "Notes"]]
          .forEach(([k, label]) => { g[k] = input(label); g[k].value = c[k] || ""; box.append(g[k]); });
        box.append(btn("Add lead", "gold small", async () => {
          const handle = g.instagram.value.trim().replace(/^@/, "");
          const notes = [g.notes.value.trim(), handle ? "Instagram @" + handle : ""].filter(Boolean).join(" · ");
          try {
            await Z.api("/api/challenge/leads", "POST", { venture: v.value, name: g.name.value, business: g.business.value, email: g.email.value, phone: g.phone.value, segment: g.segment.value, location: g.location.value, channel: handle ? "instagram" : g.phone.value ? "whatsapp" : "email", notes });
            Z.toast("Lead added", "ok"); box.remove(); await refresh();
          } catch (e) { Z.toast(e.message, "bad"); }
        }));
        out.append(box);
      });
    };
    add(f, btn("Read it", "gold small", async () => {
      try { show(await Z.api("/api/challenge/ingest", "POST", { text: ta.value, image: image || "", mime: image ? "image/jpeg" : "" })); }
      catch (e) { Z.toast(e.message, "bad"); }
    }), out);
    return f;
  }

  function configForm(c, refresh) {
    const f = el("div", "form");
    const target = input("Target USD", "number"); target.value = c.target_usd;
    const start = input("Start", "date"); start.value = c.start; const end = input("End", "date"); end.value = c.end;
    add(f, field("Cash target (USD)", target), field("Starts", start), field("Ends", end));
    const offers = {};
    ["buildflow", "agriloop"].forEach(k => {
      const o = c.offers[k], fm = input("Free months", "number"); fm.value = o.free_months; offers[k] = { fm, tiers: {} };
      add(f, el("h3", null, VENT[k] + " offer"), field("Free months (annual = 12 minus this, in months billed)", fm));
      Object.entries(o.tiers).forEach(([tk, t]) => { const m = input("Monthly USD", "number"); m.value = t.monthly_usd; offers[k].tiers[tk] = m; add(f, field(t.label + " - monthly price (USD)", m)); });
    });
    add(f, btn("Save", "gold small", async () => {
      const body = { target_usd: target.value, start: start.value, end: end.value, offers: {} };
      Object.entries(offers).forEach(([k, o]) => { body.offers[k] = { free_months: parseInt(o.fm.value, 10), tiers: Object.fromEntries(Object.entries(o.tiers).map(([tk, m]) => [tk, m.value])) }; });
      await Z.api("/api/challenge/config", "POST", body); Z.toast("Saved", "ok"); Z.$("drawer").close(); await refresh();
    }));
    return f;
  }

  Z.pages.challenge = {
    title: "Challenge", sub: "60 days, $10k cash: sell annual plans with 1-on-1 onboarding", icon: "target",
    async render(root) {
      const [s, ld, pay, t] = await Promise.all([Z.api("/api/challenge"), Z.api("/api/challenge/leads"), Z.api("/api/payments"), Z.api("/api/treasury/overview")]);
      const refresh = () => Z.rerender();
      const c = s.config, g = el("div", "grid");

      // hero
      const hero = el("section", "card hero s8");
      const when = s.state === "before" ? `Starts in ${s.starts_in_days} day${s.starts_in_days === 1 ? "" : "s"} (${c.start})` : s.state === "after" ? "Challenge ended" : `Day ${s.day} of ${s.total_days} · ${s.days_left} left`;
      add(hero, el("div", "label", "Verified cash in the challenge window · " + when), el("div", "big", fmt.usd(s.cash_usd) + " / " + usd0(s.target_usd)));
      const bar = el("div", "bar"); const fill = el("i"); fill.style.width = Math.min(100, 100 * s.cash_usd / s.target_usd) + "%"; bar.append(fill); hero.append(bar);
      const ahead = s.ahead_by_usd >= 0;
      hero.append(el("p", "sub", s.state === "running" ? (ahead ? `Ahead of pace by ${usd0(s.ahead_by_usd)}.` : `Behind pace by ${usd0(-s.ahead_by_usd)} (pace target today: ${usd0(s.pace_target_usd)}).`) : "Only payments Treasury has verified count as cash. Pipeline is not cash."));
      const tiles = el("div", "tiles");
      [["Still to earn", usd0(s.remaining_usd)], ["BuildFlow deals needed", s.deals_needed == null ? "-" : s.deals_needed], ["Per week needed", s.per_week_needed == null ? "-" : s.per_week_needed], ["Open deals", `${s.deals_open} · ${usd0(s.pipeline_usd)}`]]
        .forEach(([l, v]) => { const x = el("div", "tile"); add(x, el("div", "label", l), el("div", "stat", v)); tiles.append(x); });
      hero.append(tiles); g.append(hero);

      // offer + actions
      const off = card("The offer", "Annual plan: 12 months for the price of 10, personal 1-on-1 onboarding."); off.classList.add("s4");
      s.plans.forEach(p => off.append(el("div", "item", `${VENT[p.venture]} ${p.venture === "buildflow" ? "" : p.label + " "}$${p.monthly_usd}/mo → ${usd0(p.annual_usd)}/year (${p.free_months} months free) · ${p.deals_needed} deals = the target`)));
      add(off, btn("Edit target & prices", "ghost small", async () => Z.openDrawer("Challenge settings", configForm(c, refresh))),
        btn("Add a lead", "gold small", async () => Z.openDrawer("Add a lead", addLeadForm(async () => { Z.$("drawer").close(); await refresh(); }))),
        btn("From screenshot / paste", "ghost small", async () => Z.openDrawer("Add leads from a screenshot or pasted text", ingestForm(s.ingest, refresh))),
        btn("Import CSV", "ghost small", async () => Z.openDrawer("Import leads (CSV)", importForm(async () => { Z.$("drawer").close(); await refresh(); }))));
      g.append(off);

      // today
      const today = card("Do these today", "Replies first, then booked onboardings, then follow-ups due, then fresh leads."); today.classList.add("s8");
      const tl = el("div", "list");
      if (!s.due.length) tl.append(Z.empty("Nothing due", "Add leads (people you can reach in person, WhatsApp or Instagram) to fill this list."));
      s.due.forEach(l => {
        const why = l.stage === "new" ? "first message" : l.stage === "replied" ? "they replied - answer now" : l.stage === "onboarding_booked" ? "onboarding booked" : "follow-up due";
        const it = el("div", "item click"); add(it, add(el("div", "meta"), pill(VENT[l.venture]), pill(why, l.stage === "replied" ? "gold" : ""), l.channel ? pill(l.channel) : null), el("div", "t", leadName(l)));
        it.onclick = () => openLead(l, refresh, s.plans); tl.append(it);
      });
      today.append(tl); g.append(today);

      // readiness
      const rd = card("Before you sell", "Known blockers from each product's own readiness reports. Be honest about these on calls."); rd.classList.add("s4");
      Object.entries(s.blockers).forEach(([k, arr]) => { rd.append(el("h3", null, VENT[k])); arr.forEach(b => rd.append(el("p", "sub", "• " + b))); });
      g.append(rd);

      // funnel
      const fn = card("Pipeline", "Leads by stage"); fn.classList.add("s6");
      ["buildflow", "agriloop"].forEach(k => {
        const row = el("div", "row"); row.append(el("b", null, VENT[k]));
        STAGES.forEach(([st, label]) => row.append(pill(label + " " + s.funnel[k][st], st === "paying" ? "ok" : st === "lost" ? "bad" : "")));
        fn.append(row);
      });
      g.append(fn);

      // learning loop
      const lp = card("What's working", `${s.touches_week} message${s.touches_week === 1 ? "" : "s"} sent in the last 7 days. Replies and paid by channel.`); lp.classList.add("s6");
      if (!s.by_channel.length) lp.append(Z.empty("No data yet", "Log each message you send; this shows which channel actually converts."));
      s.by_channel.forEach(r => lp.append(add(el("div", "row"), el("b", null, nice(r.channel)), pill(r.sent + " sent"), pill(r.replies + " replied", r.replies ? "gold" : ""), pill(r.paying + " paying", r.paying ? "ok" : ""))));
      g.append(lp);

      // deals
      const dl = card("Deals & payments", "Tap Copy PayPal message, paste it to the customer yourself, then Check if paid. Cash counts only once verified."); dl.classList.add("s12");
      const dlist = el("div", "list");
      if (!s.deals.length) dlist.append(Z.empty("No deals yet", "Open a lead and press 'They paid / close the deal' when they say yes."));
      s.deals.forEach(d => {
        const p = pay.payments.find(x => x.id === d.payment_id);
        const it = el("div", "item");
        add(it, add(el("div", "meta"), pill(VENT[d.venture]), pill(d.status === "paid" ? "Paid & verified" : "Awaiting payment", d.status === "paid" ? "ok" : "warn"), pill(d.free_months + " months free"), pill("Onboarding: " + nice(d.onboarding_status), d.onboarding_status === "done" ? "ok" : "")),
          el("div", "t", `${d.business || d.name || "Customer"} · ${usd0(d.amount_usd)}`));
        if (d.status !== "paid" && t.paypal) {
          const warn = d.venture === "agriloop" ? "AgriLoop's database is not confirmed live yet. Only continue if it is. Create the PayPal message?" : "";
          it.append(btn("Copy PayPal message", "gold small", async () => {
            if (warn && !window.confirm(warn)) return;
            try {
              const r = await Z.api("/api/challenge/paypal-message", "POST", { deal_id: d.id });
              await Z.copy(r.message, "PayPal message");
              if (r.warning) Z.toast(r.warning, "bad");
            } catch (e) { Z.toast(e.message, "bad"); }
          }, "copy"));
        }
        if (d.status !== "paid" && p) { if (t.paypal) it.append(Z.paypalForm(p)); if (t.chains.length) it.append(Z.verifyForm(p, t.chains)); }
        const ob = select([["to_schedule", "Onboarding: to schedule"], ["scheduled", "Onboarding: scheduled"], ["done", "Onboarding: done"]], d.onboarding_status);
        ob.onchange = async () => { try { await Z.api("/api/challenge/onboarding", "POST", { deal_id: d.id, status: ob.value }); Z.toast("Saved", "ok"); } catch (e) { Z.toast(e.message, "bad"); } };
        it.append(ob); dlist.append(it);
      });
      dl.append(dlist); g.append(dl);

      // all leads
      const all = card("All leads", "Tap a lead to draft, log a message, or close a deal."); all.classList.add("s12");
      const flt = select([["", "All ventures"], ["buildflow", "BuildFlow"], ["agriloop", "AgriLoop"]]);
      const fst = select([["", "All stages"], ...STAGES]);
      const list = el("div", "list");
      const paint = () => {
        list.replaceChildren();
        const rows = ld.leads.filter(l => (!flt.value || l.venture === flt.value) && (!fst.value || l.stage === fst.value));
        if (!rows.length) list.append(Z.empty("No leads here", "Add one or import a CSV."));
        rows.slice(0, 100).forEach(l => {
          const it = el("div", "item click");
          add(it, add(el("div", "meta"), pill(VENT[l.venture]), pill(nice(l.stage), l.stage === "paying" ? "ok" : l.stage === "lost" ? "bad" : "gold"), l.channel ? pill(l.channel) : null, l.last_contacted_at ? pill("last " + fmt.ago(l.last_contacted_at)) : null), el("div", "t", leadName(l)),
            el("div", "sub", [l.segment, l.location].filter(Boolean).join(" · ")));
          it.onclick = () => openLead(l, refresh, s.plans); list.append(it);
        });
      };
      flt.onchange = fst.onchange = paint; paint();
      add(all, add(el("div", "row"), flt, fst), list); g.append(all);
      root.append(g);
    },
  };
})();
