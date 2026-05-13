from __future__ import annotations

import unittest

from reference_agent.weblog_agent.mcp import StdioMCPClient


class MCPTests(unittest.TestCase):
    def test_stdio_mcp_server_lists_and_calls_tool(self):
        client = StdioMCPClient()
        try:
            tools = client.list_tools()
            self.assertTrue(any(tool["name"] == "get_service_context" for tool in tools["tools"]))
            context = client.call_tool("get_service_context", {"path": "/api/login"})
        finally:
            client.close()

        self.assertEqual(context["service"], "identity-api")
        self.assertEqual(context["owner"], "identity-platform")
        self.assertIn("auth-provider", context["dependencies"])
        self.assertEqual(context["slo"]["p95LatencyMs"], 800)


if __name__ == "__main__":
    unittest.main()
