import pytest

from src.agent.tools import TOOL_IMPLEMENTATIONS, run_tool
from src.data.repo import DataRepo
from src.monday.mock_client import MockMondayClient


@pytest.fixture(scope="module")
def repo():
    return DataRepo(MockMondayClient())


def test_all_tools_run_without_error(repo):
    for name in TOOL_IMPLEMENTATIONS:
        args = {"sector": "Renewables"} if name != "get_data_quality_report" else {}
        result = run_tool(repo, name, args)
        assert "error" not in result, f"{name} raised: {result.get('error')}"


def test_query_work_orders_filters_by_sector_and_matches_manual_count(repo):
    result = run_tool(repo, "query_work_orders", {"sector": "Mining"})
    manual_count = (repo.work_orders["sector"] == "Mining").sum()
    assert result["matched_count"] == manual_count


def test_unknown_tool_reports_error_instead_of_raising(repo):
    result = run_tool(repo, "not_a_real_tool", {})
    assert "error" in result


def test_sector_performance_requires_sector_argument(repo):
    result = run_tool(repo, "sector_performance", {})
    assert "error" in result  # missing required 'sector' -> TypeError caught and surfaced


def test_generate_leadership_summary_includes_caveats(repo):
    result = run_tool(repo, "generate_leadership_summary", {})
    assert isinstance(result["data_quality_caveats"], list)
    assert len(result["data_quality_caveats"]) > 0
