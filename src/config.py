"""Central place reading environment configuration. See .env.example."""
from __future__ import annotations

import os

from src.monday.client_interface import MondayClient


def _require_board_env(mode: str) -> tuple[str, str, str]:
    token = os.environ.get("MONDAY_API_TOKEN")
    wo_board_id = os.environ.get("MONDAY_WORK_ORDERS_BOARD_ID")
    deals_board_id = os.environ.get("MONDAY_DEALS_BOARD_ID")
    missing = [
        name
        for name, val in [
            ("MONDAY_API_TOKEN", token),
            ("MONDAY_WORK_ORDERS_BOARD_ID", wo_board_id),
            ("MONDAY_DEALS_BOARD_ID", deals_board_id),
        ]
        if not val
    ]
    if missing:
        raise RuntimeError(f"MONDAY_MODE={mode} requires these env vars: {', '.join(missing)}")
    return token, wo_board_id, deals_board_id


def get_monday_client() -> MondayClient:
    mode = os.environ.get("MONDAY_MODE", "mock").lower()

    if mode == "live":
        # Real monday.com account, via monday.com's own hosted MCP server
        # (https://mcp.monday.com/mcp) -- see src/monday/mcp_client.py.
        from src.monday.mcp_client import MCPMondayClient

        token, wo_board_id, deals_board_id = _require_board_env(mode)
        mcp_url = os.environ.get("MONDAY_MCP_URL", "https://mcp.monday.com/mcp")
        return MCPMondayClient(token, wo_board_id, deals_board_id, mcp_url=mcp_url)

    if mode == "api":
        # Real monday.com account, via a direct read-only GraphQL client
        # instead of MCP -- kept as the documented alternative (see
        # DECISION_LOG.md) for anyone who prefers not to depend on monday.com's
        # MCP server.
        from src.monday.graphql_client import GraphQLMondayClient

        token, wo_board_id, deals_board_id = _require_board_env(mode)
        return GraphQLMondayClient(token, wo_board_id, deals_board_id)

    from src.monday.mock_client import MockMondayClient

    return MockMondayClient()


def get_llm_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "anthropic").lower()
