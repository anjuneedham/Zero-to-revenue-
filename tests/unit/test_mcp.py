import json
import os
import unittest
from unittest import mock

from dashboard.app import handle
from tests.dbutil import make_conn
from dashboard import api_data

TOKEN = "k" * 40


class McpTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.env = mock.patch.dict(os.environ, {"MCP_CONNECTOR_TOKEN": TOKEN}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def rpc(self, method, params=None, rid=1, path=f"/mcp/{TOKEN}", authz=None):
        body = json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}).encode()
        c, _, out = handle("POST", path, authz, self.conn, body)
        return c, (json.loads(out) if out else None)

    def test_auth(self):
        self.assertEqual(self.rpc("ping", path="/mcp")[0], 401)
        self.assertEqual(self.rpc("ping", path="/mcp/wrong")[0], 401)
        self.assertEqual(self.rpc("ping", path="/mcp", authz=f"Bearer {TOKEN}")[0], 200)
        with mock.patch.dict(os.environ, {"MCP_CONNECTOR_TOKEN": "short"}):
            self.assertEqual(self.rpc("ping", path="/mcp/short")[0], 401)  # weak token = disabled
        self.assertEqual(handle("GET", f"/mcp/{TOKEN}", None, self.conn, b"")[0], 405)

    def test_handshake_and_tool_list_are_read_only(self):
        c, r = self.rpc("initialize", {"protocolVersion": "2025-06-18"})
        self.assertEqual(r["result"]["serverInfo"]["name"], "founder-os")
        c, _, out = handle("POST", f"/mcp/{TOKEN}", None, self.conn, b'{"jsonrpc":"2.0","method":"notifications/initialized"}')
        self.assertEqual(c, 202)
        tools = self.rpc("tools/list")[1]["result"]["tools"]
        self.assertEqual({t["name"] for t in tools}, {"what_needs_my_attention", "get_status", "daily_report", "list_payments"})
        self.assertTrue(all(t["annotations"]["readOnlyHint"] for t in tools))

    def test_tools_return_real_data_and_change_nothing(self):
        api_data.create_manual_payment(self.conn, "owner", "Annual plan", "500")
        before = {t: self.conn.execute(f"select count(*) from {t}").fetchone()[0] for t in ("opportunities", "payments", "ledger_entries")}
        r = self.rpc("tools/call", {"name": "what_needs_my_attention"})[1]["result"]["structuredContent"]
        self.assertTrue(any("awaiting verification" in i for i in r["needs_attention"]))
        pays = self.rpc("tools/call", {"name": "list_payments"})[1]["result"]["structuredContent"]
        self.assertEqual(pays["payments"][0]["status"], "AWAITING_PAYMENT")
        for name in ("get_status", "daily_report"):
            self.assertNotIn("error", self.rpc("tools/call", {"name": name})[1], name)
        after = {t: self.conn.execute(f"select count(*) from {t}").fetchone()[0] for t in before}
        self.assertEqual(before, after)
        self.assertEqual(self.conn.execute("select count(*) from audit_events where action='mcp.tool'").fetchone()[0], 4)

    def test_bad_input(self):
        self.assertEqual(self.rpc("tools/call", {"name": "drop_tables"})[1]["error"]["code"], -32602)
        self.assertEqual(self.rpc("resources/list")[1]["error"]["code"], -32601)
        self.assertEqual(handle("POST", f"/mcp/{TOKEN}", None, self.conn, b"not json")[0], 400)


if __name__ == "__main__":
    unittest.main()
