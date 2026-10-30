# Go / no-go checklist: before ANY real money

Copy this into a dated file (e.g. `docs/trading/go-no-go-YYYY-MM-DD.md`), fill it with real numbers from logs, and sign it. **Every box must be checked. One unchecked box = NO-GO.** Do not edit thresholds after seeing results; if you tighten them, write down why. Claude fills in facts; Jay makes the decision.

Strategy / bot name and version (commit hash): ______   Market(s) / timeframe: ______   Date: ______

## A. Hypothesis and honesty
- [ ] Hypothesis, rationale and "what would prove me wrong" were written **before** testing.
- [ ] I can state why this edge should exist (and for synthetics, why a random process would allow it), or I accept that the evidence is purely statistical and demand stronger proof.
- [ ] Number of strategy variants and parameter sets tried: ____ (all are counted in the multiple-testing view).

## B. Data and backtest quality
- [ ] Data source, period, gaps and timeframe documented; no look-ahead; no survivorship issues.
- [ ] Costs included: spread, commission, swap, slippage, lot limits, stop-level/freeze rules.
- [ ] Backtest trade count: ____ (target >= 200 total, >= 100 out-of-sample).
- [ ] Final holdout (>= 30%) stayed **sealed** until the last evaluation and was used **once**.

## C. Out-of-sample proof
- [ ] Walk-forward done (windows: ______); OOS results reported separately.
- [ ] OOS expectancy per trade (after costs) > 0 with bootstrap 95% CI lower bound > 0: ______
- [ ] OOS profit factor >= 1.3 after costs: ______   OOS Sharpe (stated method): ______
- [ ] Parameter robustness: +/-20-30% changes do not collapse results.
- [ ] Monte Carlo / random-entry comparison shows the result is not within the range of luck.
- [ ] Performance holds on at least one other symbol/period or regime (or I accept single-market risk explicitly).

## D. Risk rules (hard, automated, tested)
- [ ] Risk per trade <= 1% (<= 0.5% for first live phase): ______
- [ ] Daily loss limit set and tested: ______
- [ ] **Hard max-drawdown kill-switch** set (default 10%, ceiling 20%): ______ and verified to stop trading in a test.
- [ ] Worst OOS drawdown ______ <= half the kill-switch level.
- [ ] Maximum simultaneous open risk <= 3%: ______
- [ ] Failure handling tested: platform disconnect, rejected orders, requotes, weekend/maintenance gaps.

## E. Paper trading
- [ ] Demo run lasted **>= 8 weeks AND >= 100 trades**; dates: ______  trades: ____
- [ ] Final code version, **no parameter changes** during the run.
- [ ] Journal complete (entry, exit, size, reason, cost, screenshot/log) and reconciled to platform statements.
- [ ] Paper results are inside the out-of-sample / Monte Carlo band; if worse, I treat it as NO-GO and investigate.

## F. Operations and safety
- [ ] No keys or tokens in the repo, chat, or logs; live mode is a deliberate human toggle, off by default.
- [ ] Monitoring and alerts exist (daily summary, kill-switch alert); I know how to stop the bot in under a minute.
- [ ] I can lose the entire amount I put in without hardship; amount at risk: ______ (and it is **not** rent, food, tax or business-reserve money).
- [ ] I have read the broker/platform terms and understand leverage, margin calls and withdrawal rules.

## G. Decision
- [ ] **GO to micro-live** (smallest size, 4+ weeks, same limits). Signed: ______  Date: ______
- [ ] **NO-GO**: reason and what evidence is needed to re-review: ______

Scale-up is a separate review after micro-live. Profits go to `investing-plan` rules, not back into more risk by default.
