# Trading (venture doc)
Repo `mq5` (MQL5 "Synthetic Edge EA", Deriv synthetic indices; 20 files; last commit 26 Sep) · stage: RESEARCH · priority 4.

## Report
An EA exists with an in-MT5 unit-test script. The repo has NO backtest results, paper journal or statistics: there is no evidence of an edge. MT5 cannot run in the Claude sandbox. *(handoff)*

## Risks
Capital loss; synthetic indices are algorithmic with no real-world edge to exploit; overfitting; leverage; OS policy forbids trading/spending/signing, and that stays.

## Scope: research only
Define the strategy in words, run the backtest on the founder's machine, keep a paper journal. No live account, no real capital, no OS integration beyond logging results.

## Roadmap
- [ ] Founder runs a documented MT5 Strategy Tester backtest (period, settings, report exported) and adds it to the repo
- [ ] Paper-trade (demo account) 30+ days with a daily journal
- [ ] Compute expectancy, max drawdown, trade count; write `RESULTS.md`
- [ ] Gate review: go-live only if edge persists out-of-sample, drawdown limit defined, and founder changes the OS policy in writing

## Metrics
backtest_trades, win_rate, expectancy_per_trade, max_drawdown_pct, paper_days. (Paper results are never revenue.)

## Acceptance criteria
RESULTS.md exists with out-of-sample statistics and a written verdict.
**Kill criterion:** negative expectancy after costs, or drawdown beyond the preset limit in paper → archive the venture.
