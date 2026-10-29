-- Phase 6 (Trading workspace): strategy research records and RESEARCH-ONLY run results.
-- SAFETY BY CONSTRUCTION: there is no 'live' value in any mode or status list, so a live result cannot be stored here, and nothing in
-- this system places orders. Backtest, out-of-sample, walk-forward and paper results are separate modes and are never combined.
-- Rollback: database/rollback/012_trading_research_down.sql (manual).
CREATE TABLE trading_strategies (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  name TEXT NOT NULL, hypothesis TEXT, instrument TEXT,
  status TEXT NOT NULL DEFAULT 'idea' CHECK (status IN ('idea','researching','backtesting','validating','paper','rejected','retired')),
  data_notes TEXT, risk_notes TEXT, failure_conditions TEXT,
  max_drawdown_limit_pct NUMERIC(8,2) CHECK (max_drawdown_limit_pct IS NULL OR (max_drawdown_limit_pct > 0 AND max_drawdown_limit_pct <= 100)),
  min_trades INTEGER CHECK (min_trades IS NULL OR min_trades > 0),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX trading_strategies_business ON trading_strategies(business_id, status);

CREATE TABLE trading_runs (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id), strategy_id TEXT NOT NULL REFERENCES trading_strategies(id),
  mode TEXT NOT NULL CHECK (mode IN ('backtest','out_of_sample','walk_forward','paper')),
  period_start TEXT, period_end TEXT, trades INTEGER CHECK (trades IS NULL OR trades >= 0),
  net_return_pct NUMERIC(12,4), max_drawdown_pct NUMERIC(8,2) CHECK (max_drawdown_pct IS NULL OR (max_drawdown_pct >= 0 AND max_drawdown_pct <= 100)),
  costs_included INTEGER CHECK (costs_included IS NULL OR costs_included IN (0,1)), cost_bps NUMERIC(10,2) CHECK (cost_bps IS NULL OR cost_bps >= 0),
  slippage_bps NUMERIC(10,2) CHECK (slippage_bps IS NULL OR slippage_bps >= 0),
  data_source TEXT, params TEXT, notes TEXT, created_at TEXT NOT NULL
);
CREATE INDEX trading_runs_strategy ON trading_runs(strategy_id, mode);
