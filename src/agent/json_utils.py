"""Converts pandas-flavored values (Timestamp, NaN, numpy scalars) into plain
JSON-safe Python so tool results can be handed straight to the LLM."""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

import pandas as pd


def jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return None if pd.isna(value) else value.strftime("%Y-%m-%d")
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if hasattr(value, "item"):  # numpy scalar
        return jsonable(value.item())
    if isinstance(value, float):
        return round(value, 2)
    return value


def records(df: pd.DataFrame, columns: list[str], limit: int | None = None) -> list[dict]:
    view = df[columns]
    if limit is not None:
        view = view.head(limit)
    return [jsonable(row) for row in view.to_dict(orient="records")]
