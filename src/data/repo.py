"""Fetches from monday.com (mock or live, whichever src.config wires up) and
caches the cleaned DataFrames + quality reports for the life of a session, so
every agent tool call doesn't re-hit the API. Call `.refresh()` to re-pull."""
from __future__ import annotations

import pandas as pd

from src.data.join import join_work_orders_deals
from src.data.normalize import clean_deals, clean_work_orders
from src.data.quality import (
    build_deals_quality_report,
    build_work_orders_quality_report,
    cross_board_sector_gap_notes,
)
from src.monday.client_interface import MondayClient


class DataRepo:
    def __init__(self, client: MondayClient):
        self._client = client
        self._wo_df: pd.DataFrame | None = None
        self._deal_df: pd.DataFrame | None = None
        self._joined_df: pd.DataFrame | None = None
        self._quality_report: dict | None = None

    def refresh(self) -> None:
        self._wo_df = clean_work_orders(self._client.get_work_orders())
        self._deal_df = clean_deals(self._client.get_deals())
        self._joined_df = join_work_orders_deals(self._wo_df, self._deal_df)
        self._quality_report = {
            "work_orders": build_work_orders_quality_report(self._wo_df),
            "deals": build_deals_quality_report(self._deal_df),
            "cross_board_notes": cross_board_sector_gap_notes(self._wo_df, self._deal_df),
        }

    @property
    def work_orders(self) -> pd.DataFrame:
        if self._wo_df is None:
            self.refresh()
        return self._wo_df

    @property
    def deals(self) -> pd.DataFrame:
        if self._deal_df is None:
            self.refresh()
        return self._deal_df

    @property
    def joined(self) -> pd.DataFrame:
        if self._joined_df is None:
            self.refresh()
        return self._joined_df

    @property
    def quality_report(self) -> dict:
        if self._quality_report is None:
            self.refresh()
        return self._quality_report
