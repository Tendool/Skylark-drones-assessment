"""Real, read-only monday.com client (GraphQL API v2).

Only ever issues read queries (`boards`, `items_page`) -- this project's
Integration Requirements are explicitly read-only against monday.com. Writing
boards/items happens once, out-of-band, via scripts/import_to_monday.py.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

MONDAY_API_URL = "https://api.monday.com/v2"
PAGE_SIZE = 100
MAX_RETRIES = 3


class MondayAPIError(RuntimeError):
    pass


class GraphQLMondayClient:
    def __init__(self, api_token: str, work_orders_board_id: str, deals_board_id: str):
        self._token = api_token
        self._board_ids = {"work_orders": work_orders_board_id, "deals": deals_board_id}
        self._column_cache: dict[str, dict[str, dict]] = {}

    def get_work_orders(self) -> list[dict]:
        return self._get_board_items(self._board_ids["work_orders"])

    def get_deals(self) -> list[dict]:
        return self._get_board_items(self._board_ids["deals"])

    # -- internals --------------------------------------------------------

    def _query(self, query: str, variables: dict) -> dict:
        body = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request(
            MONDAY_API_URL,
            data=body,
            headers={
                "Authorization": self._token,
                "Content-Type": "application/json",
                "API-Version": "2024-10",
            },
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                if "errors" in result:
                    raise MondayAPIError(str(result["errors"]))
                return result["data"]
            except (urllib.error.URLError, MondayAPIError) as exc:
                last_error = exc
                time.sleep(2**attempt)
        raise MondayAPIError(f"monday.com API request failed after {MAX_RETRIES} attempts: {last_error}")

    def _get_columns(self, board_id: str) -> dict[str, dict]:
        if board_id in self._column_cache:
            return self._column_cache[board_id]
        query = """
        query ($boardId: ID!) {
          boards(ids: [$boardId]) { columns { id title type } }
        }"""
        data = self._query(query, {"boardId": board_id})
        boards = data.get("boards") or []
        if not boards:
            raise MondayAPIError(f"Board {board_id} not found or not accessible with this token.")
        columns = {c["id"]: c for c in boards[0]["columns"]}
        self._column_cache[board_id] = columns
        return columns

    def _get_board_items(self, board_id: str) -> list[dict]:
        columns = self._get_columns(board_id)
        query = """
        query ($boardId: ID!, $cursor: String, $limit: Int!) {
          boards(ids: [$boardId]) {
            items_page(limit: $limit, cursor: $cursor) {
              cursor
              items { id name column_values { id text value } }
            }
          }
        }"""

        items: list[dict] = []
        cursor = None
        while True:
            data = self._query(query, {"boardId": board_id, "cursor": cursor, "limit": PAGE_SIZE})
            page = data["boards"][0]["items_page"]
            for raw_item in page["items"]:
                items.append(
                    {
                        "id": raw_item["id"],
                        "name": raw_item["name"],
                        "column_values": [
                            {
                                "id": cv["id"],
                                "title": columns.get(cv["id"], {}).get("title", cv["id"]),
                                "type": columns.get(cv["id"], {}).get("type", "text"),
                                "text": cv["text"],
                                "value": cv["value"],
                            }
                            for cv in raw_item["column_values"]
                        ],
                    }
                )
            cursor = page["cursor"]
            if not cursor:
                break
        return items
