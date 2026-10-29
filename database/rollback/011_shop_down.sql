-- Manual rollback for 011 (runner is forward-only). Loses the rows in these tables; the fashion description edit is not reverted.
DROP TABLE IF EXISTS shop_campaigns;
DROP TABLE IF EXISTS shop_sales;
DROP TABLE IF EXISTS shop_products;
