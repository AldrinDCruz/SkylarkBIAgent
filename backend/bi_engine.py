"""
bi_engine.py
Business Intelligence analytics functions operating on normalized data dicts.
"""

from datetime import date, datetime
from typing import Any
from collections import defaultdict


def _today() -> date:
    return date.today()


def _parse_date(d: Any) -> Any:
    if not d:
        return None
    try:
        return datetime.strptime(str(d), "%Y-%m-%d").date()
    except Exception:
        return None


def _fmt_inr(amount: float) -> str:
    """Format a number in Indian style: Cr / L / K."""
    if amount >= 1e7:
        return f"₹{amount/1e7:.2f} Cr"
    elif amount >= 1e5:
        return f"₹{amount/1e5:.2f} L"
    elif amount >= 1e3:
        return f"₹{amount/1e3:.1f}K"
    return f"₹{amount:.0f}"


# ─────────────────────────────────────────
# DEALS analysis
# ─────────────────────────────────────────

def pipeline_summary(deals: list) -> dict:
    """Comprehensive pipeline analysis."""
    total_deals = len(deals)
    status_counts = defaultdict(int)
    sector_values = defaultdict(float)
    sector_counts = defaultdict(lambda: {"won": 0, "dead": 0, "open": 0})
    stage_counts = defaultdict(int)
    owner_values = defaultdict(float)
    prob_values = {"High": 0.0, "Medium": 0.0, "Low": 0.0, "Unknown": 0.0}
    open_pipeline_value = 0.0
    won_value = 0.0
    zero_value_count = 0

    for d in deals:
        status = (d.get("deal_status") or "Unknown").strip()
        status_counts[status] += 1
        val = d.get("deal_value", 0.0)
        sector = (d.get("sector") or "Unknown").strip()
        stage = (d.get("deal_stage") or "Unknown").strip()
        owner = (d.get("owner_code") or "Unknown").strip()
        prob = (d.get("closure_probability") or "Unknown").strip()

        if val == 0:
            zero_value_count += 1

        if status.lower() == "open":
            open_pipeline_value += val
            sector_values[sector] += val
        elif status.lower() == "won":
            won_value += val
            sector_counts[sector]["won"] += 1
        if status.lower() == "dead":
            sector_counts[sector]["dead"] += 1
        if status.lower() in ("open", "on hold"):
            sector_counts[sector]["open"] += 1

        stage_counts[stage] += 1
        owner_values[owner] += val

        if prob in prob_values:
            prob_values[prob] += val
        else:
            prob_values["Unknown"] += val

    # Sort sector values descending
    top_sectors = sorted(sector_values.items(), key=lambda x: x[1], reverse=True)[:10]
    top_owners = sorted(owner_values.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_deals": total_deals,
        "status_counts": dict(status_counts),
        "open_pipeline_value": open_pipeline_value,
        "open_pipeline_formatted": _fmt_inr(open_pipeline_value),
        "won_value": won_value,
        "won_value_formatted": _fmt_inr(won_value),
        "zero_value_deals": zero_value_count,
        "top_sectors_by_open_value": [(s, _fmt_inr(v), round(v)) for s, v in top_sectors],
        "top_owners_by_value": [(o, _fmt_inr(v)) for o, v in top_owners],
        "stage_distribution": dict(stage_counts),
        "probability_breakdown": {k: _fmt_inr(v) for k, v in prob_values.items()},
        "sector_win_dead": {
            s: {"won": c["won"], "dead": c["dead"], "open": c["open"]}
            for s, c in sector_counts.items()
        },
    }


def win_rate(deals: list) -> dict:
    """Win rate overall and by sector."""
    sector_data = defaultdict(lambda: {"won": 0, "dead": 0})
    total_won = total_dead = 0

    for d in deals:
        status = (d.get("deal_status") or "").lower()
        sector = (d.get("sector") or "Unknown").strip()
        if status == "won":
            sector_data[sector]["won"] += 1
            total_won += 1
        elif status == "dead":
            sector_data[sector]["dead"] += 1
            total_dead += 1

    def _rate(won, dead):
        total = won + dead
        return round(won / total * 100, 1) if total > 0 else None

    overall = _rate(total_won, total_dead)
    by_sector = {
        s: {
            "won": d["won"],
            "dead": d["dead"],
            "win_rate_pct": _rate(d["won"], d["dead"]),
        }
        for s, d in sector_data.items()
        if d["won"] + d["dead"] >= 3
    }
    by_sector_sorted = dict(
        sorted(by_sector.items(), key=lambda x: (x[1]["win_rate_pct"] or 0), reverse=True)
    )

    return {
        "overall_won": total_won,
        "overall_dead": total_dead,
        "overall_win_rate_pct": overall,
        "by_sector": by_sector_sorted,
    }


def overdue_deals(deals: list) -> list:
    """Open or On-Hold deals where actual/tentative close date has passed."""
    today = _today()
    overdue = []
    for d in deals:
        status = (d.get("deal_status") or "").lower()
        if status not in ("open", "on hold"):
            continue
        close = _parse_date(d.get("close_date_actual")) or _parse_date(d.get("tentative_close_date"))
        if close and close < today:
            overdue.append({
                "name": d.get("name"),
                "owner": d.get("owner_code"),
                "sector": d.get("sector"),
                "stage": d.get("deal_stage"),
                "value": _fmt_inr(d.get("deal_value", 0)),
                "close_date": str(close),
                "days_overdue": (today - close).days,
                "probability": d.get("closure_probability"),
            })

    return sorted(overdue, key=lambda x: x["days_overdue"], reverse=True)


def at_risk_deals(deals: list) -> list:
    """High-value deals with Low probability or late-stage stalled."""
    today = _today()
    at_risk = []
    late_stages = {"Negotiations", "Proposal Sent", "Feasibility", "WO Received", "POC"}

    for d in deals:
        status = (d.get("deal_status") or "").lower()
        if status not in ("open", "on hold"):
            continue
        val = d.get("deal_value", 0)
        prob = (d.get("closure_probability") or "").strip()
        stage = d.get("deal_stage", "")
        close = _parse_date(d.get("tentative_close_date"))
        risk_reasons = []

        if prob.lower() == "low" and val > 0:
            risk_reasons.append("Low probability")
        if stage in late_stages and close and close < today:
            risk_reasons.append(f"Overdue in {stage}")
        if val > 5000000 and prob.lower() == "low":
            risk_reasons.append("High value, low probability")

        if risk_reasons:
            at_risk.append({
                "name": d.get("name"),
                "owner": d.get("owner_code"),
                "sector": d.get("sector"),
                "stage": stage,
                "value": _fmt_inr(val),
                "raw_value": val,
                "probability": prob,
                "risk_reasons": risk_reasons,
                "tentative_close": str(close) if close else "Not set",
            })

    return sorted(at_risk, key=lambda x: x["raw_value"], reverse=True)[:15]


def upcoming_deals(deals: list, days_ahead: int = 30) -> list:
    """Deals with tentative close dates within the next N days."""
    today = _today()
    upcoming = []
    for d in deals:
        status = (d.get("deal_status") or "").lower()
        if status not in ("open", "on hold"):
            continue
        close = _parse_date(d.get("tentative_close_date"))
        if close and 0 <= (close - today).days <= days_ahead:
            upcoming.append({
                "name": d.get("name"),
                "owner": d.get("owner_code"),
                "sector": d.get("sector"),
                "stage": d.get("deal_stage"),
                "value": _fmt_inr(d.get("deal_value", 0)),
                "tentative_close": str(close),
                "days_until_close": (close - today).days,
                "probability": d.get("closure_probability"),
            })
    return sorted(upcoming, key=lambda x: x["days_until_close"])


# ─────────────────────────────────────────
# WORK ORDERS analysis
# ─────────────────────────────────────────

def billing_summary(wos: list) -> dict:
    """Total contracted value, billed, collected, outstanding AR."""
    total_contract = total_billed = total_collected = total_ar = 0.0
    total_to_be_billed = 0.0
    sector_contract = defaultdict(float)
    sector_billed = defaultdict(float)
    sector_ar = defaultdict(float)
    high_ar_accounts = []
    corrupted_count = 0

    for wo in wos:
        contract = wo.get("amount_excl_gst", 0.0) or wo.get("amount_incl_gst", 0.0)
        billed = wo.get("billed_value_incl_gst", 0.0) or wo.get("billed_value_excl_gst", 0.0)
        collected = wo.get("collected_amount_incl_gst", 0.0)
        ar = wo.get("amount_receivable", 0.0)
        to_bill = wo.get("amount_to_be_billed_incl_gst", 0.0)
        sector = (wo.get("sector") or "Unknown").strip()

        total_contract += contract
        total_billed += billed
        total_collected += collected
        total_ar += ar
        total_to_be_billed += to_bill

        sector_contract[sector] += contract
        sector_billed[sector] += billed
        sector_ar[sector] += ar

        if ar > 500000 and wo.get("ar_priority", "").lower() in ("high", "critical"):
            high_ar_accounts.append({
                "deal": wo.get("deal_name"),
                "ar": _fmt_inr(ar),
                "raw_ar": ar,
                "priority": wo.get("ar_priority"),
                "sector": sector,
                "customer": wo.get("customer_code"),
            })

    collection_eff = round(total_collected / total_billed * 100, 1) if total_billed > 0 else 0
    billing_gap = total_contract - total_billed

    top_sectors = sorted(sector_contract.items(), key=lambda x: x[1], reverse=True)[:8]
    high_ar_accounts = sorted(high_ar_accounts, key=lambda x: x["raw_ar"], reverse=True)[:10]

    return {
        "total_contract_value": total_contract,
        "total_contract_formatted": _fmt_inr(total_contract),
        "total_billed": total_billed,
        "total_billed_formatted": _fmt_inr(total_billed),
        "total_collected": total_collected,
        "total_collected_formatted": _fmt_inr(total_collected),
        "total_ar": total_ar,
        "total_ar_formatted": _fmt_inr(total_ar),
        "billing_gap": billing_gap,
        "billing_gap_formatted": _fmt_inr(billing_gap),
        "amount_to_be_billed": total_to_be_billed,
        "amount_to_be_billed_formatted": _fmt_inr(total_to_be_billed),
        "collection_efficiency_pct": collection_eff,
        "top_sectors": [
            {
                "sector": s,
                "contract": _fmt_inr(v),
                "billed": _fmt_inr(sector_billed.get(s, 0)),
                "ar": _fmt_inr(sector_ar.get(s, 0)),
            }
            for s, v in top_sectors
        ],
        "high_priority_ar": high_ar_accounts,
    }


def active_work_orders(wos: list) -> dict:
    """Work order status breakdown."""
    status_counts = defaultdict(int)
    stuck = []

    for wo in wos:
        status = (wo.get("execution_status") or wo.get("wo_status") or "Unknown").strip()
        status_counts[status] += 1
        if status.lower() in ("pause/struck", "paused", "struck", "on hold"):
            stuck.append({
                "deal": wo.get("deal_name"),
                "customer": wo.get("customer_code"),
                "sector": wo.get("sector"),
                "status": status,
                "bd_kam": wo.get("bd_kam_code"),
            })

    return {
        "status_breakdown": dict(status_counts),
        "total_work_orders": len(wos),
        "stuck_projects": stuck,
        "stuck_count": len(stuck),
    }


def platform_adoption(deals: list, wos: list) -> dict:
    """Platform usage breakdown from both boards."""
    deal_platform = defaultdict(int)
    wo_platform = defaultdict(int)
    for d in deals:
        prod = (d.get("product") or "Unknown").strip()
        deal_platform[prod] += 1
    for wo in wos:
        plat = (wo.get("platform") or "None/Unknown").strip()
        wo_platform[plat] += 1
    return {
        "by_product_type": dict(deal_platform),
        "by_platform_on_wos": dict(wo_platform),
    }



# ─────────────────────────────────────────
# AD HOC ANALYSIS
# ─────────────────────────────────────────

ADHOC_DIMENSIONS = ["sector", "owner", "stage", "status", "platform"]
ADHOC_METRICS = ["deal_count", "deal_value", "win_rate", "wo_count", "ar", "billed", "collected"]

# Metrics that need work-order data
WO_METRICS = {"wo_count", "ar", "billed", "collected"}
# Dimensions valid for work-order data
WO_DIMENSIONS = {"sector", "platform"}


def adhoc_analysis(deals: list, wos: list, dimension: str, metric: str) -> dict:
    """
    Flexible pivot: group data by `dimension`, aggregate by `metric`.
    Returns:
        {
          "chart":   {type, title, isAmount, data: [{name, value}], bars},
          "summary": {total, top_name, top_value, unit},
        }
    """
    dimension = dimension.lower().strip()
    metric    = metric.lower().strip()

    if dimension not in ADHOC_DIMENSIONS:
        raise ValueError(f"Unknown dimension '{dimension}'. Must be one of {ADHOC_DIMENSIONS}")
    if metric not in ADHOC_METRICS:
        raise ValueError(f"Unknown metric '{metric}'. Must be one of {ADHOC_METRICS}")

    # ── Work-order metrics ────────────────────────────────────────────────────
    if metric in WO_METRICS:
        groups: dict = defaultdict(float)

        for wo in wos:
            if dimension == "sector":
                key = (wo.get("sector") or "Unknown").strip()
            elif dimension == "platform":
                key = (wo.get("platform") or "Unknown").strip()
            else:
                # owner / stage / status are deal-board concepts; fall back to sector
                key = (wo.get("sector") or "Unknown").strip()

            if metric == "wo_count":
                groups[key] += 1
            elif metric == "ar":
                groups[key] += wo.get("amount_receivable", 0.0)
            elif metric == "billed":
                groups[key] += wo.get("billed_value_incl_gst", 0.0) or wo.get("billed_value_excl_gst", 0.0)
            elif metric == "collected":
                groups[key] += wo.get("collected_amount_incl_gst", 0.0)

        sorted_groups = sorted(groups.items(), key=lambda x: x[1], reverse=True)
        data = [{"name": k, "value": round(v)} for k, v in sorted_groups if v > 0]

        is_amount = metric != "wo_count"
        total = sum(v for _, v in sorted_groups)
        top = sorted_groups[0] if sorted_groups else ("—", 0)

        metric_labels = {
            "wo_count":  "Work Order Count",
            "ar":        "Outstanding AR",
            "billed":    "Billed Value",
            "collected": "Amount Collected",
        }
        dim_labels = {"sector": "Sector", "platform": "Platform", "owner": "Owner", "stage": "Stage", "status": "Status"}

        chart_type = "donut" if (metric == "wo_count" and len(data) <= 6) else "bar"
        title = f"{metric_labels[metric]} by {dim_labels.get(dimension, dimension.title())}"
        bars = [{"key": "value", "label": metric_labels[metric], "color": "#06b6d4"}]

        return {
            "chart": {
                "type": chart_type,
                "title": title,
                "isAmount": is_amount,
                "data": data[:10],
                "bars": bars,
            },
            "summary": {
                "total": round(total),
                "total_formatted": _fmt_inr(total) if is_amount else str(int(total)),
                "top_name": top[0],
                "top_value": round(top[1]),
                "top_value_formatted": _fmt_inr(top[1]) if is_amount else str(int(top[1])),
                "unit": "₹" if is_amount else "WOs",
                "record_count": len(wos),
            },
        }

    # ── Deal-board metrics ────────────────────────────────────────────────────
    if metric == "win_rate":
        groups: dict = defaultdict(lambda: {"won": 0, "dead": 0})
        for d in deals:
            status = (d.get("deal_status") or "").lower()
            if status not in ("won", "dead"):
                continue
            if dimension == "sector":
                key = (d.get("sector") or "Unknown").strip()
            elif dimension == "owner":
                key = (d.get("owner_code") or "Unknown").strip()
            elif dimension == "stage":
                key = (d.get("deal_stage") or "Unknown").strip()
            elif dimension == "platform":
                key = (d.get("product") or "Unknown").strip()
            else:
                key = (d.get("deal_status") or "Unknown").strip()

            if status == "won":
                groups[key]["won"] += 1
            else:
                groups[key]["dead"] += 1

        data = []
        for k, v in groups.items():
            total_closed = v["won"] + v["dead"]
            if total_closed >= 2:
                wr = round(v["won"] / total_closed * 100, 1)
                data.append({"name": k, "value": wr, "won": v["won"], "dead": v["dead"]})

        data.sort(key=lambda x: x["value"], reverse=True)
        top = data[0] if data else {"name": "—", "value": 0}

        dim_labels = {"sector": "Sector", "platform": "Platform", "owner": "Owner", "stage": "Stage", "status": "Status"}
        return {
            "chart": {
                "type": "bar",
                "title": f"Win Rate (%) by {dim_labels.get(dimension, dimension.title())}",
                "isAmount": False,
                "data": data[:10],
                "bars": [
                    {"key": "won",   "label": "Won",  "color": "#10b981"},
                    {"key": "dead",  "label": "Dead", "color": "#ef4444"},
                ],
            },
            "summary": {
                "total": len(deals),
                "total_formatted": str(len(deals)),
                "top_name": top["name"],
                "top_value": top["value"],
                "top_value_formatted": f"{top['value']}%",
                "unit": "%",
                "record_count": len(deals),
            },
        }

    # deal_count or deal_value
    groups: dict = defaultdict(float)
    for d in deals:
        if dimension == "sector":
            key = (d.get("sector") or "Unknown").strip()
        elif dimension == "owner":
            key = (d.get("owner_code") or "Unknown").strip()
        elif dimension == "stage":
            key = (d.get("deal_stage") or "Unknown").strip()
        elif dimension == "status":
            key = (d.get("deal_status") or "Unknown").strip()
        elif dimension == "platform":
            key = (d.get("product") or "Unknown").strip()
        else:
            key = "Unknown"

        if metric == "deal_count":
            groups[key] += 1
        elif metric == "deal_value":
            groups[key] += d.get("deal_value", 0.0)

    is_amount = metric == "deal_value"
    sorted_groups = sorted(groups.items(), key=lambda x: x[1], reverse=True)
    data = [{"name": k, "value": round(v)} for k, v in sorted_groups if v > 0]

    total = sum(v for _, v in sorted_groups)
    top = sorted_groups[0] if sorted_groups else ("—", 0)

    metric_labels = {"deal_count": "Deal Count", "deal_value": "Open Deal Value"}
    dim_labels = {"sector": "Sector", "owner": "Owner", "stage": "Stage", "status": "Status", "platform": "Platform"}

    # Use donut for status (few categories), bar for everything else
    chart_type = "donut" if (dimension == "status" and len(data) <= 7) else "bar"
    title = f"{metric_labels[metric]} by {dim_labels.get(dimension, dimension.title())}"
    bars = [{"key": "value", "label": metric_labels[metric], "color": "#3b82f6"}]

    return {
        "chart": {
            "type": chart_type,
            "title": title,
            "isAmount": is_amount,
            "data": data[:10],
            "bars": bars,
        },
        "summary": {
            "total": round(total),
            "total_formatted": _fmt_inr(total) if is_amount else str(int(total)),
            "top_name": top[0],
            "top_value": round(top[1]),
            "top_value_formatted": _fmt_inr(top[1]) if is_amount else str(int(top[1])),
            "unit": "₹" if is_amount else "deals",
            "record_count": len(deals),
        },
    }


def leadership_update(deals: list, wos: list) -> dict:
    """Generate a structured leadership update dict."""
    pipe = pipeline_summary(deals)
    win = win_rate(deals)
    bill = billing_summary(wos)
    active = active_work_orders(wos)
    overdue = overdue_deals(deals)
    at_risk = at_risk_deals(deals)
    upcoming = upcoming_deals(deals, 30)

    # Top 3 open opportunities by value
    open_deals_sorted = sorted(
        [d for d in deals if (d.get("deal_status") or "").lower() == "open"],
        key=lambda x: x.get("deal_value", 0),
        reverse=True,
    )
    top_3_open = [
        {
            "name": d.get("name"),
            "value": _fmt_inr(d.get("deal_value", 0)),
            "sector": d.get("sector"),
            "stage": d.get("deal_stage"),
            "probability": d.get("closure_probability"),
        }
        for d in open_deals_sorted[:3]
    ]

    return {
        "pipeline": pipe,
        "win_rate": win,
        "billing": bill,
        "operations": active,
        "top_open_opportunities": top_3_open,
        "overdue_deals_count": len(overdue),
        "at_risk_count": len(at_risk),
        "upcoming_closures_30d": len(upcoming),
    }
def dashboard_metrics(deals: list, wos: list) -> dict:
    """Aggregates data for the new board-centric dashboard."""
    # 1. Sales Pipeline Metrics
    open_deals = [d for d in deals if (d.get("deal_status") or "").lower() == "open"]
    total_pipeline_val = sum(d.get("deal_value", 0.0) for d in open_deals)
    
    # Value by Probability
    prob_colors = {"High": "#34d399", "Medium": "#fbbf24", "Low": "#f87171"}
    prob_dist = defaultdict(float)
    for d in open_deals:
        p = (d.get("closure_probability") or "Unknown").title()
        if "High" in p: p = "High"
        elif "Medium" in p: p = "Medium"
        elif "Low" in p: p = "Low"
        prob_dist[p] += d.get("deal_value", 0.0)
    
    # Value by Product
    prod_dist = defaultdict(float)
    for d in open_deals:
        p = d.get("product") or "Uncategorized"
        prod_dist[p] += d.get("deal_value", 0.0)

    # 2. Operations & Billing
    total_contract = sum(w.get("amount_excl_gst", 0.0) or w.get("amount_incl_gst", 0.0) for w in wos)
    total_billed = sum(w.get("billed_value_excl_gst", 0.0) for w in wos)
    total_ar = sum(w.get("amount_receivable", 0.0) for w in wos)
    
    billing_counts = defaultdict(int)
    for w in wos:
        st = w.get("billing_status") or "Pending"
        billing_counts[st] += 1

    # KPI Layout
    kpis = [
        {
            "id": "pipeline",
            "label": "Total Open Pipeline",
            "value": _fmt_inr(total_pipeline_val),
            "sub": f"{len(open_deals)} open deals",
            "icon": "💰",
            "color": "var(--accent-blue)"
        },
        {
            "id": "high_prob",
            "label": "High Probability Deals",
            "value": _fmt_inr(prob_dist.get("High", 0.0)),
            "sub": "Closure Probability: High",
            "icon": "🔥",
            "color": prob_colors["High"]
        },
        {
            "id": "ar",
            "label": "Total Receivable",
            "value": _fmt_inr(total_ar),
            "sub": "Outstanding across projects",
            "icon": "⚠️",
            "color": "var(--accent-orange)"
        },
        {
            "id": "billed",
            "label": "Total Billed Value",
            "value": _fmt_inr(total_billed),
            "sub": f"Of {_fmt_inr(total_contract)} contract",
            "icon": "📋",
            "color": "var(--accent-cyan)"
        }
    ]

    charts = [
        {
            "id": "prob_distribution",
            "type": "bar",
            "title": "OPEN PIPELINE BY CLOSURE PROBABILITY",
            "data": [
                {"name": "High", "value": prob_dist.get("High", 0.0), "fill": prob_colors["High"]},
                {"name": "Medium", "value": prob_dist.get("Medium", 0.0), "fill": prob_colors["Medium"]},
                {"name": "Low", "value": prob_dist.get("Low", 0.0), "fill": prob_colors["Low"]}
            ],
            "bars": [{"key": "value", "label": "Value (₹)", "color": "#818cf8"}],
            "isAmount": True
        },
        {
            "id": "product_mix",
            "type": "donut",
            "title": "PIPELINE MIX BY PRODUCT",
            "data": [{"name": k, "value": v} for k, v in prod_dist.items() if v > 0]
        },
        {
            "id": "billing_status_ops",
            "type": "bar",
            "title": "PROJECT COUNT BY BILLING STATUS",
            "data": [{"name": k, "count": v} for k, v in billing_counts.items()],
            "bars": [{"key": "count", "label": "Projects", "color": "#38bdf8"}]
        }
    ]

    # Sorted by contract value
    sorted_wos = sorted(wos, key=lambda x: x.get("amount_excl_gst", 0.0) or x.get("amount_incl_gst", 0.0), reverse=True)
    table_wos = [
        {
            "work_order": w.get("deal_name", "N/A"),
            "sector": w.get("sector", "N/A"),
            "status": w.get("billing_status") or w.get("execution_status") or "Unknown",
            "contract_value": _fmt_inr(w.get("amount_excl_gst", 0.0) or w.get("amount_incl_gst", 0.0)),
            "receivable": _fmt_inr(w.get("amount_receivable", 0.0)),
            "is_ar_high": (w.get("amount_receivable", 0.0) > 0)
        }
        for w in sorted_wos[:10]
    ]

    return {
        "kpis": kpis,
        "charts": charts,
        "top_work_orders": table_wos,
        "summary": {
            "last_updated": datetime.now().strftime("%I:%M:%S %p")
        }
    }


def _parse_amt(s: str) -> float:
    """Internal helper to parse formatted INR strings back to raw floats for charts."""
    if not s or "₹" not in s: return 0.0
    text = s.replace("₹", "").strip()
    mult = 1.0
    if "Cr" in text: mult = 1e7; text = text.replace("Cr", "")
    elif "L" in text: mult = 1e5; text = text.replace("L", "")
    elif "K" in text: mult = 1e3; text = text.replace("K", "")
    try:
        return float(text.strip()) * mult
    except:
        return 0.0
