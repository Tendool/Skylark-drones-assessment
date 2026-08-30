"""Builds a data quality report the agent can quote back to the user instead of
silently presenting incomplete data as if it were complete."""
from __future__ import annotations

import pandas as pd

HIGH_MISSING_THRESHOLD = 50.0  # percent
FULLY_EMPTY_THRESHOLD = 99.0


def missingness_pct(df: pd.DataFrame) -> dict[str, float]:
    return (df.isna().mean() * 100).round(1).to_dict()


def _notes_for_missingness(board_name: str, missing: dict[str, float], ignore_cols: set[str]) -> list[str]:
    notes = []
    fully_empty = [c for c, pct in missing.items() if pct >= FULLY_EMPTY_THRESHOLD and c not in ignore_cols]
    if fully_empty:
        notes.append(
            f"{board_name}: columns {fully_empty} are effectively unused (>{FULLY_EMPTY_THRESHOLD}% empty) "
            "-- likely deprecated or not filled in by the team."
        )
    high_missing = [
        c for c, pct in missing.items()
        if HIGH_MISSING_THRESHOLD <= pct < FULLY_EMPTY_THRESHOLD and c not in ignore_cols
    ]
    if high_missing:
        notes.append(f"{board_name}: columns {high_missing} are missing in over half of records -- treat metrics from them as directional, not exact.")
    return notes


def build_work_orders_quality_report(df: pd.DataFrame, dropped_row_warnings: list[str] | None = None) -> dict:
    missing = missingness_pct(df.drop(columns=["_item_id", "_item_name"], errors="ignore"))
    notes = _notes_for_missingness("Work Orders", missing, ignore_cols=set())

    unmatched_client_codes = int(df["client_code"].isna().sum())
    if unmatched_client_codes:
        notes.append(f"Work Orders: {unmatched_client_codes} row(s) have no usable client code and can't be joined to a Deal.")

    if dropped_row_warnings:
        notes.extend(dropped_row_warnings)

    return {
        "board": "Work Orders",
        "row_count": len(df),
        "missing_pct": missing,
        "notes": notes,
    }


def build_deals_quality_report(df: pd.DataFrame, dropped_row_warnings: list[str] | None = None) -> dict:
    missing = missingness_pct(df.drop(columns=["_item_id", "_item_name"], errors="ignore"))
    notes = _notes_for_missingness("Deals", missing, ignore_cols=set())

    unmatched_client_codes = int(df["client_code"].isna().sum())
    if unmatched_client_codes:
        notes.append(f"Deals: {unmatched_client_codes} row(s) have no usable client code and can't be joined to a Work Order.")

    if dropped_row_warnings:
        notes.append(
            f"Deals: {len(dropped_row_warnings)} row(s) were dropped before loading because they were corrupted "
            "(a spreadsheet header row pasted in as data) -- see DECISION_LOG.md."
        )

    return {
        "board": "Deals",
        "row_count": len(df),
        "missing_pct": missing,
        "notes": notes,
    }


def cross_board_sector_gap_notes(wo_df: pd.DataFrame, deal_df: pd.DataFrame) -> list[str]:
    wo_sectors = set(wo_df["sector"].dropna().unique())
    deal_sectors = set(deal_df["sector"].dropna().unique())
    deal_only = sorted(deal_sectors - wo_sectors)
    if deal_only:
        return [
            f"Sectors {deal_only} appear in the Deals pipeline but have no delivered Work Orders yet -- "
            "either brand-new sectors or not-yet-executed deals."
        ]
    return []
