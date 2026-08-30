"""Read-only interface both the mock and real monday.com clients implement.

Every item returned is shaped identically regardless of source:
    {"id": str, "name": str, "column_values": [{"id", "title", "type", "text", "value"}]}

This is the one seam between "talking to monday.com" and "everything else" -- the
normalization layer, agent tools, and UI never know or care which implementation
is behind it.
"""
from __future__ import annotations

from typing import Protocol


class MondayClient(Protocol):
    def get_work_orders(self) -> list[dict]:
        """All items from the Work Orders board."""
        ...

    def get_deals(self) -> list[dict]:
        """All items from the Deals board."""
        ...
