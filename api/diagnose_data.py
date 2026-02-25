
import os
import asyncio
from monday_client import MondayClient
from dotenv import load_dotenv

async def check():
    load_dotenv()
    token = os.environ.get("MONDAY_API_TOKEN")
    deals_id = os.environ.get("DEALS_BOARD_ID")
    wo_id = os.environ.get("WO_BOARD_ID")
    
    print(f"Token: {token[:10]}...")
    print(f"Deals ID: {deals_id}")
    print(f"WO ID: {wo_id}")
    
    client = MondayClient(token, deals_id, wo_id)
    
    print("\n--- Checking Deals Board ---")
    try:
        deals = await client.get_deals()
        print(f"Fetched {len(deals)} raw items")
        if deals:
            print("First item columns:", [cv.get("title") for cv in deals[0].get("column_values", [])])
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Checking WO Board ---")
    try:
        wos = await client.get_work_orders()
        print(f"Fetched {len(wos)} raw items")
        if wos:
            print("First item columns:", [cv.get("title") for cv in wos[0].get("column_values", [])])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
