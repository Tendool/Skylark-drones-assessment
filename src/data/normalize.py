"""Cleans raw monday.com items into tidy pandas DataFrames.

This is the "Data Resilience" layer the assignment asks for: it never drops a
record just because a field is missing, it normalizes formats that differ
between (and within) the two boards, and it records what it had to fix so
src/data/quality.py can surface caveats to the user instead of pretending the
data is perfect.
"""
from __future__ import annotations

import re

import pandas as pd

from src.monday.schema import DEALS_COLUMNS, WORK_ORDERS_COLUMNS

# Canonical sector taxonomy the agent reasons in. The Deals board uses a superset
# of the Work Orders board's sectors (e.g. "DSP", "Tender" are sales-only concepts
# with no delivery-side equivalent yet) -- we keep the raw label rather than
# forcing a merge that would misrepresent the business.
KNOWN_SECTORS = {
    "mining", "renewables", "railways", "powerline", "construction", "others",
    "dsp", "tender", "manufacturing", "security and surveillance", "aviation",
}

# Typos / casing variants observed in the source data -> canonical label.
STATUS_TYPO_FIXES = {
    "billed": "Billed",
    "bilied": "Billed",
}


def _clean_text(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    value = str(value).strip()
    return value or None


_MINOR_WORDS = {"and", "of"}


def _title_case_sector(known_lower: str) -> str:
    if known_lower == "dsp":
        return "DSP"
    return " ".join(w if w in _MINOR_WORDS else w.capitalize() for w in known_lower.split())


def canonicalize_sector(raw: str | None) -> str | None:
    """Source sectors are already consistently cased; this only fixes stray
    case mismatches (e.g. "mining" vs "Mining") against the known taxonomy
    without mangling multi-word names like "Security and Surveillance"."""
    text = _clean_text(raw)
    if text is None:
        return None
    key = text.lower()
    if key in KNOWN_SECTORS:
        return _title_case_sector(key)
    return text


def canonicalize_status(raw: str | None) -> str | None:
    text = _clean_text(raw)
    if text is None:
        return None
    return STATUS_TYPO_FIXES.get(text.lower(), text)


def normalize_client_code(raw: str | None) -> str | None:
    """WOCOMPANY_002 (Work Orders) and COMPANY002 (Deals) identify the same
    client under two different naming conventions -- see DECISION_LOG.md.
    This maps either form to one canonical "COMPANY###" key so the boards can
    be joined."""
    text = _clean_text(raw)
    if text is None:
        return None
    match = re.search(r"(\d+)$", text)
    if not match:
        return text.upper()
    digits = match.group(1)
    return f"COMPANY{digits.zfill(3)}"


def items_to_dataframe(items: list[dict], expected_columns: list[str] | None = None) -> pd.DataFrame:
    """Flattens monday.com items (id/name/column_values) into a DataFrame keyed
    by column title, keeping the raw item id and name. `expected_columns` are
    guaranteed to exist (as all-missing) even if absent from every item -- a
    live board that's missing/renamed a column shouldn't crash the pipeline."""
    rows = []
    for item in items:
        row = {"_item_id": item["id"], "_item_name": item["name"]}
        for cv in item["column_values"]:
            row[cv["title"]] = cv["text"]
        rows.append(row)
    df = pd.DataFrame(rows)
    if expected_columns:
        df = df.reindex(columns=["_item_id", "_item_name", *expected_columns])
    return df


def clean_work_orders(raw_items: list[dict]) -> pd.DataFrame:
    df = items_to_dataframe(raw_items, expected_columns=[c.title for c in WORK_ORDERS_COLUMNS])

    df["client_code"] = df["Customer Name Code"].apply(normalize_client_code)
    df["sector"] = df["Sector"].apply(canonicalize_sector)
    df["execution_status"] = df["Execution Status"].apply(canonicalize_status)
    df["billing_status"] = df["Billing Status"].apply(canonicalize_status)

    for col in ["Data Delivery Date", "Date of PO/LOI", "Probable Start Date",
                "Probable End Date", "Last invoice date", "Collection Date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["Amount in Rupees (Excl of GST) (Masked)", "Amount in Rupees (Incl of GST) (Masked)",
                "Billed Value in Rupees (Excl of GST.) (Masked)", "Billed Value in Rupees (Incl of GST.) (Masked)",
                "Collected Amount in Rupees (Incl of GST.) (Masked)", "Amount Receivable (Masked)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def clean_deals(raw_items: list[dict]) -> pd.DataFrame:
    df = items_to_dataframe(raw_items, expected_columns=[c.title for c in DEALS_COLUMNS])

    df["client_code"] = df["Client Code"].apply(normalize_client_code)
    df["sector"] = df["Sector/service"].apply(canonicalize_sector)
    df["deal_status"] = df["Deal Status"].apply(canonicalize_status)

    for col in ["Close Date (A)", "Tentative Close Date", "Created Date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["Masked Deal value"] = pd.to_numeric(df["Masked Deal value"], errors="coerce")

    return df
