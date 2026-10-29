import json
import unittest
from datetime import date

from core import workspace as ws
from dashboard.app import handle
from tests.authutil import session
from tests.dbutil import make_conn

TODAY = date(2026, 10, 29)


def P(**kw):
    return {"id": "p", "name": "Tee", "status": "live", "price": None, "unit_cost": None, "stock_qty": None, "reorder_point": None, "currency": "JMD", **kw}


class ProductMathTest(unittest.TestCase):
    def test_margin_and_stock_value_only_when_inputs_exist(self):
        v = ws.product_view(P(price=4000, unit_cost=1500, stock_qty=20))
        self.assertEqual((v["margin_amount"], v["margin_pct"], v["stock_value"]), (2500.0, 62.5, 30000.0))
        e = ws.product_view(P(price=4000))
        self.assertEqual((e["margin_pct"], e["stock_value"]), (None, None))
        self.assertIsNone(ws.product_view(P(price=0, unit_cost=5))["margin_pct"])

    def test_flags(self):
        self.assertEqual(ws.product_view(P(stock_qty=0))["stock_flag"], "out of stock")
        self.assertEqual(ws.product_view(P(stock_qty=3, reorder_point=5))["stock_flag"], "at or below reorder point")
        self.assertIsNone(ws.product_view(P(stock_qty=9, reorder_point=5))["stock_flag"])
        self.assertEqual(ws.product_view(P(price=10, unit_cost=12))["margin_flag"], "selling below cost")


class SalesSummaryTest(unittest.TestCase):
    def sale(self, rev, cur="JMD", qty=1, ref=None, at="2026-10-28T10:00:00+00:00"):
        return {"revenue": rev, "currency": cur, "quantity": qty, "customer_ref": ref, "sold_at": at}

    def test_per_currency_and_unvalued(self):
        s = ws.sales_summary([self.sale(100.0), self.sale(50.0, qty=2), self.sale(5.0, "USD"), self.sale(None), self.sale(9.0, "")], TODAY)
        jmd = next(c for c in s["by_currency"] if c["currency"] == "JMD")
        self.assertEqual((jmd["orders"], jmd["units"], jmd["revenue"], jmd["avg_order_value"]), (2, 3, 150.0, 75.0))
        self.assertEqual((len(s["by_currency"]), s["unvalued_orders"], s["orders_total"]), (2, 2, 5))

    def test_repeat_customers_need_a_reference(self):
        s = ws.sales_summary([self.sale(1.0, ref="Ann"), self.sale(1.0, ref=" ann "), self.sale(1.0, ref="Bo"), self.sale(1.0)], TODAY)
        self.assertEqual((s["customers_identified"], s["repeat_customers"]), (2, 1))

    def test_last_30_days_window(self):
        s = ws.sales_summary([self.sale(10.0, at="2026-10-20T00:00:00+00:00"), self.sale(7.0, at="2026-08-01T00:00:00+00:00")], TODAY)
        self.assertEqual((s["by_currency"][0]["revenue"], s["by_currency"][0]["last_30_days"]), (17.0, 10.0))

    def test_empty(self):
        self.assertEqual(ws.sales_summary([], TODAY)["by_currency"], [])


class CampaignTest(unittest.TestCase):
    def test_roas_needs_spend_and_revenue(self):
        c = {"spend": 200.0, "attributed_revenue": 500.0, "orders": 5}
        v = ws.campaign_view(c)
        self.assertEqual((v["roas"], v["cost_per_order"]), (2.5, 40.0))
        self.assertIsNone(ws.campaign_view({"spend": 200.0, "attributed_revenue": None, "orders": None})["roas"])
        self.assertIsNone(ws.campaign_view({"spend": 0, "attributed_revenue": 5.0, "orders": 0})["roas"])


class ShopApiTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.tok = session(self.conn)[0]

    def call(self, method, path, body=None):
        c, _, out = handle(method, path, f"Bearer {self.tok}", self.conn, json.dumps(body).encode() if body is not None else b"")
        return c, json.loads(out)

    def make(self, biz, entity, **body):
        c, r = self.call("POST", f"/api/founder/businesses/{biz}/{entity}", body)
        self.assertEqual(c, 201, r)
        return r

    def shop(self):
        return self.call("GET", "/api/founder/workspace/fashion")[1]["shop"]

    def test_brand_description_set_by_migration_and_empty_shop_is_honest(self):
        w = self.call("GET", "/api/founder/workspace/fashion")[1]
        self.assertIn("Yaad n Abroad", w["business"]["description"])
        s = w["shop"]
        self.assertEqual((s["products"], s["sales"], s["campaigns"], s["attention"], s["inventory_value_at_cost"]), ([], [], [], [], []))
        self.assertNotIn("shop", self.call("GET", "/api/founder/workspace/buildflow")[1])

    def test_flow_product_sale_campaign(self):
        p = self.make("fashion", "shop-products", name="Pain into Art tee", status="live", unit_cost=1500, price=4000, currency="JMD", stock_qty=2, reorder_point=5)
        self.make("fashion", "shop-sales", product_id=p["id"], quantity=2, revenue=8000, currency="JMD", customer_ref="Ann", channel="instagram")
        self.make("fashion", "shop-sales", product_id=p["id"], quantity=1, revenue=4000, currency="JMD", customer_ref="Ann")
        c = self.make("fashion", "shop-campaigns", name="Launch reel", channel="instagram", spend=1000, attributed_revenue=8000, orders=1, currency="JMD", status="done")
        s = self.shop()
        self.assertEqual(s["products"][0]["margin_pct"], 62.5)
        self.assertEqual(s["attention"], [{"product": "Pain into Art tee", "flag": "at or below reorder point"}])
        self.assertEqual(s["inventory_value_at_cost"], [{"currency": "JMD", "amount": 3000.0}])
        ss = s["sales_summary"]
        self.assertEqual((ss["by_currency"][0]["revenue"], ss["repeat_customers"], s["sales"][0]["product_name"]), (12000.0, 1, "Pain into Art tee"))
        self.assertEqual((s["campaigns"][0]["roas"], s["campaigns"][0]["cost_per_order"]), (8.0, 1000.0))
        self.assertEqual(self.call("POST", f"/api/founder/shop-campaigns/{c['id']}", {"status": "cancelled"})[0], 200)

    def test_sale_update_works_without_updated_at_and_sold_at_defaults(self):
        s = self.make("fashion", "shop-sales", quantity=1)
        self.assertIsNotNone(s["sold_at"])
        self.assertEqual(self.call("POST", f"/api/founder/shop-sales/{s['id']}", {"revenue": 10, "currency": "JMD"})[0], 200)

    def test_isolation_and_validation(self):
        p = self.make("fashion", "shop-products", name="Tee")
        self.assertEqual(self.call("POST", "/api/founder/businesses/agriloop/shop-sales", {"product_id": p["id"]})[0], 400)
        bad = [("shop-products", {"name": "x", "price": -1}), ("shop-products", {"name": "x", "stock_qty": -3}), ("shop-products", {"name": "x", "status": "sold"}),
               ("shop-sales", {"quantity": 0}), ("shop-sales", {"revenue": -5}), ("shop-campaigns", {"name": "c", "spend": -1}), ("shop-campaigns", {"name": ""})]
        for ent, body in bad:
            self.assertEqual(self.call("POST", f"/api/founder/businesses/fashion/{ent}", body)[0], 400, (ent, body))

    def test_content_and_feedback_are_reused_for_fashion(self):
        self.make("fashion", "content-items", platform="instagram", topic="drop", status="posted", views=500)
        self.make("fashion", "feedback-items", body="Loved the colours", kind="praise")
        w = self.call("GET", "/api/founder/workspace/fashion")[1]
        self.assertEqual((len(w["content"]["items"]), len(w["feedback"])), (1, 1))
        self.assertEqual(self.call("GET", "/api/founder/workspace/buildflow")[1]["feedback"], [])


if __name__ == "__main__":
    unittest.main()
