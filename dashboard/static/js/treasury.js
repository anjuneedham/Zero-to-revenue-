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

      const pc = card("Payments you are owed", "Paste the transaction hash the payer sends you and Treasury checks it on-chain."); pc.classList.add("s12");
      const pl = el("div", "list");
      if (!pay.payments.length) pl.append(Z.empty("No payments expected yet", "They appear after you mark work as submitted."));
      pay.payments.forEach(p => {
        const it = el("div", "item"); add(it, el("div", "t", p.title || p.id), add(el("div", "meta"), pill(nice(p.status), Z.statusKind(p.status)),
          pill((p.expected_amount == null ? "?" : fmt.num(p.expected_amount, 2)) + " " + (p.asset || "") + " expected")));
        if (p.received_amount != null) {
          const ra = String(p.received_asset || ""), tok = ra.startsWith("TOKEN:"), label = tok ? "token " + ra.slice(6, 12) + "…" : ra;
          it.firstChild.nextSibling.append(pill("received " + fmt.num(p.received_amount) + " " + label, "ok"));
          if (!tok && /^(USD|USDC|USDT|DAI|USDG)$/i.test(p.asset || "")) it.append(el("div", "flags", "Paid in " + ra + ", not the " + p.asset + " you expected. Check the amount with the payer."));
          else if (tok) it.append(el("div", "sub", "A token arrived. Confirm it is the asset and amount you agreed."));
        }
        if (p.status !== "PAYMENT_VERIFIED" && t.chains.length) it.append(verifyForm(p, t.chains)); pl.append(it);
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
