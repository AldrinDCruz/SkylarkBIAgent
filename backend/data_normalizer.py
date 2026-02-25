"""
data_normalizer.py
Cleans and normalizes raw Monday.com data into structured dicts.
"""

import re
from dateutil import parser as dateparser
from typing import Any, Optional, Tuple


# ─────────────────────────────────────────
# Low-level field cleaners
# ─────────────────────────────────────────

def clean_amount(value: Any) -> float:
    """Handle #VALUE!, empty, None, comma-separated numbers → float."""
    if value is None:
        return 0.0
    text = str(value).strip()
    if text in ("", "#VALUE!", "nan", "N/A", "-"):
        return 0.0
    # Remove currency symbols and commas
    text = re.sub(r"[₹,\s]", "", text)
    try:
        return float(text)
    except ValueError:
        return 0.0


def clean_quantity(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """Extract numeric part from '2186.54 HA', '350 KM', '7 mines' → (number, unit)."""
    if not value:
        return None, None
    text = str(value).strip()
    match = re.match(r"^([\d,\.]+)\s*(.*)?$", text)
    if match:
        num_str = match.group(1).replace(",", "")
        unit = match.group(2).strip() or None
        try:
            return float(num_str), unit
        except ValueError:
            pass
    return None, text


def normalize_date(value: Any) -> Optional[str]:
    """Try multiple date formats → ISO string or None."""
    if not value:
        return None
    text = str(value).strip()
    if text in ("", "nan", "N/A", "-"):
        return None
    try:
        return dateparser.parse(text, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return None


def is_header_row(item: dict) -> bool:
    """Filter duplicate header rows embedded in the CSV-imported data."""
    status_val = item.get("deal_status", "")
    return status_val in (
        "Deal Status", "Close Date (A)", "Execution Status",
        "Status", "deal_status", "WO Status"
    )


# ─────────────────────────────────────────
# Stage label mapping
# ─────────────────────────────────────────

STAGE_LABELS = {
    "A": "Lead",
    "B": "SQL",
    "C": "Demo Done",
    "D": "Feasibility",
    "E": "Proposal Sent",
    "F": "Negotiations",
    "G": "Won",
    "H": "WO Received",
    "I": "POC",
    "J": "Invoice Sent",
    "K": "Amount Accrued",
    "L": "Project Lost",
    "M": "On Hold",
    "N": "Not Relevant",
    "O": "Not Relevant",
}


def map_stage(raw: Any) -> str:
    if not raw:
        return "Unknown"
    text = str(raw).strip().upper()
    # Match single letter stage like "A", "B - ...", "Stage B", etc.
    match = re.match(r"^([A-O])\b", text)
    if match:
        letter = match.group(1)
        return STAGE_LABELS.get(letter, f"Stage {letter}")
    return text.title() if text else "Unknown"


# ─────────────────────────────────────────
# Board-level normalizers
# ─────────────────────────────────────────

def _get(col_values: list, col_id: str, fallback_title: str = "") -> str:
    """Extract text from column_values by id or title."""
    for cv in col_values:
        if cv.get("id") == col_id or cv.get("title", "") == fallback_title:
            return (cv.get("text") or "").strip()
    return ""


def normalize_deals(raw_items: list) -> list:
    """
    Normalize raw Monday.com items from the Deals board.
    We map by column position/title since IDs are board-specific.
    The normalizer builds a dict from column_values list by iterating all.
    """
    normalized = []
    for item in raw_items:
        col_vals = item.get("column_values", [])
        # Build a flat dict: {title_lower: text} for looser matching
        cols = {}
        for cv in col_vals:
            title = (cv.get("title") or cv.get("id") or "").lower().strip()
            text = (cv.get("text") or "").strip()
            cols[title] = text

        deal = {
            "id": item.get("id", ""),
            "name": (item.get("name") or "").strip(),
            "owner_code": _lookup(cols, ["owner code", "owner", "bd/kam personnel code"]),
            "client_code": _lookup(cols, ["client code", "client", "customer name code"]),
            "deal_status": _lookup(cols, ["deal status", "status"]),
            "close_date_actual": normalize_date(_lookup(cols, ["close date (a)", "close date"])),
            "closure_probability": _lookup(cols, ["closure probability", "probability"]),
            "deal_value": clean_amount(_lookup(cols, ["masked deal value", "deal value", "value"])),
            "tentative_close_date": normalize_date(_lookup(cols, ["tentative close date", "tentative close"])),
            "deal_stage": map_stage(_lookup(cols, ["deal stage", "stage"])),
            "product": _lookup(cols, ["product deal", "product"]),
            "sector": _lookup(cols, ["sector/service", "sector"]),
            "created_date": normalize_date(_lookup(cols, ["created date"])),
        }

        # Filter header rows
        if is_header_row(deal):
            continue

        normalized.append(deal)

    return normalized


def normalize_work_orders(raw_items: list) -> list:
    """Normalize raw Monday.com items from the Work Orders board."""
    normalized = []
    for item in raw_items:
        col_vals = item.get("column_values", [])
        cols = {}
        for cv in col_vals:
            title = (cv.get("title") or cv.get("id") or "").lower().strip()
            text = (cv.get("text") or "").strip()
            cols[title] = text

        wo = {
            "id": item.get("id", ""),
            "deal_name": (item.get("name") or "").strip(),
            "customer_code": _lookup(cols, ["customer name code", "client code"]),
            "execution_status": _lookup(cols, ["execution status", "status"]),
            "probable_start_date": normalize_date(_lookup(cols, ["probable start date"])),
            "probable_end_date": normalize_date(_lookup(cols, ["probable end date"])),
            "sector": _lookup(cols, ["sector", "sector/service"]),
            "amount_excl_gst": clean_amount(_lookup(cols, ["amount excl gst (masked)", "amount excl gst"])),
            "amount_incl_gst": clean_amount(_lookup(cols, ["amount incl gst (masked)", "amount incl gst"])),
            "billed_value_excl_gst": clean_amount(_lookup(cols, ["billed value excl gst (masked)", "billed value excl gst"])),
            "collected_amount_incl_gst": clean_amount(_lookup(cols, ["collected amount incl gst (masked)", "collected amount"])),
            "amount_receivable": clean_amount(_lookup(cols, ["amount receivable", "ar"])),
            "billing_status": _lookup(cols, ["billing status", "status"]),
            "wo_status": _lookup(cols, ["wo status (billed)", "wo status"]),
        }

        # Filter header rows
        if wo.get("execution_status") in ("Execution Status", "Status"):
            continue

        normalized.append(wo)

    return normalized


def _lookup(cols: dict, keys: list) -> str:
    """Try multiple key names and return first non-empty match."""
    for key in keys:
        val = cols.get(key, "")
        if val:
            return val
    return ""
