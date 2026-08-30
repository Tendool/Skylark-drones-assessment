import pandas as pd

from src.monday.build_items import rows_to_items
from src.monday.schema import ColumnDef

COLUMNS = [ColumnDef("status_col", "Status", "status"), ColumnDef("stage_col", "Stage", "status")]


def test_rows_to_items_builds_expected_shape():
    df = pd.DataFrame({"Name": ["Row A"], "Status": ["Open"], "Stage": ["Lead"]})
    items, warnings = rows_to_items(df, COLUMNS, "Name", "T")

    assert warnings == []
    assert len(items) == 1
    assert items[0]["name"] == "Row A"
    values = {cv["id"]: cv["text"] for cv in items[0]["column_values"]}
    assert values == {"status_col": "Open", "stage_col": "Lead"}


def test_rows_to_items_drops_corrupted_header_echo_row():
    df = pd.DataFrame(
        {"Name": ["Real row", "Corrupted"], "Status": ["Open", "Status"], "Stage": ["Lead", "Stage"]}
    )
    items, warnings = rows_to_items(df, COLUMNS, "Name", "T")

    assert len(items) == 1
    assert items[0]["name"] == "Real row"
    assert len(warnings) == 1
    assert "corrupted" in warnings[0]
