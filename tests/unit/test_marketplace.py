import json
import unittest

from core import workspace as ws
from dashboard.app import handle
from tests.authutil import session
from tests.dbutil import make_conn


def L(id="l1", product="Tomatoes", status="open", **kw):
    return {"id": id, "product": product, "status": status, "location": None, "price": None, "currency": None, "quantity": None, "unit": None, "party_name": "F", **kw}


def D(id="d1", product="tomatoes", status="open", **kw):
    return {"id": id, "product": product, "status": status, "location": None, "max_price": None, "currency": None, "quantity": None, "unit": None, "party_name": "B", **kw}


class MatchingTest(unittest.TestCase):
    def test_same_product_case_insensitive_and_labelled_inference(self):
        m = ws.suggest_matches([L()], [D()])
        self.assertEqual((len(m), m[0]["label"]), (1, "inference"))
        self.assertIn("location", " ".join(m[0]["unknown"]))

    def test_different_product_or_closed_rows_never_match(self):
        self.assertEqual(ws.suggest_matches([L(product="yam")], [D()]), [])
        self.assertEqual(ws.suggest_matches([L(status="closed")], [D()]), [])
        self.assertEqual(ws.suggest_matches([L()], [D(status="fulfilled")]), [])

    def test_known_location_mismatch_rules_out_but_unknown_does_not(self):
        self.assertEqual(ws.suggest_matches([L(location="St Elizabeth")], [D(location="Kingston")]), [])
        self.assertEqual(len(ws.suggest_matches([L(location="Kingston")], [D(location=" kingston ")])), 1)
        self.assertEqual(len(ws.suggest_matches([L(location="Kingston")], [D()])), 1)

    def test_price_only_compared_in_the_same_currency(self):
        self.assertEqual(ws.suggest_matches([L(price=300, currency="JMD")], [D(max_price=200, currency="JMD")]), [])
        ok = ws.suggest_matches([L(price=100, currency="JMD")], [D(max_price=200, currency="JMD")])
        self.assertEqual(len(ok), 1)
        mixed = ws.suggest_matches([L(price=300, currency="JMD")], [D(max_price=2, currency="USD")])
        self.assertEqual(len(mixed), 1)  # not comparable, so not excluded
        self.assertTrue(any("price" in u for u in mixed[0]["unknown"]))

    def test_better_evidence_ranks_first(self):
        m = ws.suggest_matches([L("a"), L("b", location="K", price=1, currency="JMD", quantity=10, unit="kg")], [D(location="K", max_price=5, currency="JMD", quantity=5, unit="kg")])
        self.assertEqual([x["listing_id"] for x in m], ["b", "a"])


class LiquidityAndMoneyTest(unittest.TestCase):
    def test_liquidity_flags_one_sided_products(self):
        r = {x["product"]: x for x in ws.liquidity([L(product="Yam"), L("l2", "Yam")], [D(product="yam"), D("d2", "callaloo")])}
        self.assertEqual((r["yam"]["supply"], r["yam"]["demand"], r["yam"]["gap"]), (2, 1, "both sides present"))
        self.assertEqual(r["callaloo"]["gap"], "no farmers recorded")

    def test_money_never_mixed_across_currencies_and_unvalued_counted(self):
        t = [{"status": "completed", "amount": 100.0, "currency": "jmd"}, {"status": "completed", "amount": 50.5, "currency": "JMD"},
             {"status": "completed", "amount": 10.0, "currency": "USD"}, {"status": "completed", "amount": None, "currency": "JMD"},
             {"status": "completed", "amount": 5.0, "currency": ""}, {"status": "agreed", "amount": 999.0, "currency": "JMD"}]
        s = ws.transaction_summary(t)
        self.assertEqual(s["completed_by_currency"], [{"currency": "JMD", "count": 2, "amount": 150.5}, {"currency": "USD", "count": 1, "amount": 10.0}])
        self.assertEqual((s["completed_without_value"], s["by_status"]["agreed"]), (2, 1))


class MarketplaceApiTest(unittest.TestCase):
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

    def market(self):
        return self.call("GET", "/api/founder/workspace/agriloop")[1]["marketplace"]

    def test_empty_marketplace_is_honest_and_other_workspaces_have_none(self):
        m = self.market()
        self.assertEqual((m["listings"], m["demand"], m["matches"], m["transactions"], m["liquidity"]), ([], [], [], [], []))
        self.assertEqual(m["transaction_summary"]["completed_by_currency"], [])
        self.assertNotIn("marketplace", self.call("GET", "/api/founder/workspace/buildflow")[1])

    def test_end_to_end_supply_demand_match_transaction(self):
        f = self.make("agriloop", "market-parties", role="farmer", name="Farmer Joe", location="St Elizabeth", status="active")
        b = self.make("agriloop", "market-parties", role="buyer", name="Hotel X", status="onboarded")
        l = self.make("agriloop", "market-listings", party_id=f["id"], product="Scotch bonnet", quantity=50, unit="kg", price=400, currency="JMD", location="St Elizabeth")
        d = self.make("agriloop", "market-demand", party_id=b["id"], product="scotch bonnet", quantity=30, unit="kg", max_price=500, currency="JMD", location="St Elizabeth")
        m = self.market()
        self.assertEqual((len(m["matches"]), m["matches"][0]["farmer"], m["matches"][0]["buyer"]), (1, "Farmer Joe", "Hotel X"))
        t = self.make("agriloop", "market-transactions", listing_id=l["id"], demand_id=d["id"], quantity=30, unit="kg", amount=12000, currency="JMD", status="completed")
        self.assertIsNotNone(t["occurred_at"])
        m = self.market()
        self.assertEqual(m["transaction_summary"]["completed_by_currency"], [{"currency": "JMD", "count": 1, "amount": 12000.0}])
        self.assertEqual((m["funnel"]["farmer"]["active"], m["funnel"]["buyer"]["onboarded"], m["buyers_with_completed"], m["repeat_buyers"]), (1, 1, 1, 0))

    def test_supply_and_demand_cannot_be_crossed_or_leak_between_businesses(self):
        f = self.make("agriloop", "market-parties", role="farmer", name="F")
        b = self.make("agriloop", "market-parties", role="buyer", name="B")
        self.assertEqual(self.call("POST", "/api/founder/businesses/agriloop/market-listings", {"party_id": b["id"], "product": "yam"})[0], 400)
        self.assertEqual(self.call("POST", "/api/founder/businesses/agriloop/market-demand", {"party_id": f["id"], "product": "yam"})[0], 400)
        self.assertEqual(self.call("POST", "/api/founder/businesses/buildflow/market-listings", {"party_id": f["id"], "product": "yam"})[0], 400)  # other business
        l = self.make("agriloop", "market-listings", party_id=f["id"], product="yam")
        self.assertEqual(self.call("POST", "/api/founder/businesses/fashion/market-transactions", {"listing_id": l["id"]})[0], 400)

    def test_validation(self):
        f = self.make("agriloop", "market-parties", role="farmer", name="F")
        for ent, body in (("market-listings", {"party_id": f["id"], "product": "yam", "quantity": 0}), ("market-listings", {"party_id": f["id"], "product": "yam", "price": -5}),
                          ("market-parties", {"role": "alien", "name": "x"}), ("market-parties", {"role": "buyer", "name": ""}),
                          ("market-transactions", {"amount": -1}), ("market-transactions", {"status": "done"})):
            self.assertEqual(self.call("POST", f"/api/founder/businesses/agriloop/{ent}", body)[0], 400, (ent, body))

    def test_repeat_buyers(self):
        f = self.make("agriloop", "market-parties", role="farmer", name="F")
        b = self.make("agriloop", "market-parties", role="buyer", name="B")
        l = self.make("agriloop", "market-listings", party_id=f["id"], product="yam")
        d = self.make("agriloop", "market-demand", party_id=b["id"], product="yam")
        for _ in range(2):
            self.make("agriloop", "market-transactions", listing_id=l["id"], demand_id=d["id"], status="completed", amount=10, currency="JMD")
        m = self.market()
        self.assertEqual((m["repeat_buyers"], m["buyers_with_completed"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
