# Trading (repo: `mq5`)

Evidence source: docs/master/HANDOFF.md (verified 28 Oct 2026). Claims not re-verified this chat are marked UNVERIFIED.

## Report
- MQL5 "Synthetic Edge EA" for Deriv synthetic indices; 20 files, last commit 26 Sep.
- Has an in-MT5 unit-test script. UNVERIFIED: not run (MT5 cannot run in this sandbox).
- No backtest results, paper-trading journal or statistics in the repo: **there is no evidence of an edge.**

## Audit
1. No backtest results committed.
2. No paper-trading journal or performance statistics.
3. No documented risk limits (max loss per trade/day, position sizing). UNVERIFIED: may exist in EA inputs.
4. Unit tests exist only inside MT5; no CI.
5. Synthetic indices are broker-generated; any edge must be shown on that data, not inferred from real-market results.

## Risks
- Real-capital loss from an unproven strategy (the dominant risk).
- Overfitting a backtest to one period; no out-of-sample split recorded.
- Broker/platform risk: Deriv synthetic indices are a single-counterparty product.
- Time sink: strategy tinkering displaces revenue ventures.

## MVP scope
In: reproducible backtest (fixed date range, in-sample/out-of-sample split, results exported to the repo), paper-trading journal (every trade logged), summary statistics (trades, win rate, expectancy, max drawdown, profit factor), written risk limits.
Out: any live capital, scaling, new strategies, copy-trading or selling signals.

## Roadmap
| Step | Work | Day |
|---|---|---|
| 1 | Run backtest in MT5 on a defined period; commit report and settings | Wed |
| 2 | Out-of-sample backtest on a later, unseen period | Wed |
| 3 | Start paper (demo) trading; daily journal entry | Wed, then daily |
| 4 | Weekly stats review; log to OS `metrics` | Sun |
| 5 | Go/no-go decision after >= 4 weeks of paper results | Week of 23 Nov at earliest |

## Growth plan
None. Trading is an evidence-gathering venture until the gate passes. No marketing, no signals product.

## Metrics
Paper trades/week, win rate, expectancy per trade, profit factor, max drawdown, deviation from backtest expectancy, weeks of continuous paper data.

## Acceptance criteria (gate to consider live capital)
- [ ] Backtest report committed, with in-sample and out-of-sample results
- [ ] >= 4 weeks of paper-trading journal with statistics
- [ ] Positive expectancy after costs on both backtest and paper, drawdown within a written limit
- [ ] Written risk rules (per-trade, daily, total loss caps) and a kill rule
- [ ] Founder explicit sign-off; until then **no live capital**
