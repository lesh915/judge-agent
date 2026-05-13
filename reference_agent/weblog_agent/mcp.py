from __future__ import annotations

from typing import Any, Dict


class MockMCPClient:
    """Reference MCP client.

    In production this would call MCP servers for deployment, ownership, and
    service metadata. For repeatable fixtures it returns deterministic service
    context while preserving explicit `mcp_call` trace events in the agent.
    """

    def get_service_context(self, path: str | None) -> Dict[str, Any]:
        if path == "/api/payment":
            return {
                "service": "payment-api",
                "owner": "payments-platform",
                "recentDeployments": ["payment-api@2026.05.13-01"],
                "dependencies": ["psp-gateway", "fraud-service"],
                "slo": {"availability": "99.95%", "p95LatencyMs": 900},
            }
        return {
            "service": "identity-api",
            "owner": "identity-platform",
            "recentDeployments": ["identity-api@2026.05.13-03", "session-store@2026.05.12-21"],
            "dependencies": ["auth-provider", "session-store", "user-db"],
            "slo": {"availability": "99.9%", "p95LatencyMs": 800},
        }
