-- Manual rollback for 009 (runner is forward-only). Loses the rows in these tables.
DROP TABLE IF EXISTS feedback_items;
DROP TABLE IF EXISTS content_items;
