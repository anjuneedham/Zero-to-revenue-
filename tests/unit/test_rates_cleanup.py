import json
import os
import unittest
from unittest import mock

import core.rates as rates
from agents.scout.cleanup import purge_junk
from agents.scout.run import run_scout
from agents.operator import run as operator
from core import actions
from integrations.web.fetch import FetchError
from tests.authutil import session
from tests.dbutil import make_conn
from tests.unit.test_scout import good
from tests.unit.test_scout_db import Source

CRYPTO_OK = {"bitcoin": {"usd": 80000}, "ethereum": {"usd": 2300}, "binancecoin": {"usd": 700},
             "usd-coin": {"usd": 1.0}, "tether": {"usd": 1.0}, "dai": {"usd": 1.0}, "solana": {"usd": 150}}
FIAT_OK = {"rates": {"JMD": 158.5, "EUR": 0.9, "GBP": 0.8, "CAD": 1.4, "XXX": 99}}


class RatesTest(unittest.TestCase):
    def setUp(self):
        rates._cache.clear()

    def fetch(self, crypto=CRYPTO_OK, fiat=FIAT_OK):
        def f(url, hosts, headers=None):
            if "coingecko" in url:
                self.assertEqual(hosts, rates.CRYPTO_HOST)
                return crypto
            self.assertEqual(hosts, rates.FIAT_HOST)
            return fiat
        return f

    def test_returns_known_cryptos_and_fiats_only(self):
        r = rates.get_rates(self.fetch())
        self.assertEqual(r["crypto_usd"]["BTC"], 80000)
        self.assertEqual(r["crypto_usd"]["USDC"], 1.0)
        self.assertEqual(r["fiat_per_usd"]["JMD"], 158.5)
        self.assertNotIn("XXX", r["fiat_per_usd"])  # not on the allowed fiat list
        self.assertFalse(r["stale"])
        self.assertIsNotNone(r["as_of"])

    def test_cached_within_ttl_then_refetches(self):
        calls = {"n": 0}

        def counting(url, hosts, headers=None):
            calls["n"] += 1
            return CRYPTO_OK if "coingecko" in url else FIAT_OK
        rates.get_rates(counting)
        rates.get_rates(counting)
        self.assertEqual(calls["n"], 2)  # one crypto + one fiat call, cached on the second get_rates
        rates.get_rates(counting, force=True)
        self.assertEqual(calls["n"], 4)

    def test_fetch_failure_serves_stale_cache_instead_of_erroring(self):
        rates.get_rates(self.fetch())  # warm the cache
        booms = lambda *a, **k: (_ for _ in ()).throw(FetchError("down"))
        r = rates.get_rates(booms, force=True)
        self.assertTrue(r["stale"])
        self.assertEqual(r["crypto_usd"]["BTC"], 80000)  # still the last good value

    def test_total_failure_with_no_cache_returns_empty_not_a_crash(self):
        booms = lambda *a, **k: (_ for _ in ()).throw(FetchError("down"))
        r = rates.get_rates(booms, force=True)
        self.assertEqual(r, {"crypto_usd": {}, "fiat_per_usd": {}, "as_of": None, "stale": True})

    def test_malformed_response_never_crashes(self):
        bad = lambda url, hosts, headers=None: ("not", "a", "dict")
        r = rates.get_rates(bad, force=True)
        self.assertEqual(r["crypto_usd"], {})


class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.env = mock.patch.dict(os.environ, {"OWNER_SKILLS": "python"}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def seed(self, **row):
        base = dict(id="opp_x", title="junk", status="REVIEW_REQUIRED", risk_score=0, scam_indicators="",
                    discovered_at="now", source_url="https://x/" + row.get("id", "opp_x"))
        base.update(row)
        cols = list(base)
        self.conn.execute(f"INSERT INTO opportunities({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                          tuple(base[c] for c in cols))

    def test_removes_untouched_scam_risk_and_hard_flags(self):
        self.seed(id="a", risk_score=75, scam_indicators="token_exchange_scheme")
        self.seed(id="b", risk_score=0, scam_indicators="duplicated_title_spam")
        self.seed(id="c", risk_score=10, scam_indicators="human_only_listing")  # clean, kept
        self.seed(id="d", risk_score=0, scam_indicators="")  # nothing wrong, kept
        self.seed(id="e", risk_score=30, scam_indicators="unclear_payment_terms")  # below the floor, kept
        n = purge_junk(self.conn)
        self.assertEqual(n, 2)
        left = {r[0] for r in self.conn.execute("select id from opportunities")}
        self.assertEqual(left, {"c", "d", "e"})
        self.assertEqual(self.conn.execute("select count(*) from audit_events where action='scout.cleanup'").fetchone()[0], 1)

    def test_never_deletes_anything_touched_by_a_task_or_payment(self):
        run_scout(self.conn, [Source([good()])])
        oid = self.conn.execute("select id from opportunities").fetchone()[0]
        self.conn.execute("update opportunities set status='REVIEW_REQUIRED', risk_score=90, scam_indicators='token_exchange_scheme'")
        self.assertEqual(purge_junk(self.conn), 0)  # has a task from the scout run

    def test_removes_untouched_off_skill_listings(self):
        self.seed(id="f", risk_score=0, scam_indicators="off_skill")
        self.seed(id="g", risk_score=0, scam_indicators="human_only_listing")  # off-skill never set alongside this; kept
        n = purge_junk(self.conn)
        self.assertEqual(n, 1)
        left = {r[0] for r in self.conn.execute("select id from opportunities")}
        self.assertEqual(left, {"g"})

    def test_only_qualified_status_untouched(self):
        self.seed(id="q", status="QUALIFIED", risk_score=90, scam_indicators="token_exchange_scheme")
        self.assertEqual(purge_junk(self.conn), 0)  # not REVIEW_REQUIRED, left for the owner to see

    def test_run_scout_cleans_up_junk_found_in_the_same_pass(self):
        from tests.unit.test_scout import LIVE_JUNK
        junk_item = good(title=LIVE_JUNK[0], source_url="https://github.com/farm/r/issues/1", payment_method="", deadline=None, required_capital=None)
        r = run_scout(self.conn, [Source([junk_item])])
        self.assertEqual(r["new"], 1)
        self.assertEqual(r["purged"], 1)
        self.assertEqual(self.conn.execute("select count(*) from opportunities").fetchone()[0], 0)


class RatesApiTest(unittest.TestCase):
    def test_requires_login_and_returns_rates(self):
        import dashboard.app as dash
        conn = make_conn()
        self.assertEqual(dash.handle("GET", "/api/rates", None, conn, b"")[0], 401)
        tok, _, _ = session(conn)
        with mock.patch("core.rates.get_rates", return_value={"crypto_usd": {"BTC": 1}, "fiat_per_usd": {"JMD": 1}, "as_of": "x", "stale": False}):
            c, _, out = dash.handle("GET", "/api/rates", f"Bearer {tok}", conn, b"")
        self.assertEqual((c, json.loads(out)["crypto_usd"]["BTC"]), (200, 1))


class DismissApiTest(unittest.TestCase):
    def setUp(self):
        import dashboard.app as dash
        self.dash = dash
        self.conn = make_conn()
        self.tok, _, _ = session(self.conn)

    def seed(self, oid):
        self.conn.execute("INSERT INTO opportunities(id,title,status,discovered_at,source_url) VALUES (?,?,?,?,?)",
                          (oid, "junk", "REVIEW_REQUIRED", "now", "https://x/" + oid))

    def call(self, body):
        c, _, out = self.dash.handle("POST", "/api/opportunities/dismiss", f"Bearer {self.tok}", self.conn, json.dumps(body).encode())
        return c, json.loads(out)

    def test_requires_auth(self):
        c, _, _ = self.dash.handle("POST", "/api/opportunities/dismiss", None, self.conn, json.dumps({"ids": ["opp_000000000000"]}).encode())
        self.assertEqual(c, 401)

    def test_removes_listed_ids_and_rejects_bad_input(self):
        self.seed("opp_111111111111")
        self.seed("opp_222222222222")
        c, r = self.call({"ids": ["opp_111111111111", "opp_222222222222", "not-a-real-id"]})
        self.assertEqual((c, r["removed"]), (200, 2))
        self.assertEqual(self.conn.execute("select count(*) from opportunities").fetchone()[0], 0)
        self.assertEqual(self.call({"ids": []})[0], 400)
        self.assertEqual(self.call({})[0], 400)

    def test_never_removes_a_touched_opportunity(self):
        run_scout(self.conn, [Source([good()])])
        oid = self.conn.execute("select id from opportunities").fetchone()[0]
        self.conn.execute("update opportunities set status='REVIEW_REQUIRED' where id=?", (oid,))
        c, r = self.call({"ids": [oid]})
        self.assertEqual((c, r["removed"], r["skipped"]), (200, 0, 1))
        self.assertEqual(self.conn.execute("select count(*) from opportunities").fetchone()[0], 1)

    def test_removable_once_its_only_task_is_cancelled_or_failed(self):
        run_scout(self.conn, [Source([good()])])
        oid = self.conn.execute("select id from opportunities").fetchone()[0]
        self.conn.execute("update tasks set status='CANCELLED' where opportunity_id=?", (oid,))
        c, r = self.call({"ids": [oid]})
        self.assertEqual((c, r["removed"]), (200, 1))
        self.assertEqual(self.conn.execute("select count(*) from opportunities").fetchone()[0], 0)

    def test_still_blocked_while_a_second_task_is_live(self):
        run_scout(self.conn, [Source([good()])])
        oid = self.conn.execute("select id from opportunities").fetchone()[0]
        self.conn.execute("update tasks set status='CANCELLED' where opportunity_id=?", (oid,))
        self.conn.execute("INSERT INTO tasks(id,opportunity_id,owner_agent,kind,status,created_at,updated_at,idempotency_key) "
                          "VALUES ('t_retry',?,'operator','draft','IN_PROGRESS','now','now','t_retry_key')", (oid,))
        c, r = self.call({"ids": [oid]})
        self.assertEqual((c, r["removed"], r["skipped"]), (200, 0, 1))


if __name__ == "__main__":
    unittest.main()
