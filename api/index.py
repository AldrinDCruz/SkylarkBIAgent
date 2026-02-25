"""
main.py
FastAPI application - entry point with /chat and /leadership-update endpoints.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from monday_client import MondayClient
from data_normalizer import normalize_deals, normalize_work_orders
from bi_engine import (
    pipeline_summary, win_rate, overdue_deals, at_risk_deals,
    upcoming_deals, billing_summary, active_work_orders, platform_adoption,
    leadership_update, adhoc_analysis, WO_METRICS, dashboard_metrics,
)
from claude_agent import ClaudeAgent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Environment
# ─────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MONDAY_API_TOKEN = os.environ.get("MONDAY_API_TOKEN", "")
DEALS_BOARD_ID = os.environ.get("DEALS_BOARD_ID", "")
WO_BOARD_ID = os.environ.get("WO_BOARD_ID", "")

# ─────────────────────────────────────────
# Lazy Init Helpers for Serverless
# ─────────────────────────────────────────
_monday_client: Optional[MondayClient] = None
_claude_agent: Optional[ClaudeAgent] = None

def get_monday_client():
    global _monday_client
    if _monday_client is None:
        if not MONDAY_API_TOKEN:
            raise HTTPException(status_code=500, detail="MONDAY_API_TOKEN not set")
        _monday_client = MondayClient(MONDAY_API_TOKEN, DEALS_BOARD_ID, WO_BOARD_ID)
    return _monday_client

def get_claude_agent():
    global _claude_agent
    if _claude_agent is None:
        if not GEMINI_API_KEY:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")
        _claude_agent = ClaudeAgent(GEMINI_API_KEY)
    return _claude_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up clients if env vars exist
    if all([GEMINI_API_KEY, MONDAY_API_TOKEN, DEALS_BOARD_ID, WO_BOARD_ID]):
        try:
            get_monday_client()
            get_claude_agent()
            logger.info("✅ Skylark BI Agent backend initialized via lifespan")
        except Exception as e:
            logger.error(f"Initialization failure: {e}")
    yield
    logger.info("Backend shutdown")


app = FastAPI(
    title="Skylark Drones BI Agent API",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api",
)

# ─────────────────────────────────────────
# CORS
# ─────────────────────────────────────────
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://*.vercel.app",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In prod, replace with ALLOWED_ORIGINS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    response: str
    boards_queried: list[str] = []
    cache_age_minutes: dict = {}
    data_counts: dict = {}
    charts: list[dict] = []


class AdhocRequest(BaseModel):
    dimension: str   # sector | owner | stage | status | platform
    metric: str      # deal_count | deal_value | win_rate | wo_count | ar | billed | collected


class AdhocResponse(BaseModel):
    chart: dict
    insight: str
    summary: dict


# ─────────────────────────────────────────
# Helper: fetch & normalize data
# ─────────────────────────────────────────
async def _get_normalized_data(boards: list[str]):
    """Fetch raw data and return normalized list of dicts."""
    mc = get_monday_client()
    deals, wos = [], []
    if "deals" in boards:
        raw_deals = await mc.get_deals()
        deals = normalize_deals(raw_deals)
        logger.info(f"Normalized {len(deals)} deals (from {len(raw_deals)} raw)")
    if "work_orders" in boards:
        raw_wos = await mc.get_work_orders()
        wos = normalize_work_orders(raw_wos)
        logger.info(f"Normalized {len(wos)} work orders (from {len(raw_wos)} raw)")
    return deals, wos


def _build_bi_context(message_lower: str, deals: list, wos: list) -> dict:
    """Build relevant BI context based on the query intent."""
    context = {}

    if deals:
        context["pipeline"] = pipeline_summary(deals)
        context["win_rate"] = win_rate(deals)

    risk_keywords = ["risk", "overdue", "slip", "behind", "late", "stuck", "miss"]
    if deals and any(k in message_lower for k in risk_keywords + ["upcoming", "closing", "this month", "pipeline"]):
        context["overdue_deals"] = overdue_deals(deals)
        context["at_risk"] = at_risk_deals(deals)
        context["upcoming_deals"] = upcoming_deals(deals, 30)

    if deals and "overdue_deals" not in context:
        context["overdue_deals"] = overdue_deals(deals)
        context["at_risk"] = at_risk_deals(deals)

    if wos:
        context["billing"] = billing_summary(wos)
        context["operations"] = active_work_orders(wos)

    if deals or wos:
        context["platform"] = platform_adoption(deals, wos)

    return context


def _build_charts(message_lower: str, bi_context: dict) -> list[dict]:
    """Build chart data objects relevant to the query for frontend rendering."""
    charts = []
    pipe = bi_context.get("pipeline", {})
    bill = bi_context.get("billing", {})
    ops  = bi_context.get("operations", {})
    wr   = bi_context.get("win_rate", {})

    # ── Deal status donut (always shown when deals queried) ──────────────
    status_counts = pipe.get("status_counts", {})
    if status_counts:
        charts.append({
            "type": "donut",
            "title": "Deal Status Distribution",
            "data": [{"name": k, "value": v} for k, v in status_counts.items() if v > 0],
        })

    # ── Pipeline value by sector (bar) ───────────────────────────────────
    sector_data = pipe.get("top_sectors_by_open_value", [])
    pipeline_keywords = ["pipeline", "sector", "energy", "renew", "mining", "rail", "top", "value"]
    if sector_data and any(k in message_lower for k in pipeline_keywords):
        charts.append({
            "type": "bar",
            "title": "Open Pipeline Value by Sector",
            "isAmount": True,
            "data": [{"name": s, "value": v} for s, _, v in sector_data[:8]],
            "bars": [{"key": "value", "label": "Open Value", "color": "#3b82f6"}],
        })

    # ── Win rate by sector (bar) ─────────────────────────────────────────
    win_keywords = ["win", "rate", "won", "dead", "conversion", "performance"]
    sector_wr = wr.get("by_sector", {})
    if sector_wr and any(k in message_lower for k in win_keywords):
        wr_data = [
            {"name": s, "win_rate": d["win_rate_pct"], "won": d["won"], "dead": d["dead"]}
            for s, d in sector_wr.items() if d["win_rate_pct"] is not None
        ][:8]
        if wr_data:
            charts.append({
                "type": "bar",
                "title": "Win Rate by Sector (%)",
                "isAmount": False,
                "data": wr_data,
                "bars": [
                    {"key": "won",  "label": "Won",  "color": "#10b981"},
                    {"key": "dead", "label": "Dead", "color": "#ef4444"},
                ],
            })

    # ── Billing vs collected area chart ──────────────────────────────────
    billing_keywords = ["bill", "collect", "ar", "revenue", "invoice", "paid", "receivable"]
    if bill and any(k in message_lower for k in billing_keywords):
        sector_rows = bill.get("top_sectors", [])
        if sector_rows:
            def _parse(s):
                s = s.replace("₹", "").strip()
                mult = 1e7 if "Cr" in s else (1e5 if "L" in s else 1e3 if "K" in s else 1)
                return float(s.replace("Cr","").replace("L","").replace("K","").strip()) * mult
            charts.append({
                "type": "bar",
                "title": "Billed vs Collected by Sector",
                "isAmount": True,
                "data": [
                    {"name": r["sector"],
                     "billed": _parse(r["billed"]),
                     "collected": _parse(r.get("ar", "₹0"))
                    }
                    for r in sector_rows[:7]
                ],
                "bars": [
                    {"key": "billed",    "label": "Billed",     "color": "#3b82f6"},
                    {"key": "collected", "label": "AR",         "color": "#f59e0b"},
                ],
            })

    # ── Work order status donut ───────────────────────────────────────────
    wo_status = ops.get("status_breakdown", {})
    wo_keywords = ["work order", "wo", "stuck", "active", "ongoing", "execut", "operational"]
    if wo_status and any(k in message_lower for k in wo_keywords):
        charts.append({
            "type": "donut",
            "title": "Work Order Status",
            "data": [{"name": k, "value": v} for k, v in wo_status.items() if v > 0],
        })

    return charts[:4]  # cap at 4 charts per response


# ─────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────

@app.get("/health")
async def health():
    try:
        cache_age = get_monday_client().get_cache_age_minutes()
    except Exception:
        cache_age = "Client not initialized"
        
    return {
        "status": "ok",
        "cache": cache_age,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not MONDAY_API_TOKEN:
        raise HTTPException(status_code=503, detail="MONDAY_API_TOKEN not configured")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")

    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Step 1: Classify which boards to query
    boards = await get_claude_agent().classify_query(message)
    logger.info(f"Query classified → boards: {boards}")

    # Step 2: Fetch and normalize data
    try:
        deals, wos = await _get_normalized_data(boards)
    except Exception as e:
        logger.error(f"Monday.com fetch error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch data from Monday.com: {str(e)}"
        )

    # Step 3: Build BI context
    bi_context = _build_bi_context(message.lower(), deals, wos)

    # Step 4: Generate Claude answer
    # 2. Get Agent Response
    try:
        agent_response = await get_claude_agent().answer(
            message=req.message,
            history=[{"role": m.role, "content": m.content} for m in req.history],
            bi_context=bi_context,
            deals=deals,
            wos=wos
        )
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        raise HTTPException(status_code=502, detail=f"AI generation failed: {str(e)}")

    return ChatResponse(
        response=agent_response,
        boards_queried=boards,
        cache_age_minutes=get_monday_client().get_cache_age_minutes(),
        data_counts={"deals": len(deals), "work_orders": len(wos)},
        charts=_build_charts(message.lower(), bi_context),
    )


@app.post("/refresh-cache")
async def refresh_cache():
    """Force-refresh Monday.com data cache."""
    get_monday_client().clear_cache()
    return {"status": "Cache cleared"}


@app.post("/adhoc", response_model=AdhocResponse)
async def adhoc(req: AdhocRequest):
    """Run an ad hoc pivot analysis on live Monday.com data."""
    if not MONDAY_API_TOKEN:
        raise HTTPException(status_code=503, detail="MONDAY_API_TOKEN not configured")

    # Choose boards based on metric
    boards = ["work_orders"] if req.metric in WO_METRICS else ["deals"]
    # win_rate needs deals; owner/stage/status need deals
    if req.metric == "win_rate" or req.dimension in ("owner", "stage", "status"):
        boards = ["deals"]
    # ar/billed/collected always need WOs
    if req.metric in ("ar", "billed", "collected", "wo_count"):
        boards = ["work_orders"]

    try:
        deals, wos = await _get_normalized_data(boards)
    except Exception as e:
        logger.error(f"Monday.com fetch error in /adhoc: {e}")
        raise HTTPException(status_code=502, detail=f"Data fetch failed: {str(e)}")

    try:
        result = adhoc_analysis(deals, wos, req.dimension, req.metric)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    chart   = result["chart"]
    summary = result["summary"]

    # Build relevant prompt
    try:
        # The provided diff for adhoc insight generation is incomplete/incorrect.
        # Reverting to original logic but using get_claude_agent()
        insight = await get_claude_agent().generate_adhoc_insight(
            dimension=req.dimension,
            metric=req.metric,
            chart_data=chart,
            summary=summary,
        )
    except Exception as e:
        logger.error(f"Claude API error in /adhoc: {e}")
        raise HTTPException(status_code=502, detail=f"AI generation failed: {str(e)}")

    return AdhocResponse(chart=chart, insight=insight, summary=summary)


@app.post("/leadership-update")
async def get_leadership_update():
    """Generate a formatted leadership briefing."""
    mc = get_monday_client()
    ca = get_claude_agent()

    try:
        raw_deals = await mc.get_deals()
        raw_wos = await mc.get_work_orders()
        deals = normalize_deals(raw_deals)
        wos = normalize_work_orders(raw_wos)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Data fetch failed: {str(e)}")

    context = leadership_update(deals, wos)

    # 2. Generate update
    try:
        update_text = await ca.generate_leadership_update(context)
        return {"report": update_text}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Briefing generation failed: {str(e)}")

from mock_data import MOCK_DASHBOARD

@app.get("/dashboard-data")
async def get_dashboard_data(mock: bool = False):
    """Fetch all metrics for the executive dashboard view."""
    if mock:
        return MOCK_DASHBOARD

    try:
        mc = get_monday_client()
    except Exception as e:
        logger.warning(f"Failed to init Monday client: {e}. Falling back to mock.")
        return MOCK_DASHBOARD
    try:
        raw_deals = await mc.get_deals()
        raw_wos = await mc.get_work_orders()
        deals = normalize_deals(raw_deals)
        wos = normalize_work_orders(raw_wos)
    except Exception as e:
        logger.error(f"Dashboard data fetch failed: {e}")
        return MOCK_DASHBOARD # Auto-fallback to mock if fetch fails entirely

    # Aggregate data using the new dashboard_metrics logic
    data = dashboard_metrics(deals, wos)
    
    # If board is totally empty, return mock data to show user what it looks like
    # (only if user hasn't explicitly asked for real data)
    is_empty = (len(deals) == 0 and len(wos) == 0)
    if is_empty:
        # We still return some metadata saying it's mock
        mock_with_hint = dict(MOCK_DASHBOARD)
        mock_with_hint["summary"]["missing_data_hint"] = "Showing sample data because your boards are currently empty."
        return mock_with_hint

    data["cache_age"] = get_monday_client().get_cache_age_minutes()
    return data
