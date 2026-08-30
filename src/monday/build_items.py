"""
Turns a raw source dataframe (one row per work order / deal) into monday.com-shaped
items: [{"id", "name", "column_values": [{"id", "title", "type", "text", "value"}]}].

Shared by scripts/import_to_monday.py (used for both the local mock fixtures and the
real monday.com push) so the row->item mapping only exists in one place.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any

import pandas as pd

from .schema import ColumnDef


def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return pd.isna(v) if not isinstance(v, (list, dict)) else False


def _cell(value: Any, col: ColumnDef) -> dict:
    if _is_missing(value):
        return {"id": col.id, "title": col.title, "type": col.type, "text": None, "value": None}

    if col.type == "date":
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return {"id": col.id, "title": col.title, "type": col.type, "text": None, "value": None}
        iso = ts.strftime("%Y-%m-%d")
        return {
            "id": col.id,
            "title": col.title,
            "type": col.type,
            "text": iso,
            "value": json.dumps({"date": iso}),
        }

    if col.type == "numbers":
        try:
            num = float(value)
        except (TypeError, ValueError):
            return {"id": col.id, "title": col.title, "type": col.type, "text": str(value), "value": None}
        text = str(int(num)) if num.is_integer() else str(num)
        return {"id": col.id, "title": col.title, "type": col.type, "text": text, "value": json.dumps(num)}

    text = str(value).strip()
    return {
        "id": col.id,
        "title": col.title,
        "type": col.type,
        "text": text,
        "value": json.dumps({"label": text}) if col.type == "status" else json.dumps(text),
    }


def rows_to_items(
    df: pd.DataFrame,
    columns: list[ColumnDef],
    name_source_column: str,
    id_prefix: str,
) -> tuple[list[dict], list[str]]:
    """Returns (items, warnings). A row is dropped (and warned about) when it is a
    corrupted embedded-header row -- i.e. a data cell literally equals its own column
    header, which is how a spreadsheet re-paste artifact shows up in this dataset."""
    items: list[dict] = []
    warnings: list[str] = []

    for idx, row in df.iterrows():
        header_echo = [c.title for c in columns if str(row.get(c.title, "")).strip() == c.title]
        if len(header_echo) >= 2:
            warnings.append(
                f"Dropped row {idx} ({id_prefix}): looks like a corrupted embedded header "
                f"row (columns echoing their own header: {header_echo})."
            )
            continue

        name = row.get(name_source_column)
        name = "" if _is_missing(name) else str(name).strip()

        items.append(
            {
                "id": f"{id_prefix}-{idx}",
                "name": name,
                "column_values": [_cell(row.get(c.title), c) for c in columns],
            }
        )

    return items, warnings
