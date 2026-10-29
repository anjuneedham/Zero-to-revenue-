// Fashion workspace (Phase 5): consumer / e-commerce (products, margins, stock, sales, campaigns). Not SaaS metrics.
(function () {
  const { el, add, pill, btn, card, fmt, nice } = Z;
  const SLUG = "fashion", TABS = [["overview", "Overview"], ["products", "Products"], ["sales", "Sales"], ["campaigns", "Campaigns"], ["content", "Content"], ["customers", "Customers"], ["notes", "Notes"]];
  const post = (path, body) => Z.api("/api/founder/" + path, "POST", body || {});
  const bad = s => s && s.error;
  let W = null, tab = Z.store.get("z2r_fa_tab") || "overview";
  const m = (v, c) => (v == null ? "n/a" : fmt.num(v, 2) + (c ? " " + c : ""));

  const PRODUCT = () => [["name", "Product", "text", null, true], ["category", "Category (tee, hoodie, cap...)", "text"], ["sku", "SKU", "text"],
    ["status", "Stage", "select", [["idea", "Idea"], ["sampling", "Sampling"], ["ready", "Ready"], ["live", "Live"], ["discontinued", "Discontinued"]]],
    ["unit_cost", "Cost per unit", "num"], ["price", "Selling price", "num"], ["currency", "Currency (JMD, USD)", "text"], ["stock_qty", "Units in stock", "int"], ["reorder_point", "Reorder when stock is at or below", "int"]];

  function overview(root) {
    Z.ws.overview(root, W, SLUG);
    const s = W.shop; if (bad(s)) { root.append(Z.ws.secErr("Shop")); return; }
    const c = card("Shop health", "Only what you recorded. Margins need a cost and a price; revenue is per currency.");
    const t = el("div", "tiles");
    add(t, Z.ws.tile("Live products", s.product_counts.live), Z.ws.tile("In development", s.product_counts.idea + s.product_counts.sampling + s.product_counts.ready), Z.ws.tile("Orders logged", s.sales_summary.orders_total), Z.ws.tile("Repeat customers", s.sales_summary.repeat_customers, s.sales_summary.customers_identified + " identified"));
    s.sales_summary.by_currency.forEach(x => t.append(Z.ws.tile("Revenue " + x.currency, fmt.num(x.revenue, 2), "last 30 days " + fmt.num(x.last_30_days, 2) + " · avg order " + fmt.num(x.avg_order_value, 2))));
    s.inventory_value_at_cost.forEach(x => t.append(Z.ws.tile("Stock at cost " + x.currency, fmt.num(x.amount, 2))));
    c.append(t);
    s.attention.forEach(a => c.append(el("p", "flags", a.product + ": " + a.flag)));
    if (!s.attention.length) c.append(el("p", "sub", "No stock or margin warnings from the data you entered."));
    root.append(c);
  }

  function products(root) {
    const s = W.shop; if (bad(s)) { root.append(Z.ws.secErr("Products")); return; }
    const c = card("Products and inventory", "Margin = (price - cost) / price, shown only when both are recorded.");
    c.append(Z.add(el("div", "row"), btn("Add product", "gold small", async () => Z.formDialog("Add product", PRODUCT(), b => post("businesses/fashion/shop-products", b)))));
    if (!s.products.length) c.append(Z.none("No products yet", "Add each design, even at idea stage."));
    s.products.forEach(p => { const it = el("div", "item"); add(it, el("div", "t", p.name), Z.add(el("div", "meta"), pill(nice(p.status), p.status === "live" ? "ok" : ""), p.category ? pill(p.category) : null,
      p.stock_qty != null ? pill(p.stock_qty + " in stock", p.stock_flag ? "warn" : "") : pill("stock unknown")),
      el("p", "sub", `Price ${m(p.price, p.currency)} · cost ${m(p.unit_cost, p.currency)} · ` + (p.margin_pct != null ? `margin ${p.margin_pct}% (${fmt.num(p.margin_amount, 2)} each)` : "margin unknown (needs price and cost)")),
      p.stock_flag || p.margin_flag ? el("p", "flags", p.stock_flag || p.margin_flag) : null, Z.add(el("div", "row"), btn("Update", "ghost small", async () => Z.formDialog("Update product", PRODUCT(), b => post("shop-products/" + p.id, b), p)),
        btn("Log a sale", "ghost small", async () => Z.formDialog("Log a sale of " + p.name, [["quantity", "Units", "int"], ["revenue", "Total received", "num"], ["currency", "Currency", "text"], ["channel", "Channel (Instagram, WhatsApp, pop-up)", "text"], ["customer_ref", "Customer (name or handle, for repeat tracking)", "text"]],
          b => post("businesses/fashion/shop-sales", { ...b, product_id: p.id }), { currency: p.currency, revenue: p.price })))); c.append(it); });
    root.append(c);
  }

  function sales(root) {
    const s = W.shop; if (bad(s)) { root.append(Z.ws.secErr("Sales")); return; }
    const c = card("Sales", s.sales_summary.note);
    c.append(Z.add(el("div", "row"), btn("Log a sale", "gold small", async () => Z.formDialog("Log a sale", [["product_id", "Product (optional)", "select", [["", "Not specified"], ...s.products.map(p => [p.id, p.name])]], ["quantity", "Units", "int"], ["revenue", "Total received", "num"], ["currency", "Currency", "text"], ["channel", "Channel", "text"], ["customer_ref", "Customer", "text"]], b => post("businesses/fashion/shop-sales", b)))));
    if (s.sales_summary.unvalued_orders) c.append(el("p", "flags", s.sales_summary.unvalued_orders + " order(s) have no revenue or currency and are not valued."));
    if (!s.sales.length) c.append(Z.none("No sales logged yet"));
    s.sales.forEach(x => c.append(Z.add(el("div", "item"), el("div", "t", (x.product_name || "Order") + " · " + x.quantity + " unit(s) · " + m(x.revenue, x.currency)), el("p", "sub", [x.channel, x.customer_ref, Z.ws.day(x.sold_at)].filter(Boolean).join(" · ")))));
    root.append(c);
  }

  function campaigns(root) {
    const s = W.shop; if (bad(s)) { root.append(Z.ws.secErr("Campaigns")); return; }
    const FIELDS = [["name", "Campaign", "text", null, true], ["channel", "Channel", "text"], ["status", "Status", "select", [["planned", "Planned"], ["running", "Running"], ["done", "Done"], ["cancelled", "Cancelled"]]], ["spend", "Spend", "num"], ["attributed_revenue", "Revenue you attribute to it", "num"], ["orders", "Orders", "int"], ["currency", "Currency", "text"], ["start_date", "Start", "date"], ["end_date", "End", "date"]];
    const c = card("Campaigns", "ROAS is shown only when spend and attributed revenue are both recorded. Attribution is your judgement, not a platform report.");
    c.append(Z.add(el("div", "row"), btn("Add campaign", "gold small", async () => Z.formDialog("Add campaign", FIELDS, b => post("businesses/fashion/shop-campaigns", b)))));
    if (!s.campaigns.length) c.append(Z.none("No campaigns yet"));
    s.campaigns.forEach(x => c.append(Z.add(el("div", "item"), el("div", "t", x.name), Z.add(el("div", "meta"), pill(nice(x.status), x.status === "running" ? "royal" : ""), x.channel ? pill(x.channel) : null),
      el("p", "sub", `Spend ${m(x.spend, x.currency)} · attributed revenue ${m(x.attributed_revenue, x.currency)} · ` + (x.roas != null ? `ROAS ${x.roas}x` : "ROAS unknown") + (x.cost_per_order != null ? ` · ${fmt.num(x.cost_per_order, 2)} per order` : "")),
      Z.add(el("div", "row"), btn("Update", "ghost small", async () => Z.formDialog("Update campaign", FIELDS, b => post("shop-campaigns/" + x.id, b), x))))));
    root.append(c);
  }

  Z.pages.fashion = {
    title: "Fashion", sub: "Priority 3 · Yaad n Abroad: products, margins, sales, content", icon: "plan",
    async render(root) {
      W = await Z.api("/api/founder/workspace/" + SLUG);
      const wrap = el("div", "list"), tabs = el("div", "tabs"); tabs.setAttribute("role", "tablist");
      TABS.forEach(([k, label]) => { const b = el("button", null, label); b.type = "button"; b.setAttribute("role", "tab"); b.setAttribute("aria-selected", String(k === tab)); b.onclick = () => { tab = k; Z.store.set("z2r_fa_tab", k); Z.rerender(); }; tabs.append(b); });
      wrap.append(tabs);
      if (tab === "notes") Z.ws.notes(wrap, W, SLUG); else if (tab === "content") Z.ws.content(wrap, W, SLUG); else if (tab === "customers") Z.ws.feedback(wrap, W, SLUG);
      else ({ overview, products, sales, campaigns }[tab] || overview)(wrap);
      root.append(wrap);
    },
  };
})();
