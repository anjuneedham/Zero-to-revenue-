-- Manual rollback for 010 (runner is forward-only). Loses the rows in these tables.
DROP TABLE IF EXISTS market_transactions;
DROP TABLE IF EXISTS market_demand;
DROP TABLE IF EXISTS market_listings;
DROP TABLE IF EXISTS market_parties;
