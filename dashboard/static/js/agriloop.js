// Agriloop workspace (Phase 4): marketplace supply, demand, matching, deals. Data comes from /api/founder/workspace/agriloop.
(function () {
  const { el, add, pill, btn, card, fmt, nice } = Z;
  const SLUG = "agriloop", TABS = [["overview", "Overview"], ["market", "Supply & demand"], ["matches", "Matches"], ["deals", "Deals"], ["people", "People"], ["notes", "Notes"]];
  const post = (path, body) => Z.api("/api/founder/" + path, "POST", body || {});
  const bad = s => s && s.error;
  let W = null, tab = Z.store.get("z2r_ag_tab") || "overview";
  const money = (v, c) => (v == null ? "n/a" : fmt.num(v, 2) + (c ? " " + c : ""));
  const parties = role => (W.marketplace.parties || []).filter(p => p.role === role).map(p => [p.id, p.name]);

  function overview(root) {
    Z.ws.overview(root, W, SLUG);
    const m = W.marketplace; if (bad(m)) { root.append(Z.ws.secErr("Marketplace")); return; }
    const c = card("Marketplace health", "Counts of what you recorded. Not a measure of real-world liquidity until the data is complete.");
    const tiles = el("div", "tiles");
    add(tiles, Z.ws.tile("Farmers (active)", m.funnel.farmer.active + " / " + Object.values(m.funnel.farmer).reduce((a, b) => a + b, 0)), Z.ws.tile("Buyers (active)", m.funnel.buyer.active + " / " + Object.values(m.funnel.buyer).reduce((a, b) => a + b, 0)),
      Z.ws.tile("Open listings", m.listings.filter(x => x.status === "open").length), Z.ws.tile("Open buyer requests", m.demand.filter(x => x.status === "open").length),
      Z.ws.tile("Suggested matches", m.matches.length), Z.ws.tile("Completed deals", m.transaction_summary.by_status.completed), Z.ws.tile("Repeat buyers", m.repeat_buyers, m.buyers_with_completed + " buyer(s) with a completed deal"));
    c.append(tiles); root.append(c);
  }

  const PARTY = () => [["role", "Role", "select", [["farmer", "Farmer"], ["buyer", "Buyer"]], true], ["name", "Name", "text", null, true], ["location", "Parish / location", "text"], ["contact", "Contact (phone/WhatsApp)", "text"],
    ["produce", "Produce / needs", "text"], ["source", "How we found them", "text"], ["status", "Stage", "select", [["lead", "Lead"], ["onboarded", "Onboarded"], ["active", "Active"], ["churned", "Churned"]]]];
  function market(root) {
    const m = W.marketplace; if (bad(m)) { root.append(Z.ws.secErr("Supply & demand")); return; }
    const L = card("Liquidity by product", "Open listings vs open buyer requests (counts; units differ).");
    if (!m.liquidity.length) L.append(Z.none("Nothing recorded yet", "Add a farmer, then a listing; add a buyer, then a request."));
    m.liquidity.forEach(p => L.append(el("p", null, `${p.product}: ${p.supply} supply · ${p.demand} demand · ${p.gap}`)));
    root.append(L);
    const lst = card("Supply (farmer listings)");
    lst.append(Z.add(el("div", "row"), parties("farmer").length ? btn("Add listing", "gold small", async () => Z.formDialog("Add listing", [["party_id", "Farmer", "select", parties("farmer"), true], ["product", "Product", "text", null, true], ["quantity", "Quantity", "num"], ["unit", "Unit (kg, lb, crate)", "text"], ["price", "Price per unit", "num"], ["currency", "Currency (JMD, USD)", "text"], ["location", "Location", "text"], ["available_from", "Available from", "date"]], b => post("businesses/agriloop/market-listings", b))) : el("span", "sub", "Add a farmer first (People tab).")));
    if (!m.listings.length) lst.append(Z.none("No listings"));
    m.listings.forEach(x => { const it = el("div", "item"); add(it, el("div", "t", x.product + (x.quantity ? " · " + fmt.num(x.quantity, 1) + " " + (x.unit || "") : "")), el("p", "sub", (x.party_name || "?") + (x.price != null ? " · " + money(x.price, x.currency) + "/" + (x.unit || "unit") : " · no price") + (x.location ? " · " + x.location : "")),
      Z.add(el("div", "meta"), pill(nice(x.status), x.status === "open" ? "ok" : "")), x.status === "open" ? Z.add(el("div", "row"), btn("Close", "ghost small", async () => { await post("market-listings/" + x.id, { status: "closed" }); await Z.rerender(); })) : null); lst.append(it); });
    root.append(lst);
    const dem = card("Demand (buyer requests)");
    dem.append(Z.add(el("div", "row"), parties("buyer").length ? btn("Add request", "gold small", async () => Z.formDialog("Add buyer request", [["party_id", "Buyer", "select", parties("buyer"), true], ["product", "Product", "text", null, true], ["quantity", "Quantity", "num"], ["unit", "Unit", "text"], ["max_price", "Max price per unit", "num"], ["currency", "Currency", "text"], ["location", "Location", "text"], ["needed_by", "Needed by", "date"]], b => post("businesses/agriloop/market-demand", b))) : el("span", "sub", "Add a buyer first (People tab).")));
    if (!m.demand.length) dem.append(Z.none("No buyer requests"));
    m.demand.forEach(x => { const it = el("div", "item"); add(it, el("div", "t", x.product + (x.quantity ? " · " + fmt.num(x.quantity, 1) + " " + (x.unit || "") : "")), el("p", "sub", (x.party_name || "?") + (x.max_price != null ? " · up to " + money(x.max_price, x.currency) : " · no max price") + (x.needed_by ? " · by " + Z.ws.day(x.needed_by) : "")),
      Z.add(el("div", "meta"), pill(nice(x.status), x.status === "open" ? "ok" : "")), x.status === "open" ? Z.add(el("div", "row"), btn("Close", "ghost small", async () => { await post("market-demand/" + x.id, { status: "closed" }); await Z.rerender(); })) : null); dem.append(it); });
    root.append(dem);
  }

  function matches(root) {
    const m = W.marketplace; if (bad(m)) { root.append(Z.ws.secErr("Marketplace")); return; }
    const c = card("Suggested matches", "INFERENCES from your recorded data (same product, no known location or price conflict). Confirm with both sides; unknowns are listed.");
    if (!m.matches.length) c.append(Z.none("No suggested matches", "Needs an open listing and an open request for the same product."));
    m.matches.forEach(x => { const it = el("div", "item"); add(it, el("div", "t", `${x.product}: ${x.farmer || "?"} → ${x.buyer || "?"}`), Z.add(el("div", "meta"), pill("inference"), pill("score " + x.score)),
      el("p", "sub", "Because: " + x.why.join("; ")), x.unknown.length ? el("p", "flags", "Unknown: " + x.unknown.join("; ")) : null,
      Z.add(el("div", "row"), btn("Record proposed deal", "gold small", async () => { await post("businesses/agriloop/market-transactions", { listing_id: x.listing_id, demand_id: x.demand_id, status: "proposed" }); Z.toast("Deal recorded as proposed", "ok"); await Z.rerender(); }))); c.append(it); });
    root.append(c);
  }

  function deals(root) {
    const m = W.marketplace; if (bad(m)) { root.append(Z.ws.secErr("Marketplace")); return; }
    const s = m.transaction_summary, c = card("Deals", s.note);
    const tiles = el("div", "tiles"); Object.entries(s.by_status).forEach(([k, v]) => tiles.append(Z.ws.tile(nice(k), v))); c.append(tiles);
    s.completed_by_currency.forEach(x => c.append(el("p", null, `Completed value: ${fmt.num(x.amount, 2)} ${x.currency} across ${x.count} deal(s)`)));
    if (s.completed_without_value) c.append(el("p", "flags", s.completed_without_value + " completed deal(s) have no amount/currency and are not valued."));
    if (!m.transactions.length) c.append(Z.none("No deals yet", "Record a proposed deal from a suggested match, or add one manually."));
    m.transactions.forEach(t => { const it = el("div", "item"); add(it, el("div", "t", (t.quantity ? fmt.num(t.quantity, 1) + " " + (t.unit || "") + " · " : "") + money(t.amount, t.currency)), Z.add(el("div", "meta"), pill(nice(t.status), t.status === "completed" ? "ok" : t.status === "cancelled" ? "bad" : "warn")));
      if (t.status === "proposed" || t.status === "agreed") it.append(Z.add(el("div", "row"), btn("Update", "ghost small", async () => Z.formDialog("Update deal", [["status", "Status", "select", [["proposed", "Proposed"], ["agreed", "Agreed"], ["completed", "Completed"], ["cancelled", "Cancelled"]]], ["quantity", "Quantity", "num"], ["unit", "Unit", "text"], ["amount", "Total amount", "num"], ["currency", "Currency", "text"]], b => post("market-transactions/" + t.id, b), t)))); c.append(it); });
    root.append(c);
  }

  function people(root) {
    const m = W.marketplace; if (bad(m)) { root.append(Z.ws.secErr("Marketplace")); return; }
    const c = card("Farmers and buyers", "Acquisition funnel: lead, onboarded, active, churned.");
    ["farmer", "buyer"].forEach(r => { const f = m.funnel[r]; c.append(el("p", null, `${nice(r)}s: ${f.lead} lead · ${f.onboarded} onboarded · ${f.active} active · ${f.churned} churned`)); });
    c.append(Z.add(el("div", "row"), btn("Add farmer or buyer", "gold small", async () => Z.formDialog("Add farmer or buyer", PARTY(), b => post("businesses/agriloop/market-parties", b)))));
    if (!m.parties.length) c.append(Z.none("Nobody recorded yet"));
    m.parties.forEach(p => { const it = el("div", "item"); add(it, el("div", "t", p.name), Z.add(el("div", "meta"), pill(nice(p.role), "royal"), pill(nice(p.status), p.status === "active" ? "ok" : p.status === "churned" ? "bad" : ""), p.location ? pill(p.location) : null),
      p.produce ? el("p", "sub", p.produce) : null, Z.add(el("div", "row"), btn("Update", "ghost small", async () => Z.formDialog("Update", PARTY(), b => post("market-parties/" + p.id, b), p)))); c.append(it); });
    root.append(c);
  }

  Z.pages.agriloop = {
    title: "Agriloop", sub: "Priority 2 · marketplace supply, demand and matching", icon: "plan",
    async render(root) {
      W = await Z.api("/api/founder/workspace/" + SLUG);
      const wrap = el("div", "list"), tabs = el("div", "tabs"); tabs.setAttribute("role", "tablist");
      TABS.forEach(([k, label]) => { const b = el("button", null, label); b.type = "button"; b.setAttribute("role", "tab"); b.setAttribute("aria-selected", String(k === tab)); b.onclick = () => { tab = k; Z.store.set("z2r_ag_tab", k); Z.rerender(); }; tabs.append(b); });
      wrap.append(tabs);
      if (tab === "notes") Z.ws.notes(wrap, W, SLUG); else ({ overview, market, matches, deals, people }[tab] || overview)(wrap);
      root.append(wrap);
    },
  };
})();
