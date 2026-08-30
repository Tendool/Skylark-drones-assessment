#!/usr/bin/env python3
"""
Import the source Work Orders / Deals spreadsheets as monday.com boards + items.

Two modes:
  --mode fixtures (default)  Write monday.com-shaped JSON to fixtures/, used by the
                              mock client (src/monday/mock_client.py) so the app can
                              run end-to-end with zero external credentials.
  --mode live                 Actually create the two boards on monday.com and push
                              every row as an item, via the GraphQL API. Requires
                              MONDAY_API_TOKEN (and optionally MONDAY_WORKSPACE_ID)
                              in the environment. Read/write use is limited to this
                              one-off import; the app itself only ever reads.

Usage:
    python scripts/import_to_monday.py --mode fixtures
    MONDAY_API_TOKEN=xxx python scripts/import_to_monday.py --mode live
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.monday.build_items import rows_to_items
from src.monday.schema import (
    DEALS_BOARD_NAME,
    DEALS_COLUMNS,
    DEALS_NAME_SOURCE_COLUMN,
    WORK_ORDERS_BOARD_NAME,
    WORK_ORDERS_COLUMNS,
    WORK_ORDERS_NAME_SOURCE_COLUMN,
)

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
FIXTURES_DIR = ROOT / "fixtures"

MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_COLUMN_TYPE_MAP = {
    "text": "text",
    "long_text": "long_text",
    "status": "status",
    "date": "date",
    "numbers": "numbers",
}


def load_work_orders() -> pd.DataFrame:
    # Row 0 of the sheet is blank, real headers are row 1 -- see DECISION_LOG.md.
    return pd.read_excel(RAW_DIR / "work_order_tracker.xlsx", sheet_name="work order tracker", header=1)


def load_deals() -> pd.DataFrame:
    return pd.read_excel(RAW_DIR / "deal_funnel.xlsx", sheet_name="Deal tracker")


def write_fixtures() -> None:
    FIXTURES_DIR.mkdir(exist_ok=True)

    wo_df = load_work_orders()
    wo_items, wo_warnings = rows_to_items(wo_df, WORK_ORDERS_COLUMNS, WORK_ORDERS_NAME_SOURCE_COLUMN, "WO")
    (FIXTURES_DIR / "work_orders_items.json").write_text(json.dumps(wo_items, indent=2))

    deal_df = load_deals()
    deal_items, deal_warnings = rows_to_items(deal_df, DEALS_COLUMNS, DEALS_NAME_SOURCE_COLUMN, "DEAL")
    (FIXTURES_DIR / "deals_items.json").write_text(json.dumps(deal_items, indent=2))

    print(f"Wrote {len(wo_items)} work order items -> fixtures/work_orders_items.json")
    for w in wo_warnings:
        print(f"  ! {w}")
    print(f"Wrote {len(deal_items)} deal items -> fixtures/deals_items.json")
    for w in deal_warnings:
        print(f"  ! {w}")


def _graphql(token: str, query: str, variables: dict) -> dict:
    import urllib.request

    req = urllib.request.Request(
        MONDAY_API_URL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": token, "Content-Type": "application/json", "API-Version": "2024-10"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    if "errors" in result:
        raise RuntimeError(f"monday.com API error: {result['errors']}")
    return result["data"]


def _create_board(token: str, name: str, workspace_id: str | None) -> str:
    query = """
    mutation ($name: String!, $workspaceId: ID) {
      create_board(board_name: $name, board_kind: private, workspace_id: $workspaceId) { id }
    }"""
    data = _graphql(token, query, {"name": name, "workspaceId": workspace_id})
    return data["create_board"]["id"]


def _create_columns(token: str, board_id: str, columns) -> dict[str, str]:
    """Returns a map of our column id -> monday.com's real column id."""
    id_map = {}
    query = """
    mutation ($boardId: ID!, $title: String!, $columnType: ColumnType!) {
      create_column(board_id: $boardId, title: $title, column_type: $columnType) { id }
    }"""
    for col in columns:
        data = _graphql(
            token,
            query,
            {"boardId": board_id, "title": col.title, "columnType": MONDAY_COLUMN_TYPE_MAP[col.type]},
        )
        id_map[col.id] = data["create_column"]["id"]
        time.sleep(0.2)  # stay well under monday.com's rate limits
    return id_map


def _create_items(token: str, board_id: str, items: list[dict], id_map: dict[str, str]) -> None:
    query = """
    mutation ($boardId: ID!, $name: String!, $columnValues: JSON!) {
      create_item(board_id: $boardId, item_name: $name, column_values: $columnValues) { id }
    }"""
    for item in items:
        column_values = {}
        for cv in item["column_values"]:
            if cv["value"] is None:
                continue
            real_id = id_map[cv["id"]]
            column_values[real_id] = json.loads(cv["value"]) if cv["type"] == "status" or cv["type"] == "date" else cv["text"]
        _graphql(
            token,
            query,
            {"boardId": board_id, "name": item["name"] or "(unnamed)", "columnValues": json.dumps(column_values)},
        )
        time.sleep(0.2)


def push_live(workspace_id: str | None) -> None:
    token = os.environ.get("MONDAY_API_TOKEN")
    if not token:
        raise SystemExit("MONDAY_API_TOKEN is required for --mode live")

    wo_df = load_work_orders()
    wo_items, wo_warnings = rows_to_items(wo_df, WORK_ORDERS_COLUMNS, WORK_ORDERS_NAME_SOURCE_COLUMN, "WO")
    for w in wo_warnings:
        print(f"  ! {w}")

    deal_df = load_deals()
    deal_items, deal_warnings = rows_to_items(deal_df, DEALS_COLUMNS, DEALS_NAME_SOURCE_COLUMN, "DEAL")
    for w in deal_warnings:
        print(f"  ! {w}")

    print(f"Creating board '{WORK_ORDERS_BOARD_NAME}'...")
    wo_board_id = _create_board(token, WORK_ORDERS_BOARD_NAME, workspace_id)
    wo_col_map = _create_columns(token, wo_board_id, WORK_ORDERS_COLUMNS)
    print(f"Pushing {len(wo_items)} work order items...")
    _create_items(token, wo_board_id, wo_items, wo_col_map)

    print(f"Creating board '{DEALS_BOARD_NAME}'...")
    deals_board_id = _create_board(token, DEALS_BOARD_NAME, workspace_id)
    deals_col_map = _create_columns(token, deals_board_id, DEALS_COLUMNS)
    print(f"Pushing {len(deal_items)} deal items...")
    _create_items(token, deals_board_id, deal_items, deals_col_map)

    print("\nDone. Set these in your .env:")
    print(f"MONDAY_WORK_ORDERS_BOARD_ID={wo_board_id}")
    print(f"MONDAY_DEALS_BOARD_ID={deals_board_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["fixtures", "live"], default="fixtures")
    parser.add_argument("--workspace-id", default=os.environ.get("MONDAY_WORKSPACE_ID"))
    args = parser.parse_args()

    if args.mode == "fixtures":
        write_fixtures()
    else:
        push_live(args.workspace_id)
