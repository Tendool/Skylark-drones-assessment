"""Tool implementations + their Anthropic-format schemas.

Each function takes the shared DataRepo plus the LLM-supplied arguments and
returns a small, JSON-safe dict -- deliberately summarized/aggregated rather
than dumping raw rows, so the model reasons over numbers it can trust instead
of re-deriving them from a wall of text.

Money columns are reported individually (contracted / billed / collected /
receivable) rather than collapsed into one "revenue" figure, because which of
those a founder means by "revenue" is genuinely ambiguous in this data -- see
DECISION_LOG.md. The system prompt tells the model to state that assumption
out loud rather than silently pick one.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from src.agent.json_utils import jsonable, records
from src.data.repo import DataRepo

CLOSURE_PROBABILITY_WEIGHT = {"high": 0.8, "medium": 0.5, "low": 0.2}
OPEN_LIKE_STATUSES = {"ongoing", "not started", "pause / struck", "details pending from client", "partial completed"}


def _ci_eq(series: pd.Series, value: str) -> pd.Series:
    return series.str.casefold() == value.casefold()


def _apply_filters(df: pd.DataFrame, **filters) -> pd.DataFrame:
    for col, value in filters.items():
        if value is None:
            continue
        df = df[_ci_eq(df[col].fillna(""), value)]
    return df


def _date_window(df: pd.DataFrame, date_col: str, date_from: str | None, date_to: str | None) -> pd.DataFrame:
    if date_from:
        df = df[df[date_col] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df[date_col] <= pd.to_datetime(date_to)]
    return df


def _money_totals(df: pd.DataFrame, columns: dict[str, str]) -> dict:
    out = {}
    for label, col in columns.items():
        series = df[col]
        out[label] = {
            "sum": jsonable(series.sum()),
            "known_records": int(series.notna().sum()),
            "missing_records": int(series.isna().sum()),
        }
    return out


def get_data_quality_report(repo: DataRepo) -> dict:
    return repo.quality_report


def query_work_orders(
    repo: DataRepo,
    sector: str | None = None,
    execution_status: str | None = None,
    client_code: str | None = None,
    probable_start_from: str | None = None,
    probable_end_to: str | None = None,
    limit: int = 20,
) -> dict:
    df = _apply_filters(repo.work_orders, sector=sector, execution_status=execution_status, client_code=client_code)
    if probable_start_from:
        df = df[df["Probable Start Date"] >= pd.to_datetime(probable_start_from)]
    if probable_end_to:
        df = df[df["Probable End Date"] <= pd.to_datetime(probable_end_to)]

    display_cols = [
        "_item_name", "Deal name masked", "client_code", "sector", "execution_status",
        "Probable Start Date", "Probable End Date",
        "Amount in Rupees (Incl of GST) (Masked)", "Amount Receivable (Masked)",
    ]
    return {
        "matched_count": len(df),
        "sample": records(df, display_cols, limit=limit),
        "money_totals": _money_totals(df, {
            "contracted_value_incl_gst": "Amount in Rupees (Incl of GST) (Masked)",
            "billed_value_incl_gst": "Billed Value in Rupees (Incl of GST.) (Masked)",
            "collected_amount_incl_gst": "Collected Amount in Rupees (Incl of GST.) (Masked)",
            "amount_receivable": "Amount Receivable (Masked)",
        }),
        "execution_status_breakdown": jsonable(df["execution_status"].value_counts(dropna=False).to_dict()),
    }


def query_deals(
    repo: DataRepo,
    sector: str | None = None,
    deal_status: str | None = None,
    deal_stage: str | None = None,
    client_code: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    tentative_close_from: str | None = None,
    tentative_close_to: str | None = None,
    limit: int = 20,
) -> dict:
    df = _apply_filters(
        repo.deals, sector=sector, deal_status=deal_status, **{"Deal Stage": deal_stage}, client_code=client_code
    )
    df = _date_window(df, "Created Date", created_from, created_to)
    df = _date_window(df, "Tentative Close Date", tentative_close_from, tentative_close_to)

    display_cols = [
        "_item_name", "client_code", "sector", "deal_status", "Deal Stage",
        "Closure Probability", "Masked Deal value", "Tentative Close Date", "Created Date",
    ]
    return {
        "matched_count": len(df),
        "sample": records(df, display_cols, limit=limit),
        "deal_value_total": _money_totals(df, {"masked_deal_value": "Masked Deal value"}),
        "stage_breakdown": jsonable(df["Deal Stage"].value_counts(dropna=False).to_dict()),
        "status_breakdown": jsonable(df["deal_status"].value_counts(dropna=False).to_dict()),
    }


def pipeline_summary(
    repo: DataRepo,
    sector: str | None = None,
    date_field: str = "Created Date",
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    if date_field not in {"Created Date", "Tentative Close Date", "Close Date (A)"}:
        date_field = "Created Date"

    df = _apply_filters(repo.deals, sector=sector)
    df = _date_window(df, date_field, date_from, date_to)

    weight = df["Closure Probability"].str.lower().map(CLOSURE_PROBABILITY_WEIGHT)
    weighted_value = (df["Masked Deal value"] * weight).sum()

    def _breakdown(group_col: str) -> list[dict]:
        grouped = df.groupby(group_col, dropna=False)["Masked Deal value"].agg(
            deal_count="size", value_sum="sum", deals_with_known_value="count"
        )
        return jsonable(grouped.reset_index().to_dict(orient="records"))

    return {
        "date_field_used": date_field,
        "matched_deal_count": len(df),
        "by_stage": _breakdown("Deal Stage"),
        "by_status": _breakdown("deal_status"),
        "total_pipeline_value_unweighted": jsonable(df["Masked Deal value"].sum()),
        "total_pipeline_value_probability_weighted": jsonable(weighted_value),
        "deals_missing_value": int(df["Masked Deal value"].isna().sum()),
        "deals_missing_closure_probability": int(df["Closure Probability"].isna().sum()),
    }


def revenue_summary(
    repo: DataRepo,
    sector: str | None = None,
    date_field: str = "Probable Start Date",
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    if date_field not in {"Probable Start Date", "Probable End Date", "Last invoice date", "Date of PO/LOI"}:
        date_field = "Probable Start Date"

    df = _apply_filters(repo.work_orders, sector=sector)
    df = _date_window(df, date_field, date_from, date_to)

    return {
        "date_field_used": date_field,
        "matched_work_order_count": len(df),
        "money_totals": _money_totals(df, {
            "contracted_value_incl_gst": "Amount in Rupees (Incl of GST) (Masked)",
            "billed_value_incl_gst": "Billed Value in Rupees (Incl of GST.) (Masked)",
            "collected_amount_incl_gst": "Collected Amount in Rupees (Incl of GST.) (Masked)",
            "amount_receivable": "Amount Receivable (Masked)",
        }),
        "by_sector": jsonable(
            df.groupby("sector", dropna=False)["Amount in Rupees (Incl of GST) (Masked)"]
            .agg(work_order_count="size", contracted_value_sum="sum", known_value_count="count")
            .reset_index()
            .to_dict(orient="records")
        ),
    }


def operational_health(repo: DataRepo, sector: str | None = None) -> dict:
    df = _apply_filters(repo.work_orders, sector=sector)
    today = pd.Timestamp(dt.date.today())

    is_open_status = df["execution_status"].str.lower().isin(OPEN_LIKE_STATUSES)
    overdue = df[is_open_status & df["Probable End Date"].notna() & (df["Probable End Date"] < today)]

    return {
        "work_order_count": len(df),
        "execution_status_breakdown": jsonable(df["execution_status"].value_counts(dropna=False).to_dict()),
        "invoice_status_breakdown": jsonable(df["Invoice Status"].value_counts(dropna=False).to_dict()),
        "overdue_count": len(overdue),
        "overdue_sample": records(
            overdue, ["_item_name", "Deal name masked", "client_code", "sector", "execution_status", "Probable End Date"], limit=15
        ),
    }


def sector_performance(repo: DataRepo, sector: str) -> dict:
    return {
        "sector": sector,
        "pipeline": pipeline_summary(repo, sector=sector),
        "revenue": revenue_summary(repo, sector=sector),
        "operations": operational_health(repo, sector=sector),
    }


def generate_leadership_summary(repo: DataRepo, sector: str | None = None) -> dict:
    """The optional 'help prepare data for leadership updates' feature: a
    structured, ready-to-paste executive brief -- pipeline health, delivery
    health, revenue, and the data-quality caveats a founder should know before
    repeating these numbers externally."""
    quality = repo.quality_report
    return {
        "scope": sector or "All sectors",
        "pipeline": pipeline_summary(repo, sector=sector),
        "revenue": revenue_summary(repo, sector=sector),
        "operations": operational_health(repo, sector=sector),
        "data_quality_caveats": (
            quality["work_orders"]["notes"] + quality["deals"]["notes"] + quality["cross_board_notes"]
        ),
    }


TOOL_SCHEMAS = [
    {
        "name": "get_data_quality_report",
        "description": "Get the current data-quality report for both boards: missingness by column, dropped/corrupt rows, and known cross-board gaps. Call this whenever the user asks about data quality, or before quoting a number that might be based on sparse data.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "query_work_orders",
        "description": "Search/filter the Work Orders (project execution) board and get aggregate totals + a sample of matching rows.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string", "description": "e.g. Mining, Renewables, Railways, Powerline, Construction, Others"},
                "execution_status": {"type": "string", "description": "e.g. Completed, Ongoing, Not Started"},
                "client_code": {"type": "string"},
                "probable_start_from": {"type": "string", "description": "ISO date, inclusive lower bound on Probable Start Date"},
                "probable_end_to": {"type": "string", "description": "ISO date, inclusive upper bound on Probable End Date"},
                "limit": {"type": "integer", "description": "Max sample rows to return, default 20"},
            },
        },
    },
    {
        "name": "query_deals",
        "description": "Search/filter the Deals (sales pipeline) board and get aggregate totals + a sample of matching rows.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string"},
                "deal_status": {"type": "string", "description": "Won, Dead, Open, On Hold"},
                "deal_stage": {"type": "string", "description": "e.g. 'A. Lead Generated', 'G. Project Won'"},
                "client_code": {"type": "string"},
                "created_from": {"type": "string", "description": "ISO date"},
                "created_to": {"type": "string", "description": "ISO date"},
                "tentative_close_from": {"type": "string", "description": "ISO date"},
                "tentative_close_to": {"type": "string", "description": "ISO date"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "pipeline_summary",
        "description": "Sales pipeline health: deal counts/value by stage and status, and probability-weighted pipeline value. Use for 'how's pipeline looking' style questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string"},
                "date_field": {"type": "string", "enum": ["Created Date", "Tentative Close Date", "Close Date (A)"], "description": "Which date field to filter the time window on -- state this choice to the user."},
                "date_from": {"type": "string", "description": "ISO date"},
                "date_to": {"type": "string", "description": "ISO date"},
            },
        },
    },
    {
        "name": "revenue_summary",
        "description": "Delivery-side money: contracted value, billed value, collected amount, and receivables from Work Orders, optionally by sector/date window. There is no single unambiguous 'revenue' column in this data -- report the breakdown, don't collapse it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string"},
                "date_field": {"type": "string", "enum": ["Probable Start Date", "Probable End Date", "Last invoice date", "Date of PO/LOI"], "description": "Which date field to filter the time window on -- state this choice to the user."},
                "date_from": {"type": "string", "description": "ISO date"},
                "date_to": {"type": "string", "description": "ISO date"},
            },
        },
    },
    {
        "name": "operational_health",
        "description": "Delivery/execution status breakdown for Work Orders, including overdue projects (past their probable end date but not completed).",
        "input_schema": {"type": "object", "properties": {"sector": {"type": "string"}}},
    },
    {
        "name": "sector_performance",
        "description": "One-call cross-board view of a single sector: pipeline + revenue + operations. Use this for 'how's the X sector doing' questions instead of calling the three tools separately.",
        "input_schema": {"type": "object", "properties": {"sector": {"type": "string"}}, "required": ["sector"]},
    },
    {
        "name": "generate_leadership_summary",
        "description": "Generate a structured executive brief (pipeline, revenue, operations, and data-quality caveats) suitable for pasting into a leadership update, optionally scoped to one sector.",
        "input_schema": {"type": "object", "properties": {"sector": {"type": "string"}}},
    },
]

TOOL_IMPLEMENTATIONS = {
    "get_data_quality_report": get_data_quality_report,
    "query_work_orders": query_work_orders,
    "query_deals": query_deals,
    "pipeline_summary": pipeline_summary,
    "revenue_summary": revenue_summary,
    "operational_health": operational_health,
    "sector_performance": sector_performance,
    "generate_leadership_summary": generate_leadership_summary,
}


def run_tool(repo: DataRepo, name: str, arguments: dict) -> dict:
    if name not in TOOL_IMPLEMENTATIONS:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return TOOL_IMPLEMENTATIONS[name](repo, **arguments)
    except Exception as exc:  # noqa: BLE001 -- surfaced to the model as a tool error, not a crash
        return {"error": f"{type(exc).__name__}: {exc}"}
