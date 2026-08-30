"""Central place reading environment configuration. See .env.example."""
from __future__ import annotations

import os

from src.monday.client_interface import MondayClient


def get_monday_client() -> MondayClient:
    mode = os.environ.get("MONDAY_MODE", "mock").lower()

    if mode == "live":
        from src.monday.graphql_client import GraphQLMondayClient

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
            raise RuntimeError(f"MONDAY_MODE=live requires these env vars: {', '.join(missing)}")
        return GraphQLMondayClient(token, wo_board_id, deals_board_id)

    from src.monday.mock_client import MockMondayClient

    return MockMondayClient()


def get_llm_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "anthropic").lower()
