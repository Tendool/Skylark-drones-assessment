"""
Board/column definitions for the two monday.com boards this project reads from.

These are *our* definitions: `scripts/import_to_monday.py` uses them to create the
boards with matching column types, and both the mock and real monday.com clients
return items shaped as {"id": ..., "name": ..., "column_values": [{"id", "title", "type", "text", "value"}]}
using these column ids/titles, so the rest of the codebase never has to care whether
the data came from a live API call or a local fixture.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnDef:
    id: str
    title: str
    type: str  # monday.com column type: text, long_text, status, dropdown, date, numbers


WORK_ORDERS_BOARD_NAME = "Work Orders"
DEALS_BOARD_NAME = "Deals"

WORK_ORDERS_COLUMNS: list[ColumnDef] = [
    ColumnDef("deal_name_masked", "Deal name masked", "text"),
    ColumnDef("customer_name_code", "Customer Name Code", "text"),
    ColumnDef("nature_of_work", "Nature of Work", "status"),
    ColumnDef("last_exec_month_recurring", "Last executed month of recurring project", "text"),
    ColumnDef("execution_status", "Execution Status", "status"),
    ColumnDef("data_delivery_date", "Data Delivery Date", "date"),
    ColumnDef("po_loi_date", "Date of PO/LOI", "date"),
    ColumnDef("document_type", "Document Type", "status"),
    ColumnDef("probable_start_date", "Probable Start Date", "date"),
    ColumnDef("probable_end_date", "Probable End Date", "date"),
    ColumnDef("bd_kam_code", "BD/KAM Personnel code", "text"),
    ColumnDef("sector", "Sector", "status"),
    ColumnDef("type_of_work", "Type of Work", "text"),
    ColumnDef("skylark_platform_in_deal", "Is any Skylark software platform part of the client deliverables in this deal?", "status"),
    ColumnDef("last_invoice_date", "Last invoice date", "date"),
    ColumnDef("latest_invoice_no", "latest invoice no.", "text"),
    ColumnDef("amount_excl_gst", "Amount in Rupees (Excl of GST) (Masked)", "numbers"),
    ColumnDef("amount_incl_gst", "Amount in Rupees (Incl of GST) (Masked)", "numbers"),
    ColumnDef("billed_value_excl_gst", "Billed Value in Rupees (Excl of GST.) (Masked)", "numbers"),
    ColumnDef("billed_value_incl_gst", "Billed Value in Rupees (Incl of GST.) (Masked)", "numbers"),
    ColumnDef("collected_amount_incl_gst", "Collected Amount in Rupees (Incl of GST.) (Masked)", "numbers"),
    ColumnDef("to_be_billed_excl_gst", "Amount to be billed in Rs. (Exl. of GST) (Masked)", "numbers"),
    ColumnDef("to_be_billed_incl_gst", "Amount to be billed in Rs. (Incl. of GST) (Masked)", "numbers"),
    ColumnDef("amount_receivable", "Amount Receivable (Masked)", "numbers"),
    ColumnDef("ar_priority_account", "AR Priority account", "status"),
    ColumnDef("quantity_by_ops", "Quantity by Ops", "numbers"),
    ColumnDef("quantities_as_per_po", "Quantities as per PO", "text"),
    ColumnDef("quantity_billed_till_date", "Quantity billed (till date)", "numbers"),
    ColumnDef("balance_in_quantity", "Balance in quantity", "numbers"),
    ColumnDef("invoice_status", "Invoice Status", "status"),
    ColumnDef("expected_billing_month", "Expected Billing Month", "text"),
    ColumnDef("actual_billing_month", "Actual Billing Month", "text"),
    ColumnDef("actual_collection_month", "Actual Collection Month", "text"),
    ColumnDef("wo_status_billed", "WO Status (billed)", "status"),
    ColumnDef("collection_status", "Collection status", "status"),
    ColumnDef("collection_date", "Collection Date", "date"),
    ColumnDef("billing_status", "Billing Status", "status"),
]

# Item name in the Work Orders board is the Serial # (unique per row in source data).
WORK_ORDERS_NAME_SOURCE_COLUMN = "Serial #"

DEALS_COLUMNS: list[ColumnDef] = [
    ColumnDef("owner_code", "Owner code", "text"),
    ColumnDef("client_code", "Client Code", "text"),
    ColumnDef("deal_status", "Deal Status", "status"),
    ColumnDef("close_date_actual", "Close Date (A)", "date"),
    ColumnDef("closure_probability", "Closure Probability", "status"),
    ColumnDef("masked_deal_value", "Masked Deal value", "numbers"),
    ColumnDef("tentative_close_date", "Tentative Close Date", "date"),
    ColumnDef("deal_stage", "Deal Stage", "status"),
    ColumnDef("product_deal", "Product deal", "text"),
    ColumnDef("sector_service", "Sector/service", "status"),
    ColumnDef("created_date", "Created Date", "date"),
]

# Item name in the Deals board is the Deal Name (NOT unique -- it's a masked alias
# reused across many distinct clients; see DECISION_LOG.md).
DEALS_NAME_SOURCE_COLUMN = "Deal Name"
