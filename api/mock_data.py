"""
mock_data.py
Sample data for the rebuilt Board-Centric Dashboard.
"""

MOCK_DASHBOARD = {
    "kpis": [
        {
            "id": "pipeline",
            "label": "Total Open Pipeline",
            "value": "₹42.35 Cr",
            "sub": "28 open deals",
            "icon": "💰",
            "color": "var(--accent-blue)"
        },
        {
            "id": "high_prob",
            "label": "High Probability Deals",
            "value": "₹15.20 Cr",
            "sub": "Closure Probability: High",
            "icon": "🔥",
            "color": "#34d399"
        },
        {
            "id": "ar",
            "label": "Total Receivable",
            "value": "₹4.12 Cr",
            "sub": "Outstanding across projects",
            "icon": "⚠️",
            "color": "var(--accent-orange)"
        },
        {
            "id": "billed",
            "label": "Total Billed Value",
            "value": "₹12.45 Cr",
            "sub": "Of ₹18.20 Cr contract",
            "icon": "📋",
            "color": "var(--accent-cyan)"
        }
    ],
    "charts": [
        {
            "id": "prob_distribution",
            "type": "bar",
            "title": "OPEN PIPELINE BY CLOSURE PROBABILITY",
            "data": [
                {"name": "High", "value": 152000000, "fill": "#34d399"},
                {"name": "Medium", "value": 185000000, "fill": "#fbbf24"},
                {"name": "Low", "value": 86500000, "fill": "#f87171"}
            ],
            "bars": [{"key": "value", "label": "Value (₹)", "color": "#818cf8"}],
            "isAmount": True
        },
        {
            "id": "product_mix",
            "type": "donut",
            "title": "PIPELINE MIX BY PRODUCT",
            "data": [
                {"name": "Services", "value": 250000000},
                {"name": "Hardware", "value": 120000000},
                {"name": "Software", "value": 53500000}
            ]
        },
        {
            "id": "billing_status_ops",
            "type": "bar",
            "title": "PROJECT COUNT BY BILLING STATUS",
            "data": [
                {"name": "Billed", "count": 12},
                {"name": "To be Billed", "count": 8},
                {"name": "Pending", "count": 5}
            ],
            "bars": [{"key": "count", "label": "Projects", "color": "#38bdf8"}]
        }
    ],
    "top_work_orders": [
        {
            "work_order": "Mining Project Alpha",
            "sector": "Mining",
            "status": "Billed",
            "contract_value": "₹2.45 Cr",
            "receivable": "₹85.00 L",
            "is_ar_high": True
        },
        {
            "work_order": "Solar Farm Zeta",
            "sector": "Renewables",
            "status": "To be Billed",
            "contract_value": "₹1.12 Cr",
            "receivable": "₹0",
            "is_ar_high": False
        },
        {
            "work_order": "Grid Monitoring",
            "sector": "Powerline",
            "status": "Billed",
            "contract_value": "₹75.00 L",
            "receivable": "₹0",
            "is_ar_high": False
        }
    ],
    "summary": {
        "last_updated": "PREVIEW MODE"
    }
}
