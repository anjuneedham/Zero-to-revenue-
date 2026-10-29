-- Phase 4 (Agriloop workspace): marketplace parties, supply listings, buyer demand, transactions. Additive, business-scoped
-- (reusable by other marketplaces). Money is stored per row WITH its currency and is never summed across currencies.
-- Rollback: database/rollback/010_marketplace_down.sql (manual).
CREATE TABLE market_parties (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  role TEXT NOT NULL CHECK (role IN ('farmer','buyer')), name TEXT NOT NULL, location TEXT, contact TEXT, source TEXT, produce TEXT,
  status TEXT NOT NULL DEFAULT 'lead' CHECK (status IN ('lead','onboarded','active','churned')), notes TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX market_parties_business ON market_parties(business_id, role, status);

CREATE TABLE market_listings (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id), party_id TEXT NOT NULL REFERENCES market_parties(id),
  product TEXT NOT NULL, quantity NUMERIC(14,3) CHECK (quantity IS NULL OR quantity > 0), unit TEXT,
  price NUMERIC(14,2) CHECK (price IS NULL OR price >= 0), currency TEXT, location TEXT, available_from TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','matched','closed','expired')),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX market_listings_business ON market_listings(business_id, status);

CREATE TABLE market_demand (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id), party_id TEXT NOT NULL REFERENCES market_parties(id),
  product TEXT NOT NULL, quantity NUMERIC(14,3) CHECK (quantity IS NULL OR quantity > 0), unit TEXT,
  max_price NUMERIC(14,2) CHECK (max_price IS NULL OR max_price >= 0), currency TEXT, location TEXT, needed_by TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','fulfilled','closed','expired')),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX market_demand_business ON market_demand(business_id, status);

CREATE TABLE market_transactions (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  listing_id TEXT REFERENCES market_listings(id), demand_id TEXT REFERENCES market_demand(id),
  quantity NUMERIC(14,3) CHECK (quantity IS NULL OR quantity > 0), unit TEXT,
  amount NUMERIC(14,2) CHECK (amount IS NULL OR amount >= 0), currency TEXT,
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','agreed','completed','cancelled')),
  occurred_at TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX market_transactions_business ON market_transactions(business_id, status);
