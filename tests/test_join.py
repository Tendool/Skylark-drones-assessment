import pandas as pd

from src.data.join import clients_without_deals, clients_without_work_orders, join_work_orders_deals


def test_join_matches_on_normalized_client_code():
    wo_df = pd.DataFrame({"client_code": ["COMPANY001", "COMPANY002"], "sector": ["Mining", "Powerline"]})
    deal_df = pd.DataFrame({"client_code": ["COMPANY002", "COMPANY003"], "sector": ["Powerline", "Railways"]})

    joined = join_work_orders_deals(wo_df, deal_df)

    assert set(joined["client_code"]) == {"COMPANY001", "COMPANY002", "COMPANY003"}
    assert clients_without_deals(joined) == ["COMPANY001"]
    assert clients_without_work_orders(joined) == ["COMPANY003"]
