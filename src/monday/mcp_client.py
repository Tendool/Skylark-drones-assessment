"""Read-only monday.com client that talks to monday.com's own **hosted MCP
server** (https://mcp.monday.com/mcp, Streamable HTTP transport) instead of
calling the GraphQL API directly -- see GraphQLMondayClient for that
alternative. Only ever calls the read tools `get_board_info` and
`get_board_items_page`; this project's Integration Requirements are read-only.

Verified live against a real monday.com account (see DECISION_LOG.md): the
tool is `get_board_items_page`, not `get_board_items` as monday.com's docs
suggested, and its `column_values` comes back as a flat {column_id: text}
dict rather than a list of {id, text, value} objects -- both handled below.
"""
from __future__ import annotations

import asyncio

import httpx
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

    def _http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
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
                        data = await self._call_tool(session, "get_board_items_page", args)

                        for raw_item in data.get("items", []):
                            # get_board_items_page returns column_values as a flat
                            # {column_id: text} dict, not a list of {id,text,value}.
                            items.append(
                                {
                                    "id": raw_item["id"],
                                    "name": raw_item["name"],
                                    "column_values": [
                                        {
                                            "id": col_id,
                                            "title": columns.get(col_id, {}).get("title", col_id),
                                            "type": columns.get(col_id, {}).get("type", "text"),
                                            "text": text,
                                            "value": None,
                                        }
                                        for col_id, text in raw_item.get("column_values", {}).items()
                                    ],
                                }
                            )

                        pagination = data.get("pagination") or {}
                        cursor = pagination.get("nextCursor")
                        if not pagination.get("has_more") or not cursor:
                            break

                    return items
