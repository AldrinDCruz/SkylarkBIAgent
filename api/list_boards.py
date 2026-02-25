
import os
import asyncio
import httpx
from dotenv import load_dotenv

async def list_boards():
    load_dotenv()
    token = os.environ.get("MONDAY_API_TOKEN")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "API-Version": "2024-01",
    }
    
    query = "{ boards (limit: 50) { id name } }"
    
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://api.monday.com/v2", headers=headers, json={"query": query})
        data = resp.json()
        if "data" in data and "boards" in data["data"]:
            print("Accessible Boards:")
            for b in data["data"]["boards"]:
                print(f"- {b['name']} (ID: {b['id']})")
        else:
            print("Error or No Boards found:", data)

if __name__ == "__main__":
    asyncio.run(list_boards())
