import json
import os
import unittest
from unittest import mock

import core.rates as rates
from integrations.web.fetch import FetchError
from tests.authutil import session
from tests.dbutil import make_conn

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


class RatesApiTest(unittest.TestCase):
    def test_requires_login_and_returns_rates(self):
        import dashboard.app as dash
        conn = make_conn()
        self.assertEqual(dash.handle("GET", "/api/rates", None, conn, b"")[0], 401)
        tok, _, _ = session(conn)
        with mock.patch("core.rates.get_rates", return_value={"crypto_usd": {"BTC": 1}, "fiat_per_usd": {"JMD": 1}, "as_of": "x", "stale": False}):
            c, _, out = dash.handle("GET", "/api/rates", f"Bearer {tok}", conn, b"")
        self.assertEqual((c, json.loads(out)["crypto_usd"]["BTC"]), (200, 1))
