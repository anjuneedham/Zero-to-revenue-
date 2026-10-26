(function () {
  const { el, add, pill, btn, card, fmt, nice } = Z;

  function verifyForm(p, chains) {
    const f = el("div", "form");
    const l1 = el("label", "f", "Chain"); const sel = el("select"); sel.id = "chain-" + p.id; sel.setAttribute("aria-label", "Chain");
    chains.forEach(c => { const o = el("option", null, c.name); o.value = c.chain_id; sel.append(o); }); l1.append(sel);
    const l2 = el("label", "f", "Transaction hash"); const tx = el("input"); tx.id = "tx-" + p.id; tx.placeholder = "0x…"; l2.append(tx);
    const b = btn("Verify on-chain", "gold small", async () => {
      const r = await Z.api("/api/payments/" + p.id + "/verify", "POST", { chain_id: sel.value, tx_hash: tx.value.trim() });
      Z.goal(r.amount + " " + r.asset + " verified"); await Z.rerender();
    });
    add(f, l1, l2, b); return f;
  }

  function linkRow(url) {
    const row = el("div", "row");
    const a = el("a", null, "Open the payment page"); a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer";
    add(row, a, btn("Copy link", "ghost small", () => Z.copy(url, "Payment link"), "copy"));
    return row;
  }

  function paypalForm(p) {
    const f = el("div", "form");
    p = { ...p, paypal_order_id: p.chain_id == null ? p.tx_hash : null };
    if (!p.paypal_order_id) {
      const reqBtn = btn("Request PayPal payment (card or bank transfer)", "gold small", async () => {
        try {
          const r = await Z.api(`/api/payments/${p.id}/paypal/request`, "POST", {});
          Z.toast("Payment link ready - send it to the client yourself", "ok");
          if (r.approval_link) add(f, linkRow(r.approval_link));
          reqBtn.disabled = true;
        } catch (e) { Z.toast(e.message, "bad"); }
      });
      f.append(reqBtn);
      return f;
    }
    const row = el("div", "row"); const code = el("code", "key", p.paypal_order_id); code.style.margin = "0";
    add(row, el("small", null, "PayPal order"), code, btn("Copy", "ghost small", () => Z.copy(p.paypal_order_id, "Order id"), "copy"));
    const linkBtn = btn("Get payment link", "ghost small", async () => {
      try {
        const r = await Z.api(`/api/payments/${p.id}/paypal/link`, "GET");
        linkBtn.replaceWith(linkRow(r.approval_link));
      } catch (e) { Z.toast(e.message, "bad"); }
    });
    const b = btn("Check if paid", "gold small", async () => {
      try { const r = await Z.api(`/api/payments/${p.id}/paypal/verify`, "POST", {}); Z.goal(r.amount + " " + r.asset + " verified"); await Z.rerender(); }
      catch (e) { Z.toast(e.message, "bad"); }
    });
    add(f, row, linkBtn, b); return f;
  }

  Z.verifyForm = verifyForm; Z.paypalForm = paypalForm;

  Z.pages.treasury = {
    title: "Treasury", sub: "Watches your wallet and verifies payments. Read-only.", icon: "treasury",
    async render(root) {
      const [t, pay] = await Promise.all([Z.api("/api/treasury/overview"), Z.api("/api/payments")]);
      const g = el("div", "grid");

      const top = el("section", "card hero s8");
      const head = el("div", "agent"); add(head, el("div", "shirt", "1"), el("h3", null, "Treasury"), el("div", "label", "Keeper · guards the money"),
        el("div", "sub", t.chains.some(c => c.checked_at) ? "Last check " + fmt.ago(t.chains.map(c => c.checked_at).filter(Boolean).sort().pop()) : "Has not checked yet"));
      top.append(head);
      if (t.address) {
        const row = el("div", "row"); const code = el("code", "key", t.address); code.style.margin = "0"; code.style.color = "var(--ink)";
        row.append(code, btn("Copy", "ghost small", () => Z.copy(t.address, "Address"), "copy")); top.append(row);
      } else top.append(el("p", "err", "OWNER_WALLET_ADDRESS is not set."));
      if (t.problem) top.append(el("p", "err", t.problem));
      top.append(add(el("div", "meta"), pill("Read-only", "ok"), pill("No signing", "ok"), pill("No spending", "ok"), pill(t.min_confirmations + " confirmations needed")));
      top.append(btn("Check wallet now", "gold", async () => {
        const r = await Z.api("/api/treasury/run", "POST");
        Z.toast(r.ran ? "Wallet checked on " + Object.keys(r.balances).length + " chains" + (r.errors.length ? ", " + r.errors.length + " failed" : "") : "Not run: " + r.reason, r.errors && r.errors.length ? "bad" : "ok"); await Z.rerender();
      }, "treasury"));
      g.append(top);

      const rev = card("Verified revenue", "Only fully verified receipts with a USD price"); rev.classList.add("s4");
      const unpriced = t.ledger.filter(e => e.type === "receipt" && e.status === "VERIFIED" && e.usd_value == null).length;
      add(rev, el("div", "stat", fmt.usd(t.revenue_usd)), el("p", "sub", "A wallet-to-wallet transfer, loan, promised or estimated payment never counts."));
      if (unpriced) rev.append(el("p", "flags", unpriced + " verified receipt(s) have no USD price yet (native coins and unconfirmed tokens are not valued), so they are not counted here."));
      g.append(rev);

      const calc = card("Payment calculator", "Convert any amount you were paid - crypto or fiat - into USD or JMD. Not tied to a job; use it for any online payment."); calc.classList.add("s12");
      const rr = await Z.api("/api/rates");
      const CODES = Object.keys(rr.crypto_usd); const FIATS = ["USD", ...Object.keys(rr.fiat_per_usd)];
      const form = el("div", "form");
      const l1 = el("label", "f", "Amount"); const amt = el("input"); amt.type = "number"; amt.step = "any"; amt.value = "1"; amt.id = "calc-amt"; l1.append(amt);
      const l2 = el("label", "f", "You received"); const from = el("select"); from.id = "calc-from";
      CODES.forEach(c => { const o = el("option", c, c); o.value = c; from.append(o); });
      const customOpt = el("option", null, "Other (enter rate)"); customOpt.value = "CUSTOM"; from.append(customOpt); l2.append(from);
      const l3 = el("label", "f", "Rate to USD (only for “Other”)"); const customRate = el("input"); customRate.type = "number"; customRate.step = "any";
      customRate.placeholder = "e.g. 1 unit = $X"; customRate.id = "calc-rate"; customRate.disabled = true; l3.append(customRate);
      const l4 = el("label", "f", "Show in"); const to = el("select"); to.id = "calc-to"; FIATS.forEach(c => { const o = el("option", c, c); o.value = c; to.append(o); }); l4.append(to);
      const out = el("div"); add(out, el("div", "label", "Result"), el("div", "stat", "-"));
      from.onchange = () => { customRate.disabled = from.value !== "CUSTOM"; };
      const compute = () => {
        const a = parseFloat(amt.value) || 0;
        const usdRate = from.value === "CUSTOM" ? (parseFloat(customRate.value) || 0) : (rr.crypto_usd[from.value] || 0);
        const usd = a * usdRate;
        const target = to.value === "USD" ? 1 : (rr.fiat_per_usd[to.value] || 0);
        Z.text(out.lastChild, target ? fmt.usd(usd * target).replace("$", "") + " " + to.value : "no rate available");
        out.lastChild.title = `1 ${from.value === "CUSTOM" ? "unit" : from.value} ≈ $${usdRate} USD`;
      };
      [amt, from, customRate, to].forEach(e => e.addEventListener("input", compute));
      compute();
      add(form, l1, l2, l3, l4); calc.append(form, out);
      calc.append(el("p", "sub", rr.as_of ? "Rates as of " + fmt.when(rr.as_of) + (rr.stale ? " (could not refresh just now; showing the last good rates)" : "") + ". Reference only - never counted as verified revenue on its own." : "Rates are not available right now."));
      g.append(calc);

      const ch = card("Chains", "Native-coin balances on the chains you allow"); ch.classList.add("s12");
      const cols = el("div", "cols");
      if (!t.chains.length) cols.append(Z.empty("No chains configured", "Set OWNER_WALLET_CHAIN_IDS in Vercel."));
      t.chains.forEach(c => {
        const it = el("div", "item"); add(it, add(el("div", "row"), el("div", "t", c.name), pill(c.checked_at ? fmt.ago(c.checked_at) : "unchecked", c.checked_at ? "" : "warn")),
          el("div", "stat", c.balance == null ? "n/a" : fmt.num(c.balance, 5)), Z.spark(c.history));
        if (c.explorer && t.address) { const a = el("a", null, "View on explorer"); a.href = c.explorer + "/address/" + t.address; a.target = "_blank"; a.rel = "noopener noreferrer"; it.append(a); }
        cols.append(it);
      });
      ch.append(cols); g.append(ch);

      const pc = card("Payments you are owed", "Paste the transaction hash the payer sends you to check it on-chain, or request a PayPal payment link for card/bank transfer."); pc.classList.add("s12");
      const addForm = el("div", "form");
      const t1 = el("input"); t1.placeholder = "What's this for? (e.g. BuildFlow subscription - Acme Co)";
      const t2 = el("input"); t2.placeholder = "Amount"; t2.type = "number"; t2.min = "0.01"; t2.step = "0.01";
      const t3 = el("input"); t3.placeholder = "Currency"; t3.value = "USD"; t3.style.maxWidth = "90px";
      const addBtn = btn("Add a payment you're owed", "gold small", async () => {
        try {
          await Z.api("/api/payments/manual", "POST", { title: t1.value.trim(), amount: t2.value, currency: t3.value.trim() || "USD" });
          Z.toast("Added - request PayPal or paste a tx hash below", "ok"); await Z.rerender();
        } catch (e) { Z.toast(e.message, "bad"); }
      });
      add(addForm, t1, t2, t3, addBtn); pc.append(addForm);
      const pl = el("div", "list");
      if (!pay.payments.length) pl.append(Z.empty("No payments expected yet", "Add one above, for work outside the automated pipeline (like a BuildFlow subscription), or they appear automatically after you mark Scout work as submitted."));
      pay.payments.forEach(p => {
        const it = el("div", "item"); add(it, el("div", "t", p.title || p.id), add(el("div", "meta"), pill(nice(p.status), Z.statusKind(p.status)),
          pill((p.expected_amount == null ? "?" : fmt.num(p.expected_amount, 2)) + " " + (p.asset || "") + " expected")));
        if (p.received_amount != null) {
          const ra = String(p.received_asset || ""), tok = ra.startsWith("TOKEN:"), label = tok ? "token " + ra.slice(6, 12) + "…" : ra;
          it.firstChild.nextSibling.append(pill("received " + fmt.num(p.received_amount) + " " + label, "ok"));
          if (!tok && /^(USD|USDC|USDT|DAI|USDG)$/i.test(p.asset || "")) it.append(el("div", "flags", "Paid in " + ra + ", not the " + p.asset + " you expected. Check the amount with the payer."));
          else if (tok) it.append(el("div", "sub", "A token arrived. Confirm it is the asset and amount you agreed."));
        }
        if (p.status !== "PAYMENT_VERIFIED") {
          if (t.chains.length) it.append(verifyForm(p, t.chains));
          if (t.paypal) it.append(paypalForm(p));
          else if (!t.chains.length) it.append(el("p", "sub", "No chains or PayPal configured yet."));
        }
        pl.append(it);
      });
      pc.append(pl); g.append(pc);

      const lg = card("Ledger", "Every verified receipt, with a link to the transaction"); lg.classList.add("s12");
      if (!t.ledger.length) lg.append(Z.empty("No ledger entries yet"));
      else { const w = el("div", "tablewrap"), tb = el("table"); const hr = el("tr"); ["Date", "Type", "Amount", "USD", "Status", "Transaction"].forEach(h => hr.append(el("th", null, h))); tb.append(hr);
        t.ledger.forEach(e => { const tr = el("tr"); const tx = el("td"); if (e.tx_url) { const a = el("a", null, e.transaction_hash.slice(0, 10) + "…"); a.href = e.tx_url; a.target = "_blank"; a.rel = "noopener noreferrer"; tx.append(a); }
          add(tr, el("td", null, fmt.when(e.date)), el("td", null, nice(e.type)), el("td", null, fmt.num(e.amount) + " " + (e.asset || "")), el("td", null, e.usd_value == null ? "no price" : fmt.usd(e.usd_value)), el("td", null, nice(e.status)), tx); tb.append(tr); });
        w.append(tb); lg.append(w); }
      g.append(lg); root.append(g);
    },
  };
})();
