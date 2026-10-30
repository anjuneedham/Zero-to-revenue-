---
name: investing-plan
description: >-
  Profit-allocation rules and tracking for Jay's money: how venture and trading-bot profits flow
  through tax set-aside, reserves and reinvestment into a disciplined, diversified investing plan,
  with position sizing, rebalancing rules and a tracking spreadsheet. Use when Jay asks where profits
  should go, how to start investing, how much to keep as reserve, how to rebalance, or how to track a
  portfolio. Educational structure only, not licensed financial advice.
---

# Investing plan

Goal (priority 4): take profits from the ventures and the bot into a disciplined, diversified plan. **Today there may be no profit to allocate; this skill sets the rules so they exist before the money does.**

**Not financial, tax or legal advice.** Percentages below are *template defaults to adapt*, not recommendations for Jay's situation. Anything about Jamaican tax, registration, pension or investment products is **UNVERIFIED**: confirm with a licensed adviser, an accountant, and the relevant authority (e.g. Tax Administration Jamaica, the Financial Services Commission, the Jamaica Stock Exchange or a licensed dealer).

## Ask once (at the end of the session, not mid-way)

Monthly essential expenses, current cash and debts, income stability, time horizon, risk tolerance, whether Jay has dependants, and any existing investments/pension. Never invent these.

## Rule 1: the profit waterfall (order matters)

Apply to **net cash profit actually received** (not revenue, not paper gains), each month:

| Step | Bucket | Template rule | Why |
|---|---|---|---|
| 1 | **Tax set-aside** | Move a fixed % into a separate account immediately (template 20-30%; confirm the real figure for a Jamaican sole trader, including statutory contributions and GCT if registered) | Tax is a bill, not a surprise |
| 2 | **Business reserve** | Build to 3-6 months of business costs, then stop topping up | Survive slow months without selling investments |
| 3 | **Personal emergency fund** | 3-6 months of personal essentials, in cash/near-cash | Keeps investing from being forced to sell |
| 4 | **High-interest debt** | Pay down anything costing more than a realistic investment return | A guaranteed return beats a hoped-for one |
| 5 | **Reinvest in ventures** | Capped % (template up to 30-50% early on) toward the venture with the best *measured* return (see `hormozi-lens`, `saas-metrics-coach`) | Avoids starving growth; the cap avoids over-concentration |
| 6 | **Long-term investing** | Remainder, on a schedule (see Rule 2) | Compounding needs consistency |

Trading-bot profits: **only withdraw profits, never principal, and only after the go/no-go in `trading-lab`.** Template: sweep a fixed share (e.g. half) of realised monthly profit into the waterfall; leave the rest as buffer toward the drawdown limit. Never top up a losing bot from the investing bucket.

## Rule 2: build the portfolio (keep it boring)

- **Core**: broad, low-cost diversified funds across geographies and asset classes (equity index funds/ETFs, bonds or government securities, cash). Check what is actually accessible to a Jamaica-resident (brokers, currency, fees, withholding tax, deposit insurance); that varies and is **UNVERIFIED**.
- **Satellite** (optional, <= 10% of the portfolio): individual stocks or ventures you can describe and monitor. Never put money you need within 3-5 years into volatile assets.
- **Concentration limits**: no single stock > 5% of the portfolio, no single sector > 25%, and your own ventures count as exposure (they are already a large, undiversified bet). Do not add a crypto/trading position on top without sizing it as a separate "speculation" slice <= 5%.
- **Costs**: favour low fees; check spreads, FX conversion and withdrawal charges before buying anything.
- **Position sizing** for any single holding: size by the loss you can accept if it goes to zero (`position-sizer` for the maths).

## Rule 3: rebalance by rules, not feelings

Set target weights once (e.g. 70% equity funds / 20% bonds / 10% cash is only an illustration). Rebalance when a bucket drifts by more than **5 percentage points** from target, or once a year, whichever comes first; use new contributions to fix drift before selling (it avoids tax and fees). Do not rebalance because of headlines. Record the reason for every change in the log.

## Rule 4: track it (copy the templates in `assets/`)

- `assets/holdings-template.csv`: one row per holding (account, asset, units, cost basis, price, currency, target weight).
- `assets/contributions-log-template.csv`: every deposit, withdrawal, fee, dividend, tax set-aside, and rebalance, with a note.
- Monthly 15-minute review: net worth, savings rate, drift from targets, fees paid, tax set-aside balance. Quarterly: re-check the waterfall percentages and reserve targets. Use `portfolio-analytics` for return/risk metrics, `financial-analyst` for budget and ratio views, `cfo-advisor` for runway of the ventures.
- Sheets formulas: weight = value / total; drift = weight - target; rebalance amount = (target - weight) x total.

## Guardrails

- No leverage, margin, options or "guaranteed returns" in the core plan. Treat any scheme promising high, guaranteed returns as a red flag.
- Don't invest money that is earmarked for tax, reserves, or the trading kill-switch capital.
- Don't recommend specific securities or promise returns. Explain concepts, trade-offs and the process; let Jay and a licensed professional choose products.

## Output format

Current waterfall status (with unknowns marked), the next monthly action, any rule breached, and a **needs verification** list (tax figures, product availability, fees).
