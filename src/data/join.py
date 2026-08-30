"""Cross-board join between Work Orders and Deals.

Joining on `Deal name masked` / `Deal Name` would be wrong: it's a masked alias
that gets reused across many distinct clients (see DECISION_LOG.md), not a
unique key. The reliable join key is the client code, once normalized to a
shared format (normalize.normalize_client_code) -- Work Orders spells it
"WOCOMPANY_002", Deals spells the same client "COMPANY002".
"""
from __future__ import annotations

import pandas as pd


def join_work_orders_deals(wo_df: pd.DataFrame, deal_df: pd.DataFrame) -> pd.DataFrame:
    return wo_df.merge(
        deal_df,
        on="client_code",
        how="outer",
        suffixes=(" (Work Order)", " (Deal)"),
        indicator=True,
    )


def clients_without_deals(joined: pd.DataFrame) -> list[str]:
    """Clients with delivered work but no matching pipeline record -- e.g. a
    deal logged before this tracker existed, or a client-code typo."""
    return sorted(joined.loc[joined["_merge"] == "left_only", "client_code"].dropna().unique().tolist())


def clients_without_work_orders(joined: pd.DataFrame) -> list[str]:
    """Clients in the pipeline with no delivery yet -- expected for open/lost deals,
    worth a second look for deals marked Won."""
    return sorted(joined.loc[joined["_merge"] == "right_only", "client_code"].dropna().unique().tolist())
