-- Phase 5 (Fashion workspace): products/inventory, sales, campaigns. Additive, business-scoped, reusable by other shops.
-- Money carries its own currency and is never summed across currencies. Unknown stays NULL.
-- Rollback: database/rollback/011_shop_down.sql (manual).
CREATE TABLE shop_products (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  name TEXT NOT NULL, category TEXT, sku TEXT,
  status TEXT NOT NULL DEFAULT 'idea' CHECK (status IN ('idea','sampling','ready','live','discontinued')),
  unit_cost NUMERIC(14,2) CHECK (unit_cost IS NULL OR unit_cost >= 0), price NUMERIC(14,2) CHECK (price IS NULL OR price >= 0), currency TEXT,
  stock_qty INTEGER CHECK (stock_qty IS NULL OR stock_qty >= 0), reorder_point INTEGER CHECK (reorder_point IS NULL OR reorder_point >= 0),
  notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX shop_products_business ON shop_products(business_id, status);

CREATE TABLE shop_sales (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id), product_id TEXT REFERENCES shop_products(id),
  quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0), revenue NUMERIC(14,2) CHECK (revenue IS NULL OR revenue >= 0), currency TEXT,
  channel TEXT, customer_ref TEXT, sold_at TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX shop_sales_business ON shop_sales(business_id, sold_at);

CREATE TABLE shop_campaigns (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  name TEXT NOT NULL, channel TEXT, status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','running','done','cancelled')),
  spend NUMERIC(14,2) CHECK (spend IS NULL OR spend >= 0), attributed_revenue NUMERIC(14,2) CHECK (attributed_revenue IS NULL OR attributed_revenue >= 0),
  orders INTEGER CHECK (orders IS NULL OR orders >= 0), currency TEXT, start_date TEXT, end_date TEXT, notes TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX shop_campaigns_business ON shop_campaigns(business_id, status);

-- The founder named the brand in the Phase 5 brief. Only replaces the Phase 1 placeholder text; the row's name/slug/id are unchanged.
UPDATE businesses SET description = 'Yaad n Abroad: "Pain into Art", Jamaican-inspired wear. Consumer / e-commerce brand (not SaaS).'
  WHERE slug = 'fashion' AND description LIKE '%not been confirmed%';
