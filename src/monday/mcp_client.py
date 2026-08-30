"""Read-only monday.com client that talks to monday.com's own **hosted MCP
server** (https://mcp.monday.com/mcp, Streamable HTTP transport) instead of
calling the GraphQL API directly -- see GraphQLMondayClient for that
alternative. Only ever calls the read tools `get_board_info` and
`get_board_items`; this project's Integration Requirements are read-only.

Verified against monday.com's published Platform MCP docs (developer.monday.com):
tool names/schemas for get_board_info and get_board_items, the hosted
Streamable HTTP endpoint, and personal-API-token auth via a Bearer header.
Not exercised against a live monday.com account during development (no
account was available) -- see DECISION_LOG.md.
"""
from __future__ import annotations

import asyncio

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MONDAY_MCP_URL = "https://mcp.monday.com/mcp"
DEFAULT_API_VERSION = "2026-07"
PAGE_SIZE = 500


class MCPMondayClient:
    def __init__(
        self,
        api_token: str,
        work_orders_board_id: str,
        deals_board_id: str,
        mcp_url: str = MONDAY_MCP_URL,
        api_version: str = DEFAULT_API_VERSION,
    ):
        self._token = api_token
        self._board_ids = {"work_orders": work_orders_board_id, "deals": deals_board_id}
        self._mcp_url = mcp_url
        self._api_version = api_version

    def get_work_orders(self) -> list[dict]:
        return asyncio.run(self._get_board_items(self._board_ids["work_orders"]))

    def get_deals(self) -> list[dict]:
        return asyncio.run(self._get_board_items(self._board_ids["deals"]))

    # -- internals --------------------------------------------------------

    def _http_client(self) -> httpx2.AsyncClient:
        return httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {self._token}", "Api-Version": self._api_version},
            timeout=30,
        )

    async def _call_tool(self, session: ClientSession, name: str, arguments: dict) -> dict:
        result = await session.call_tool(name, arguments)
        if result.is_error:
            text = "; ".join(c.text for c in result.content if hasattr(c, "text"))
            raise RuntimeError(f"monday.com MCP tool '{name}' failed: {text}")
        if result.structured_content is not None:
            return result.structured_content
        # Fall back to the first text content block if the server didn't
        # return structured JSON for this tool.
        for block in result.content:
            if hasattr(block, "text"):
                import json

                return json.loads(block.text)
        raise RuntimeError(f"monday.com MCP tool '{name}' returned no usable content")

    async def _get_columns(self, session: ClientSession, board_id: str) -> dict[str, dict]:
        data = await self._call_tool(session, "get_board_info", {"boardId": int(board_id)})
        columns = data.get("columns") or data.get("board", {}).get("columns", [])
        return {c["id"]: c for c in columns}

    async def _get_board_items(self, board_id: str) -> list[dict]:
        async with self._http_client() as http_client:
            async with streamable_http_client(self._mcp_url, http_client=http_client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    columns = await self._get_columns(session, board_id)

                    items: list[dict] = []
                    cursor = None
                    while True:
                        args = {"boardId": int(board_id), "includeColumns": True, "limit": PAGE_SIZE}
                        if cursor:
                            args["cursor"] = cursor
                        data = await self._call_tool(session, "get_board_items", args)

                        for raw_item in data.get("items", []):
                            items.append(
                                {
                                    "id": raw_item["id"],
                                    "name": raw_item["name"],
                                    "column_values": [
                                        {
                                            "id": cv["id"],
                                            "title": columns.get(cv["id"], {}).get("title", cv["id"]),
                                            "type": columns.get(cv["id"], {}).get("type", "text"),
                                            "text": cv.get("text"),
                                            "value": cv.get("value"),
                                        }
                                        for cv in raw_item.get("column_values", [])
                                    ],
                                }
                            )

                        pagination = data.get("pagination") or {}
                        cursor = pagination.get("nextCursor")
                        if not pagination.get("has_more") or not cursor:
                            break

                    return items
