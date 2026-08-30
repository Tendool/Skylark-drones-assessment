"""Verifies MCPMondayClient against a throwaway in-process MCP server that
mimics monday.com's real get_board_info/get_board_items_page tool contracts,
as confirmed against a live monday.com account (see DECISION_LOG.md) --
notably get_board_items_page (not get_board_items), and column_values coming
back as a flat {column_id: text} dict rather than a list. No network access,
no real monday.com account needed to run this test."""
import socket
import threading
import time

import pytest
import uvicorn
from mcp.server.mcpserver import MCPServer

from src.monday.mcp_client import MCPMondayClient

BOARD_ID = "111"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_server() -> MCPServer:
    server = MCPServer("fake-monday")
    board = {
        "columns": [
            {"id": "sector", "title": "Sector", "type": "status"},
            {"id": "amount", "title": "Amount in Rupees (Incl of GST) (Masked)", "type": "numbers"},
        ],
        "items": [
            {"id": "1", "name": "SER-1", "column_values": {"sector": "Mining", "amount": "1000"}},
            {"id": "2", "name": "SER-2", "column_values": {"sector": "Renewables", "amount": "2000"}},
        ],
    }

    @server.tool()
    def get_board_info(boardId: int) -> dict:
        assert str(boardId) == BOARD_ID
        return {"board": {"columns": board["columns"]}}

    @server.tool()
    def get_board_items_page(boardId: int, includeColumns: bool = False, limit: int = 25, cursor: str | None = None) -> dict:
        assert str(boardId) == BOARD_ID
        idx = int(cursor) if cursor else 0
        page = board["items"][idx : idx + 1]  # 1 item per page, to exercise pagination
        next_idx = idx + 1
        has_more = next_idx < len(board["items"])
        return {"items": page, "pagination": {"nextCursor": str(next_idx) if has_more else None, "has_more": has_more}}

    return server


@pytest.fixture(scope="module")
def fake_mcp_url():
    port = _free_port()
    server = _make_server()
    config = uvicorn.Config(server.streamable_http_app(), host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    for _ in range(50):
        if uv_server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}/mcp"
    uv_server.should_exit = True
    thread.join(timeout=5)


def test_get_work_orders_paginates_and_enriches_columns(fake_mcp_url):
    client = MCPMondayClient("fake-token", BOARD_ID, BOARD_ID, mcp_url=fake_mcp_url)

    items = client.get_work_orders()

    assert [i["name"] for i in items] == ["SER-1", "SER-2"]
    first_cols = {cv["id"]: cv for cv in items[0]["column_values"]}
    assert first_cols["sector"]["title"] == "Sector"
    assert first_cols["sector"]["type"] == "status"
    assert first_cols["sector"]["text"] == "Mining"


def test_items_flow_through_the_normal_cleaning_pipeline(fake_mcp_url):
    from src.data.normalize import clean_work_orders

    client = MCPMondayClient("fake-token", BOARD_ID, BOARD_ID, mcp_url=fake_mcp_url)
    df = clean_work_orders(client.get_work_orders())

    assert list(df["sector"]) == ["Mining", "Renewables"]
