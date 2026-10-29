"""Growth funnels from the records already in the database (Phase 9). Read-only, deterministic, no model, one business at a time.

A stage with no recorded data is `null` (shown as "not tracked"), never 0. A conversion rate is computed only over rows that have
BOTH numbers, and always carries its sample size and a small-sample flag. Trading is research-only and has no growth funnel.
"""

from decimal import Decimal

from core import founder

SMALL = 30  # below this many observations a rate is flagged as noise


def _n(v):
    return float(v) if isinstance(v, Decimal) else v


def _stage(key, label, value, note=None):
    return {"key": key, "label": label, "value": _n(value), "note": note}


def _rate(key, label, num, den, n, note=None):
    ok = den is not None and den > 0 and num is not None
    return {"key": key, "label": label, "rate_pct": round(num / den * 100, 1) if ok else None, "numerator": _n(num), "denominator": _n(den), "sample": n,
            "small_sample": bool(ok and n < SMALL), "note": note if ok else (note or "needs recorded numbers on both sides")}


def _one(conn, sql, params):
    return conn.execute(sql, params).fetchone()


def _buildflow(conn, bid):
    c = _one(conn, "SELECT count(*) AS posts, count(views) AS with_views, COALESCE(sum(views),0) AS views, count(signups) AS with_signups, COALESCE(sum(signups),0) AS signups "
                   "FROM content_items WHERE business_id=? AND status='posted'", (bid,))
    both = _one(conn, "SELECT count(*) AS n, COALESCE(sum(views),0) AS v, COALESCE(sum(signups),0) AS s FROM content_items WHERE business_id=? AND status='posted' AND views IS NOT NULL AND signups IS NOT NULL", (bid,))
    kpi = _one(conn, "SELECT name, unit, current_value FROM kpis WHERE business_id=? AND is_primary=1 ORDER BY created_at LIMIT 1", (bid,))
    stages = [_stage("posts", "Posts published", c["posts"]),
              _stage("views", "Views (posts with views recorded)", c["views"] if c["with_views"] else None, f"{c['with_views']} of {c['posts']} posts have views recorded"),
              _stage("signups", "Signups from content (posts with signups recorded)", c["signups"] if c["with_signups"] else None, f"{c['with_signups']} of {c['posts']} posts have signups recorded"),
              _stage("primary_kpi", ("Primary KPI: " + kpi["name"]) if kpi else "Primary KPI", kpi["current_value"] if kpi else None, None if kpi else "no primary KPI set (different unit: not used in rates)")]
    return stages, [_rate("view_to_signup", "Views to signups", both["s"], both["v"], both["n"], f"over {both['n']} posts that have both numbers")]


def _agriloop(conn, bid):
    q = lambda sql: _one(conn, sql, (bid,))["n"]
    out = []
    rates = []
    for role in ("farmer", "buyer"):
        tot = conn.execute("SELECT count(*) AS n, count(*) FILTER (WHERE status IN ('onboarded','active')) AS onb, count(*) FILTER (WHERE status='active') AS act FROM market_parties WHERE business_id=? AND role=?", (bid, role)).fetchone()
        out += [_stage(role + "s", f"{role.title()}s recorded (not churned history)", tot["n"]), _stage(role + "s_onboarded", f"{role.title()}s onboarded or active", tot["onb"]), _stage(role + "s_active", f"{role.title()}s active", tot["act"])]
        rates.append(_rate(role + "_onboarding", f"{role.title()}s reaching onboarding", tot["onb"], tot["n"], tot["n"], "churned parties are counted in the base: their history is not tracked"))
    out += [_stage("listings", "Listings", q("SELECT count(*) AS n FROM market_listings WHERE business_id=?")), _stage("requests", "Buyer requests", q("SELECT count(*) AS n FROM market_demand WHERE business_id=?")),
            _stage("deals_agreed", "Deals agreed or completed", q("SELECT count(*) AS n FROM market_transactions WHERE business_id=? AND status IN ('agreed','completed')")),
            _stage("deals_completed", "Deals completed", q("SELECT count(*) AS n FROM market_transactions WHERE business_id=? AND status='completed'"))]
    d = _one(conn, "SELECT count(*) FILTER (WHERE status IN ('agreed','completed')) AS a, count(*) FILTER (WHERE status='completed') AS c FROM market_transactions WHERE business_id=?", (bid,))
    rates.append(_rate("deal_completion", "Agreed deals completed", d["c"], d["a"], d["a"]))
    return out, rates


def _fashion(conn, bid):
    camp = _one(conn, "SELECT count(*) FILTER (WHERE status IN ('running','done')) AS run, count(orders) FILTER (WHERE status IN ('running','done')) AS with_orders, COALESCE(sum(orders) FILTER (WHERE status IN ('running','done')),0) AS orders FROM shop_campaigns WHERE business_id=?", (bid,))
    sales = _one(conn, "SELECT count(*) AS n, count(DISTINCT customer_ref) AS cust FROM shop_sales WHERE business_id=?", (bid,))
    rep = _one(conn, "SELECT count(*) AS n FROM (SELECT customer_ref FROM shop_sales WHERE business_id=? AND customer_ref IS NOT NULL AND customer_ref<>'' GROUP BY customer_ref HAVING count(*)>1) t", (bid,))["n"]
    live = _one(conn, "SELECT count(*) AS n FROM shop_products WHERE business_id=? AND status='live'", (bid,))["n"]
    stages = [_stage("live_products", "Products live", live), _stage("campaigns", "Campaigns run (running or done)", camp["run"]),
              _stage("campaign_orders", "Orders attributed to campaigns", camp["orders"] if camp["with_orders"] else None, f"{camp['with_orders']} of {camp['run']} campaigns have orders recorded"),
              _stage("sales", "Sales recorded", sales["n"]), _stage("customers", "Distinct customers (where a reference is recorded)", sales["cust"]), _stage("repeat_customers", "Repeat customers (2+ sales)", rep)]
    return stages, [_rate("repeat_rate", "Customers who bought again", rep, sales["cust"], sales["cust"], "only sales with a customer reference")]


BUILDERS = {"buildflow": _buildflow, "agriloop": _agriloop, "fashion": _fashion}


def funnel(conn, slug) -> dict:
    biz = founder.get_business(conn, slug)
    if slug not in BUILDERS:
        return {"business": slug, "stages": None, "rates": [], "reason": "Trading is research and paper only: it has no growth funnel."}
    stages, rates = BUILDERS[slug](conn, biz["id"])
    return {"business": slug, "stages": stages, "rates": rates,
            "caveats": ["Built only from records you entered; untracked stages show as not tracked, not zero.",
                        f"A rate over fewer than {SMALL} observations is flagged small-sample: treat it as noise, not a trend."]}
