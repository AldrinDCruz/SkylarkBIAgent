# Skylark Drones — Business Intelligence Agent

An AI-powered BI agent that queries your Monday.com boards in real-time, normalises messy data, and answers founder-level business questions via a conversational chat UI.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER BROWSER                            │
│  React + Vite frontend  (Vercel / Railway static)           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  ChatWindow  │  │  QuickChips  │  │ LeadershipReport │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         └────────────────┬┘                   │            │
└──────────────────────────┼────────────────────┼────────────┘
                           │ POST /chat           │ POST /leadership-update
                           ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend  (Railway)                   │
│                                                             │
│  main.py ──► 1. classify_query (Claude)                     │
│              2. monday_client.py ──► Monday.com GraphQL API │
│              3. data_normalizer.py (clean messy fields)      │
│              4. bi_engine.py (pipeline/billing analytics)    │
│              5. claude_agent.py ──► Anthropic Claude API    │
│              6. Return structured response                   │
└─────────────────────────────────────────────────────────────┘
          │                                    │
          ▼                                    ▼
  Monday.com API v2                   Anthropic Claude API
  (Deals board + WO board)            (claude-sonnet-4-5)
```

### Data Flow
1. User sends a question in the chat UI
2. Backend asks Claude to classify which board(s) to query
3. Monday.com data is fetched via GraphQL (cursor-based pagination, 500 items/page)
4. Data is normalised: `#VALUE!` → 0, `"2186 HA"` → `(2186, "HA")`, dates standardised
5. BI engine computes analytics: pipeline summary, win rates, billing gaps, AR priority
6. Claude receives the computed context + question and generates a founder-level answer
7. Response streams back with metadata (which boards queried, record counts)

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Anthropic API key
- Monday.com API token
- Two Monday.com Board IDs (Deals and Work Orders)

### Getting your Monday.com API Token
1. Log in to Monday.com → click your **avatar** (bottom-left)
2. Go to **Administration → API**  
   *or* open [monday.com/developers/v2](https://monday.com/developers/v2)
3. Copy the **Personal API Token**

### Finding Board IDs
**Method 1 — URL:** Open the board in Monday.com. The URL looks like:  
`https://your-company.monday.com/boards/1234567890`  
The number at the end is your Board ID.

**Method 2 — Developer Console:**
```graphql
query { boards(limit: 10) { id name } }
```
Run at [api.monday.com/v2](https://api.monday.com/v2) with your token.

### Monday.com Board Column Setup

> **Note:** The normaliser uses column *titles* (not IDs) for mapping.  
> Use the exact column names below when creating your boards.

#### Deals Board (required columns)
| Column Title | Type |
|---|---|
| Owner code | Text |
| Client Code | Text |
| Deal Status | Status (Open/Won/Dead/On Hold) |
| Close Date (A) | Date |
| Closure Probability | Status (High/Medium/Low) |
| Masked Deal value | Numbers |
| Tentative Close Date | Date |
| Deal Stage | Text |
| Product deal | Text |
| Sector/service | Text |
| Created Date | Date |

#### Work Orders Board (required columns)
| Column Title | Type |
|---|---|
| Customer Name Code | Text |
| Execution Status | Status |
| Date of PO/LOI | Date |
| BD/KAM Personnel code | Text |
| Sector | Text |
| Platform | Status (SPECTRA/DMO/NONE) |
| Amount Excl GST (Masked) | Numbers |
| Amount Incl GST (Masked) | Numbers |
| Billed Value Excl GST (Masked) | Numbers |
| Billed Value Incl GST (Masked) | Numbers |
| Collected Amount Incl GST (Masked) | Numbers |
| Amount Receivable | Numbers |
| AR Priority | Status (High/Medium/Low) |
| Invoice Status | Status |
| WO Status (billed) | Status |
| Collection status | Status |

---

## Local Development

### Backend

```bash
cd e:\skylark\backend

# Install dependencies
pip install -r requirements.txt

# Copy and fill in the .env file
cp ../.env.example .env
# edit .env with your real keys

# Start the server
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/health` — should return `{"status":"ok"}`.

### Frontend

```bash
cd e:\skylark\frontend

# Copy the local env file
# Edit VITE_API_URL if backend is not on localhost:8000
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

### Unified Vercel Deployment (Recommended)

1. Push the repo to GitHub.
2. Import the project at [vercel.com/new](https://vercel.com/new).
3. Vercel will auto-detect the configuration via `vercel.json` and the `api/` directory.
4. Set environment variables in Vercel:
   ```
   GOOGLE_API_KEY=...
   MONDAY_API_TOKEN=...
   DEALS_BOARD_ID=...
   WO_BOARD_ID=...
   ```
5. Deploy.

> **CORS:** The backend allows `*` by default. For production security, set `ALLOWED_ORIGINS` to your Vercel domain.

### Alternative: Both on Railway

Railway supports static site deploys too:
1. Add a second service for the frontend
2. Set start command: `npm run build && npx serve dist`
3. Set `VITE_API_URL` env var to the backend service URL

---

## Sample Test Queries

Once deployed, test with these queries:

```
1. How's our pipeline looking for energy sector this quarter?
2. Who is our top performing BD owner?
3. What deals are overdue or at risk of slipping?
4. Give me a billing and collections summary
5. Which sectors have the highest win rate?
6. How many active work orders do we have and which are stuck?
7. What's our total contracted value vs what we've actually billed?
8. Show me all high-value deals still in negotiation
```

---

## Data Quality Handling

The agent handles these data quality issues automatically:

| Issue | How it's handled |
|---|---|
| `#VALUE!` in amount fields | Returns 0.0, flagged in AI response |
| `"2186.54 HA"` quantities | Parsed to `(2186.54, "HA")` |
| Empty/null values | Treated as 0 or "Unknown" |
| Duplicate header rows | Filtered by checking if "Deal Status" = "Deal Status" |
| Missing close dates | Noted as "date not set", no crash |
| ₹0 deal values | Counted but noted as missing data |
| Inconsistent date formats | `dateutil.parser` handles all common formats |

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | From console.anthropic.com |
| `MONDAY_API_TOKEN` | ✅ | From monday.com/developers/v2 |
| `DEALS_BOARD_ID` | ✅ | Numeric ID of your Deals board |
| `WO_BOARD_ID` | ✅ | Numeric ID of your Work Orders board |
| `ALLOWED_ORIGINS` | Optional | Comma-separated list of allowed frontend URLs |

---

## Project Structure

```
e:\skylark\
├── api/
│   ├── index.py             # FastAPI entry point
│   ├── monday_client.py     # GraphQL client
│   ├── data_normalizer.py   # Field cleaners
│   ├── bi_engine.py         # Analytics
│   ├── claude_agent.py      # AI logic
│   └── requirements.txt
├── src/                     # React source
├── public/                  # Static assets
├── index.html
├── package.json
└── vercel.json
```
