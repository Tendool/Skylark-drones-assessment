from src.data.normalize import (
    canonicalize_sector,
    canonicalize_status,
    clean_deals,
    clean_work_orders,
    normalize_client_code,
)


def test_normalize_client_code_strips_wo_prefix():
    assert normalize_client_code("WOCOMPANY_002") == "COMPANY002"


def test_normalize_client_code_already_canonical():
    assert normalize_client_code("COMPANY089") == "COMPANY089"


def test_normalize_client_code_handles_missing():
    assert normalize_client_code(None) is None
    assert normalize_client_code("") is None


def test_canonicalize_sector_fixes_case_without_mangling_multiword():
    assert canonicalize_sector("security and surveillance") == "Security and Surveillance"
    assert canonicalize_sector("MINING") == "Mining"
    assert canonicalize_sector("Renewables") == "Renewables"


def test_canonicalize_sector_passes_through_unknown_values():
    assert canonicalize_sector("Some New Sector") == "Some New Sector"


def test_canonicalize_status_fixes_known_typo():
    assert canonicalize_status("BIlled") == "Billed"
    assert canonicalize_status("Completed") == "Completed"


def _item(item_id, name, **cols):
    return {
        "id": item_id,
        "name": name,
        "column_values": [
            {"id": k, "title": title, "type": ctype, "text": text, "value": None}
            for k, (title, ctype, text) in cols.items()
        ],
    }


def test_clean_work_orders_parses_dates_and_numbers():
    items = [
        _item(
            "WO-0",
            "SER-1",
            deal_name_masked=("Deal name masked", "text", "Alias"),
            customer_name_code=("Customer Name Code", "text", "WOCOMPANY_007"),
            sector=("Sector", "status", "mining"),
            execution_status=("Execution Status", "status", "Completed"),
            probable_start=("Probable Start Date", "date", "2025-05-01"),
            probable_end=("Probable End Date", "date", "not-a-date"),
            amount_incl=("Amount in Rupees (Incl of GST) (Masked)", "numbers", "1000.5"),
        )
    ]
    df = clean_work_orders(items)
    assert df.loc[0, "client_code"] == "COMPANY007"
    assert df.loc[0, "sector"] == "Mining"
    assert df.loc[0, "Probable Start Date"].strftime("%Y-%m-%d") == "2025-05-01"
    assert df.loc[0, "Probable End Date"] is not None
    assert df.loc[0, "Probable End Date"] != df.loc[0, "Probable End Date"]  # NaT != NaT
    assert df.loc[0, "Amount in Rupees (Incl of GST) (Masked)"] == 1000.5


def test_clean_deals_normalizes_client_code():
    items = [
        _item(
            "DEAL-0",
            "Sakura",
            client_code=("Client Code", "text", "COMPANY042"),
            deal_status=("Deal Status", "status", "Won"),
            sector_service=("Sector/service", "status", "Renewables"),
            masked_deal_value=("Masked Deal value", "numbers", "500000"),
        )
    ]
    df = clean_deals(items)
    assert df.loc[0, "client_code"] == "COMPANY042"
    assert df.loc[0, "Masked Deal value"] == 500000.0
