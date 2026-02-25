"""
claude_agent.py
Handles LLM API calls using Google Gemini (free tier).
Query classification, BI answering, and leadership update generation.

Free API key: https://aistudio.google.com/app/apikey
Model used: gemini-1.5-flash (free tier: 15 req/min, 1M tokens/day)
"""

import json
import logging
import re
from typing import Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Business Intelligence agent for Skylark Drones, a drone survey and analytics company. You have access to two data sources: a Deals pipeline board and a Work Orders execution board from Monday.com.

Your job is to answer founder-level business questions with clarity, numbers, and insight - not just raw data dumps.

CONTEXT ON THE DATA:
- Deal names and company names are masked for privacy (anime/cartoon characters = deal names, COMPANY_XXX = clients, OWNER_XXX = BD/KAM personnel)
- Currency is Indian Rupees (₹). Values in the data are already in rupees.
- Deal stages follow this funnel: A→Lead, B→SQL, C→Demo Done, D→Feasibility, E→Proposal Sent, F→Negotiations, G→Won, H→WO Received, I→POC, J→Invoice Sent, K→Amount Accrued, L→Project Lost, M→On Hold, N/O→Not Relevant
- Work Order execution statuses: Completed, Ongoing, Executed until current month, Not Started, Pause/struck, Partial Completed
- Sectors: Mining, Renewables, Railways, Powerline, Construction, DSP, Others, Aviation, Manufacturing, Security and Surveillance

DATA QUALITY NOTES - always mention relevant caveats:
- Some deals have ₹0 value (missing data)
- Some records have duplicate/missing owner codes
- Dates may be missing or inconsistent
- A small number of records have corrupted values (#VALUE!)
- "Won" status deals include both active WOs and historical completions

RESPONSE STYLE:
- Lead with the direct answer and key number
- Provide sector/owner/stage breakdowns when relevant
- Flag data quality issues that affect the answer
- Suggest follow-up questions the founder might want to ask
- Format numbers in Indian style (use Cr for crore, L for lakh)
- Be concise - founders want signal, not noise
- Use markdown formatting for readability (bold key numbers, use bullet lists for breakdowns)
"""

CLASSIFICATION_PROMPT = """You are a query router for a business intelligence system. Given a user question, decide which Monday.com board(s) to query.

Respond with ONLY a JSON object like: {"boards": ["deals"], "reasoning": "..."}
Options for boards array: "deals", "work_orders", or both like ["deals", "work_orders"]

Rules:
- Pipeline, deal stages, win rate, owner performance → "deals"
- Billing, AR, collections, invoices, work execution → "work_orders"
- Revenue overview, performance vs pipeline → both
- "top performer" without context → both
- General health / overview → both

User question: {question}"""


class ClaudeAgent:
    """LLM agent using Google Gemini (free tier). Class name kept for compatibility."""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        # Using 'latest' alias is more stable across SDK versions
        self.model_name = "gemini-1.5-flash-latest"
        try:
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_PROMPT,
            )
            self.classifier_model = genai.GenerativeModel(
                model_name=self.model_name,
            )
            logger.info(f"✅ GeminiAgent initialized with {self.model_name}")
        except Exception as e:
            logger.error(f"❌ Gemini initialization failed: {e}")
            # Dynamic fallback to a known ultra-stable model
            self.model_name = "gemini-1.5-flash"
            self.model = genai.GenerativeModel(model_name=self.model_name, system_instruction=SYSTEM_PROMPT)
            self.classifier_model = genai.GenerativeModel(model_name=self.model_name)

    async def classify_query(self, message: str) -> list[str]:
        """Classify which boards to query for a given user message."""
        try:
            prompt = CLASSIFICATION_PROMPT.format(question=message)
            response = self.classifier_model.generate_content(prompt)
            text = response.text.strip()
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                boards = result.get("boards", ["deals", "work_orders"])
                if isinstance(boards, str):
                    boards = [boards]
                return boards
        except Exception as e:
            logger.warning(f"Classification failed (likely quota), defaulting to both boards: {e}")
        return ["deals", "work_orders"]

    async def answer(
        self,
        message: str,
        history: list[dict],
        bi_context: dict,
        deals: Optional[list] = None,
        wos: Optional[list] = None,
    ) -> str:
        """Generate a BI answer using Gemini with full context."""

        # Build context string from BI analytics
        context_parts = ["## LIVE DATA CONTEXT FROM MONDAY.COM\n"]

        if "pipeline" in bi_context:
            pipe = bi_context["pipeline"]
            context_parts.append(f"""### Pipeline Summary
- Total deals: {pipe.get('total_deals', 0)}
- Status breakdown: {json.dumps(pipe.get('status_counts', {}), indent=2)}
- Open pipeline value: {pipe.get('open_pipeline_formatted', 'N/A')}
- Won deals value: {pipe.get('won_value_formatted', 'N/A')}
- Deals with ₹0 value (data quality): {pipe.get('zero_value_deals', 0)}
- Top sectors by open value: {json.dumps(pipe.get('top_sectors_by_open_value', []))}
- Top owners by deal value: {json.dumps(pipe.get('top_owners_by_value', []))}
- Deal stage distribution: {json.dumps(pipe.get('stage_distribution', {}), indent=2)}
- Probability breakdown: {json.dumps(pipe.get('probability_breakdown', {}), indent=2)}
""")

        if "win_rate" in bi_context:
            wr = bi_context["win_rate"]
            context_parts.append(f"""### Win Rate Analysis
- Overall: {wr.get('overall_win_rate_pct')}% (Won: {wr.get('overall_won')}, Dead: {wr.get('overall_dead')})
- By sector: {json.dumps(wr.get('by_sector', {}), indent=2)}
""")

        if "overdue_deals" in bi_context:
            overdue = bi_context["overdue_deals"]
            context_parts.append(f"""### Overdue Deals (Open/On-Hold past close date)
Count: {len(overdue)}
{json.dumps(overdue[:10], indent=2)}
""")

        if "at_risk" in bi_context:
            at_risk = bi_context["at_risk"]
            context_parts.append(f"""### At-Risk Deals
Count: {len(at_risk)}
{json.dumps(at_risk[:8], indent=2)}
""")

        if "upcoming_deals" in bi_context:
            upcoming = bi_context["upcoming_deals"]
            context_parts.append(f"""### Deals Closing Next 30 Days
Count: {len(upcoming)}
{json.dumps(upcoming[:10], indent=2)}
""")

        if "billing" in bi_context:
            bill = bi_context["billing"]
            context_parts.append(f"""### Revenue & Billing Summary
- Total contract value: {bill.get('total_contract_formatted', 'N/A')}
- Total billed: {bill.get('total_billed_formatted', 'N/A')}
- Total collected: {bill.get('total_collected_formatted', 'N/A')}
- Outstanding AR: {bill.get('total_ar_formatted', 'N/A')}
- Billing gap (contract - billed): {bill.get('billing_gap_formatted', 'N/A')}
- Amount yet to be billed: {bill.get('amount_to_be_billed_formatted', 'N/A')}
- Collection efficiency: {bill.get('collection_efficiency_pct')}%
- Sector breakdown: {json.dumps(bill.get('top_sectors', []), indent=2)}
- High priority AR: {json.dumps(bill.get('high_priority_ar', []), indent=2)}
""")

        if "operations" in bi_context:
            ops = bi_context["operations"]
            context_parts.append(f"""### Work Order Operations
- Total WOs: {ops.get('total_work_orders', 0)}
- Status breakdown: {json.dumps(ops.get('status_breakdown', {}), indent=2)}
- Stuck/paused projects ({ops.get('stuck_count', 0)}): {json.dumps(ops.get('stuck_projects', []), indent=2)}
""")

        if "platform" in bi_context:
            context_parts.append(f"""### Platform Adoption
{json.dumps(bi_context['platform'], indent=2)}
""")

        full_context = "\n".join(context_parts)

        # Build Gemini multi-turn chat history
        gemini_history = []
        for h in history[-10:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if content:
                # Gemini uses "model" instead of "assistant"
                gemini_role = "model" if role == "assistant" else "user"
                gemini_history.append({"role": gemini_role, "parts": [content]})

        # Start chat with history then send current question + context
        chat = self.model.start_chat(history=gemini_history)
        user_message = f"{full_context}\n\n## FOUNDER'S QUESTION\n{message}"

        try:
            response = chat.send_message(user_message)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error in answer(): {e}")
            if "404" in str(e) or "not found" in str(e).lower():
                logger.warning("🔄 Primary model failed. Attempting fallback to gemini-1.5-pro...")
                try:
                    fallback_model = genai.GenerativeModel(model_name="gemini-1.5-pro", system_instruction=SYSTEM_PROMPT)
                    fallback_chat = fallback_model.start_chat(history=gemini_history)
                    response = fallback_chat.send_message(user_message)
                    return response.text
                except Exception as e2:
                    logger.error(f"❌ Fallback 1 (1.5-pro) failed: {e2}")
                    # Final attempt - 1.0 Pro
                    try:
                        fallback_model = genai.GenerativeModel(model_name="gemini-pro", system_instruction=SYSTEM_PROMPT)
                        fallback_chat = fallback_model.start_chat(history=gemini_history)
                        response = fallback_chat.send_message(user_message)
                        return response.text
                    except Exception as e3:
                         logger.error(f"❌ Final fallback failed: {e3}")
            
            if "quota" in str(e).lower() or "429" in str(e):
                return "⚠️ **AI Quota Exceeded.** Based on the data, you have an open pipeline of **" + \
                    bi_context.get("pipeline", {}).get("open_pipeline_formatted", "N/A") + \
                    "** and revenue of **" + bi_context.get("pipeline", {}).get("won_value_formatted", "N/A") + \
                    "**. (Self-correction: Displaying raw BI summary as fallback)."
            raise

    async def generate_adhoc_insight(
        self,
        dimension: str,
        metric: str,
        chart_data: dict,
        summary: dict,
    ) -> str:
        """Generate a 2–3 sentence business insight for an ad hoc pivot result."""
        dim_labels = {
            "sector": "sector", "owner": "BD/KAM owner", "stage": "deal stage",
            "status": "deal status", "platform": "product/platform",
        }
        metric_labels = {
            "deal_count": "number of deals", "deal_value": "open deal value",
            "win_rate": "win rate", "wo_count": "work order count",
            "ar": "outstanding AR", "billed": "billed value", "collected": "amount collected",
        }

        top_items = chart_data.get("data", [])[:5]
        prompt = f"""You are a BI analyst for Skylark Drones. Given this pivot data, write exactly 2-3 concise sentences of insight for a founder.

Pivot: {metric_labels.get(metric, metric)} grouped by {dim_labels.get(dimension, dimension)}
Top results: {json.dumps(top_items)}
Summary: total={summary.get('total_formatted')}, top={summary.get('top_name')} at {summary.get('top_value_formatted')}

Rules:
- Lead with the most important insight (the dominant group)
- Mention the share % if relevant
- Flag any concentration risk or opportunity
- Use Indian number format (Cr/L)
- No bullet points, just flowing sentences
- Maximum 3 sentences"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Adhoc insight generation failed (quota?): {e}")
            top_val = summary.get('top_value_formatted', 'N/A')
            top_name = summary.get('top_name', '—')
            return f"{top_name} leads this category with {top_val}. This represents a key area of focus for the current pipeline."

    async def generate_leadership_update(self, leadership_data: dict) -> str:
        """Generate a formatted leadership briefing document."""
        prompt = f"""Generate a professional leadership update briefing for Skylark Drones management.
Use this structured data:

{json.dumps(leadership_data, indent=2)}

Format it as:
## 📊 Skylark Drones — Leadership Update

### Executive Summary
(3-4 sentences on overall business health)

### 🔥 Pipeline Highlights
- Open pipeline value and count
- Top 3 open opportunities (name = masked, show sector + stage + value)
- Deals closing this month

### 💰 Revenue Snapshot
- Contract value, billing, collections in one clear table
- Collection efficiency %
- Billing gap warning if significant
- Key AR priority accounts

### ⚙️ Operational Pulse
- Active work orders summary
- Stuck/paused projects flagged
- Platform adoption (SPECTRA vs DMO)

### ⚠️ Key Risks & Flags
- Overdue deals count and severity
- At-risk high-value deals
- Data quality issues to be aware of

Keep it concise, use Indian number formatting (Cr/L), and make it copy-paste ready for a leadership meeting."""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Leadership update generation failed (quota?): {e}")
            return "## 📊 Skylark Drones — Quick Summary (Fallback)\n\n" + \
                   f"- **Pipeline:** {leadership_data['pipeline'].get('open_pipeline_formatted')}\n" + \
                   f"- **Wins:** {leadership_data['pipeline'].get('won_value_formatted')}\n" + \
                   f"- **Collection Rate:** {leadership_data['billing'].get('collection_efficiency_pct')}%\n\n" + \
                   "*(AI detailed report hidden due to quota limits)*"
