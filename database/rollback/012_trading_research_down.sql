-- Manual rollback for 012 (runner is forward-only). Loses the rows in these tables.
DROP TABLE IF EXISTS trading_runs;
DROP TABLE IF EXISTS trading_strategies;
