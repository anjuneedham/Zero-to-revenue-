(function () {
  const { el, add, pill, btn, card, fmt } = Z;
  let tab = "bf", data = null, ticks = {}, who = "ALL";
  const TABS = [["week", "This week"], ["bf", "BuildFlow launch"], ["acq", "First 5 users"], ["sources", "Get more jobs"], ["sys", "Your checklist"], ["road", "Roadmap"], ["year", "12-month plan"], ["cmd", "Commands"], ["app", "Get the app"]];
  const WHO = { owner: ["You", "gold"], agent: ["Agent", "royal"], both: ["Both", ""] };
  const CAT = { buildflow: ["BuildFlow", "gold"], jobs: ["Jobs", "ok"], study: ["Study", "royal"], improve: ["Improve", ""] };

  const mono = t => { const c = el("code", "key", t); c.style.margin = "0"; c.style.fontSize = "13px"; return c; };
  const table = (heads, rows) => {
    const w = el("div", "tablewrap"), tb = el("table"), hr = el("tr"); heads.forEach(h => hr.append(el("th", null, h))); tb.append(hr);
    rows.forEach(r => { const tr = el("tr"); r.forEach((c, i) => tr.append(el("td", null, c))); tb.append(tr); }); w.append(tb); return w;
  };

  function checklist(items, redraw) {
    const wrap = el("div", "list");
    const shown = items.filter(i => who === "ALL" || (who === "OPEN" ? !ticks[i.id] : i.who === who));
    ["P0", "P1", "P2"].forEach(p => {
      const group = shown.filter(i => i.p === p); if (!group.length) return;
      wrap.append(el("div", "label", { P0: "P0 · blocks launch", P1: "P1 · before the closed test", P2: "P2 · after" }[p]));
      group.forEach(i => {
        const done = !!ticks[i.id]; const row = el("label", "check" + (done ? " done" : "")); row.htmlFor = "c-" + i.id;
        const cb = el("input"); cb.type = "checkbox"; cb.id = "c-" + i.id; cb.checked = done;
        cb.onchange = async () => { try { const r = await Z.api("/api/plan", "POST", { id: i.id, done: cb.checked }); ticks = r.ticks; Z.toast(cb.checked ? "Ticked off" : "Reopened", "ok"); } catch (e) { cb.checked = !cb.checked; Z.toast(e.message, "bad"); } redraw(); };
        const mid = el("div"); add(mid, el("b", null, i.title), el("p", null, i.detail)); if (i.src) mid.append(el("small", null, "Source: " + i.src));
        add(row, cb, mid, pill(WHO[i.who][0], WHO[i.who][1])); wrap.append(row);
      });
    });
    if (!shown.length) wrap.append(Z.empty("Nothing here", "Try another filter."));
    return wrap;
  }

  function list(items, redraw) {
    const box = el("div", "list"); const all = items.length, done = items.filter(i => ticks[i.id]).length;
    const bar = el("div", "bar"); const f = el("i"); f.style.width = (all ? 100 * done / all : 0) + "%"; bar.append(f);
    box.append(add(el("div", "row"), el("b", null, done + " of " + all + " done")), bar);
    const chips = el("div", "chips"); [["ALL", "All"], ["OPEN", "Still open"], ["owner", "Only you"], ["agent", "Only the agent"], ["both", "Both"]].forEach(([k, l]) => {
      const b = el("button", null, l); b.type = "button"; b.setAttribute("aria-pressed", who === k); b.onclick = () => { who = k; redraw(); }; chips.append(b); });
    box.append(chips, checklist(items, redraw)); return box;
  }

  function weekDay(day, redraw) {
    const sec = el("div", "item");
    add(sec, el("div", "t", day.day + " · " + day.date));
    day.items.forEach(i => {
      const done = !!ticks[i.id]; const row = el("label", "check" + (done ? " done" : "")); row.htmlFor = "c-" + i.id;
      const cb = el("input"); cb.type = "checkbox"; cb.id = "c-" + i.id; cb.checked = done;
      cb.onchange = async () => { try { const r = await Z.api("/api/plan", "POST", { id: i.id, done: cb.checked }); ticks = r.ticks; Z.toast(cb.checked ? "Ticked off" : "Reopened", "ok"); } catch (e) { cb.checked = !cb.checked; Z.toast(e.message, "bad"); } redraw(); };
      const mid = el("div"); add(mid, el("b", null, i.title), el("p", null, i.detail));
      add(row, cb, mid, pill(CAT[i.cat][0], CAT[i.cat][1])); sec.append(row);
    });
    return sec;
  }

  const panels = {
    week(redraw) {
      const all = data.week.days.flatMap(d => d.items);
      const done = all.filter(i => ticks[i.id]).length;
      const c = card("This week", data.week.range);
      const bar = el("div", "bar"); const f = el("i"); f.style.width = (all.length ? 100 * done / all.length : 0) + "%"; bar.append(f);
      c.append(add(el("div", "row"), el("b", null, done + " of " + all.length + " done")), bar);
      const l = el("div", "list");
      data.week.days.forEach(day => l.append(weekDay(day, redraw)));
      c.append(l); return c;
    },
    bf(redraw) {
      const c = card("BuildFlow: path to launch", "Read from the BuildFlow repo on 25 Oct. Verdict in its own report: not ready, with one owner-side blocker (Storage).");
      c.append(el("p", "sub", "BuildFlow is live in beta at buildflow-app-beta.vercel.app: customer and project management for contractors, a public profile where customers find them, $50/month with a 14-day trial. The code is in good shape; launch is blocked by setup only you can do, and by billing, which is not built yet."), list(data.buildflow, redraw)); return c;
    },
    acq(redraw) {
      const a = data.acquire;
      const c = card("First 5 users at $10", "Research note: the next main focus. Faceless, repeatable short videos that give value for a comment and ask for a setup call.");
      c.append(el("p", "sub", a.goal), el("p", "sub", a.thesis));
      c.append(el("h2", null, "The 6-beat storyboard (every video)"), table(["Beat", "What goes on screen"], a.beats));
      c.append(el("h2", null, "No-camera formats"), table(["Format", "How it works"], a.formats));
      c.append(el("h2", null, "What we give away"), table(["Offer", "Why"], a.offers));
      c.append(el("h2", null, "Funnel to track"), table(["Stage", "Action", "Note"], a.funnel));
      c.append(el("h2", null, "The 10-day test"), el("p", "sub", a.experiment));
      c.append(el("h2", null, "Risks and conflicts"), ...a.risks.map(r => el("p", "sub", "• " + r)));
      c.append(el("h2", null, "Open questions"), ...a.open.map(r => el("p", "sub", "• " + r)));
      c.append(el("h2", null, "Actions"), list(a.tasks, redraw));
      return c;
    },
    sys(redraw) { const c = card("Zero-to-Revenue: your checklist", "Setup that only you can do."); c.append(list(data.system, redraw)); return c; },
    sources(redraw) {
      const c = card("Where to get more jobs", "Scout already reads these automatically: Superteam Earn, GitHub's bounty label, Freelancer.com, Remotive and Himalayas (contract/freelance only). Everything below needs a login, so Scout can't read it - this is what unlocks more and bigger work.");
      c.append(list(data.sources_setup, redraw));
      c.append(el("p", "sub", "Checked and skipped: OpenStreetMap Overpass (blocked here), Nominatim (refuses automated bulk use), WeWorkRemotely (almost entirely full-time salaried roles, not one-off paid work)."));
      return c;
    },
    road() {
      const c = card("Roadmap", "Each phase ships tested before the next starts."); const l = el("div", "list");
      data.phases.forEach(([n, name, what, st]) => { const it = el("div", "item"); add(it, add(el("div", "row"), el("b", null, n + " · " + name), pill({ done: "Complete", now: "Now", next: "Next", later: "Later" }[st], st === "done" ? "ok" : st === "now" ? "gold" : "")), el("div", "sub", what)); l.append(it); });
      c.append(l); return c;
    },
    year() {
      const c = card("12-month plan", "Targets, not forecasts. Each stage has a gate: miss it and we fix before scaling.");
      const chart = el("div", "list"); let cum = 0;
      data.year.forEach((v, i) => { cum += v; const r = el("div", "yr"); const bar = el("i"); bar.style.width = (v / 15 * 100) + "%"; add(r, el("span", null, "M" + (i + 1)), bar, el("b", null, "$" + v + "k · total $" + cum.toFixed(1) + "k")); chart.append(r); });
      c.append(chart, table(["Months", "Engine", "Target / month", "Gate to advance"], data.stages));
      c.append(el("h2", null, "The ladder"), el("p", "sub", "One customer, four tiers. Prices are hypotheses except BuildFlow's own."), table(["Tier", "Price", "Why"], data.ladder));
      c.append(el("p", "sub", "Honest maths: at $50/month, 100 contractors is $5,000/month, so the subscription alone will not reach $100k. Stacking setups and retainers on the same contractors is what changes the total. A realistic year-one range with 30 clients is roughly $60-85k."));
      return c;
    },
    cmd() {
      const c = card("Commands", "Three places to give instructions."); 
      c.append(el("h2", null, "Ask any Claude chat (connector, read-only)"), table(["Say", "What happens"], data.commands.ask),
        el("h2", null, "Claude Code slash commands (this coding session)"), table(["Command", "What it does"], data.commands.slash));
      return c;
    },
    app() {
      const c = card("Get the app", "One app, same login, same data on every device. It works live and locally.");
      const inst = el("div", "item"); inst.append(el("div", "t", "Install on this device"));
      if (Z.installEvent) inst.append(btn("Install now", "gold", async () => { Z.installEvent.prompt(); await Z.installEvent.userChoice; }));
      else inst.append(el("p", "sub", "Your browser has not offered install yet. On a phone: Chrome menu, Install app (or Add to Home screen). iPhone: Share, Add to Home Screen. On a computer: the install icon at the right of the address bar."));
      c.append(inst);
      const steps = [["Live (any device)", "Open " + (data.live_url || location.origin) + ", sign in, install it. Works anywhere there is internet."],
        ["Local (your computer)", "Runs the same app on your machine, against the same database, with the same login. Steps below."],
        ["Android APK (later)", "The installed app can be wrapped as an APK with PWABuilder or Bubblewrap. Needs the final HTTPS address and a signing key you keep and back up."]];
      steps.forEach(([t, d]) => c.append(add(el("div", "item"), el("div", "t", t), el("div", "sub", d))));
      const loc = el("div", "item"); loc.append(el("div", "t", "Local mode, step by step"));
      [["1. Get the code", "git clone https://github.com/anjuneedham/Zero-to-revenue-.git && cd Zero-to-revenue-"], ["2. Install", "pip install -r requirements.txt"],
       ["3. Add your settings", "copy .env.example to .env.local, then set DATABASE_URL (Neon console > Connection string), OWNER_WALLET_ADDRESS and OWNER_WALLET_CHAIN_IDS"],
       ["4. Start", "python scripts/run_local.py"]].forEach(([a, b]) => { loc.append(el("div", "sub", a)); loc.append(mono(b)); });
      loc.append(el("p", "sub", "It opens http://127.0.0.1:8080 and shows a LOCAL badge. Never put your keys or passwords anywhere except .env.local, which git ignores."));
      c.append(loc); return c;
    },
  };

  Z.pages.plan = {
    title: "Game plan", sub: "Where we are, what blocks launch, and where we're going", icon: "plan",
    async render(root) {
      if (!data) data = await (await fetch("/data/plan.json")).json();
      ticks = (await Z.api("/api/plan")).ticks;
      const wrap = el("div", "list"); const tabs = el("div", "tabs"); tabs.setAttribute("role", "tablist"); const body = el("div");
      const draw = () => {
        tabs.replaceChildren(...TABS.map(([k, l]) => { const b = el("button", null, l); b.type = "button"; b.setAttribute("role", "tab"); b.setAttribute("aria-selected", tab === k); b.onclick = () => { tab = k; draw(); }; return b; }));
        body.replaceChildren(panels[tab](draw));
      };
      draw(); add(wrap, tabs, body); root.append(wrap);
    },
  };
})();
