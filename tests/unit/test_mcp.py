import json
import os
import unittest
from unittest import mock

from dashboard.app import handle
from tests.dbutil import make_conn
from tests.unit.test_scout import good
from tests.unit.test_scout_db import Source
from agents.scout.run import run_scout
from agents.operator import run as operator

TOKEN = "k" * 40


class McpTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.env = mock.patch.dict(os.environ, {"MCP_CONNECTOR_TOKEN": TOKEN, "OWNER_SKILLS": "python"}, clear=True)
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
        self.assertEqual(r["result"]["serverInfo"]["name"], "zero-to-revenue")
        c, _, out = handle("POST", f"/mcp/{TOKEN}", None, self.conn, b'{"jsonrpc":"2.0","method":"notifications/initialized"}')
        self.assertEqual(c, 202)
        tools = self.rpc("tools/list")[1]["result"]["tools"]
        self.assertEqual({t["name"] for t in tools}, {"what_needs_my_attention", "get_status", "daily_report",
                                                       "list_opportunities", "list_open_actions", "list_payments"})
        self.assertTrue(all(t["annotations"]["readOnlyHint"] for t in tools))

    def test_tools_return_real_data_and_change_nothing(self):
        run_scout(self.conn, [Source([good()])])
        operator.step(self.conn)
        before = {t: self.conn.execute(f"select count(*) from {t}").fetchone()[0] for t in ("opportunities", "tasks", "user_actions", "payments")}
        r = self.rpc("tools/call", {"name": "what_needs_my_attention"})[1]["result"]["structuredContent"]
        self.assertTrue(any(i.startswith("Decision needed") for i in r["needs_attention"]))
        opps = self.rpc("tools/call", {"name": "list_opportunities", "arguments": {"limit": 5}})[1]["result"]["structuredContent"]
        self.assertEqual(opps["opportunities"][0]["status"], "IN_PROGRESS")
        self.assertIn("untrusted", opps["note"])
        for name in ("get_status", "daily_report", "list_open_actions", "list_payments"):
            self.assertNotIn("error", self.rpc("tools/call", {"name": name})[1], name)
        after = {t: self.conn.execute(f"select count(*) from {t}").fetchone()[0] for t in before}
        self.assertEqual(before, after)
        self.assertEqual(self.conn.execute("select count(*) from audit_events where action='mcp.tool'").fetchone()[0], 6)

    def test_bad_input(self):
        self.assertEqual(self.rpc("tools/call", {"name": "drop_tables"})[1]["error"]["code"], -32602)
        self.assertTrue(self.rpc("tools/call", {"name": "list_opportunities", "arguments": {"limit": "x"}})[1]["result"]["isError"])
        self.assertEqual(self.rpc("resources/list")[1]["error"]["code"], -32601)
        self.assertEqual(handle("POST", f"/mcp/{TOKEN}", None, self.conn, b"not json")[0], 400)


if __name__ == "__main__":
    unittest.main()
