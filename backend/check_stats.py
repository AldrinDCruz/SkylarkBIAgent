
import os
import asyncio
import httpx
from dotenv import load_dotenv

async def check_stats():
    load_dotenv()
    token = os.environ.get("MONDAY_API_TOKEN")
    deals_id = os.environ.get("DEALS_BOARD_ID")
    wo_id = os.environ.get("WO_BOARD_ID")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "API-Version": "2024-01",
    }
    
    query = """
    query($ids: [ID!]) {
      boards(ids: $ids) {
        id
        name
        items_count
        type
      }
    }
    """
    
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://api.monday.com/v2", headers=headers, json={"query": query, "variables": {"ids": [deals_id, wo_id]}})
        print(resp.json())

if __name__ == "__main__":
    asyncio.run(check_stats())
