"""
monday_client.py
Handles all Monday.com GraphQL API calls with pagination and in-memory caching.
"""

import asyncio
import time
import logging
from typing import Optional
import httpx
import os

logger = logging.getLogger(__name__)

MONDAY_API_URL = "https://api.monday.com/v2"
CACHE_TTL_SECONDS = 300  # 5-minute cache


class MondayClient:
    def __init__(self, api_token: str, deals_board_id: str, wo_board_id: str):
        self.api_token = api_token
        self.deals_board_id = str(deals_board_id)
        self.wo_board_id = str(wo_board_id)
        self._cache: dict = {}
        self._cache_timestamps: dict = {}
        self._headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "API-Version": "2024-01",
        }

    def _is_cache_valid(self, key: str) -> bool:
        ts = self._cache_timestamps.get(key)
        if ts is None:
            return False
        return (time.time() - ts) < CACHE_TTL_SECONDS

    async def _fetch_board_items(self, board_id: str) -> list:
        """Fetch all items from a board using cursor-based pagination."""
        all_items = []
        cursor = None
        page_num = 0

        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                page_num += 1
                logger.info(f"Fetching board {board_id}, page {page_num}, cursor={cursor}")

                if cursor:
                    query = """
                    query($boardId: ID!, $cursor: String!) {
                      boards(ids: [$boardId]) {
                        items_page(limit: 500, cursor: $cursor) {
                          cursor
                          items {
                            id
                            name
                            column_values {
                              id
                              title
                              text
                              value
                            }
                          }
                        }
                      }
                    }
                    """
                    variables = {"boardId": board_id, "cursor": cursor}
                else:
                    query = """
                    query($boardId: ID!) {
                      boards(ids: [$boardId]) {
                        items_page(limit: 500) {
                          cursor
                          items {
                            id
                            name
                            column_values {
                              id
                              title
                              text
                              value
                            }
                          }
                        }
                      }
                    }
                    """
                    variables = {"boardId": board_id}

                data = await self._graphql_request(client, query, variables)

                boards = data.get("data", {}).get("boards", [])
                if not boards:
                    logger.warning(f"No boards returned for id={board_id}")
                    break

                items_page = boards[0].get("items_page", {})
                items = items_page.get("items", [])
                all_items.extend(items)

                cursor = items_page.get("cursor")
                if not cursor:
                    break

        logger.info(f"Board {board_id}: fetched {len(all_items)} total items")
        return all_items

    async def _graphql_request(self, client: httpx.AsyncClient, query: str, variables: dict, retries: int = 3) -> dict:
        """Execute a GraphQL query with retry logic."""
        payload = {"query": query, "variables": variables}
        for attempt in range(retries):
            try:
                response = await client.post(
                    MONDAY_API_URL,
                    headers=self._headers,
                    json=payload,
                )
                if response.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited (429), waiting {wait}s before retry {attempt+1}")
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                result = response.json()
                if "errors" in result:
                    logger.error(f"GraphQL errors: {result['errors']}")
                return result
            except httpx.HTTPStatusError as e:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Request failed: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        return {}

    async def get_deals(self, force_refresh: bool = False) -> list:
        """Get all deals from the Deals board (cached)."""
        cache_key = f"deals_{self.deals_board_id}"
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.info("Returning cached deals data")
            return self._cache[cache_key]

        items = await self._fetch_board_items(self.deals_board_id)
        self._cache[cache_key] = items
        self._cache_timestamps[cache_key] = time.time()
        return items

    async def get_work_orders(self, force_refresh: bool = False) -> list:
        """Get all work orders from the WO board (cached)."""
        cache_key = f"wo_{self.wo_board_id}"
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.info("Returning cached WO data")
            return self._cache[cache_key]

        items = await self._fetch_board_items(self.wo_board_id)
        self._cache[cache_key] = items
        self._cache_timestamps[cache_key] = time.time()
        return items

    def invalidate_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("Cache invalidated")

    def get_cache_age_minutes(self) -> dict:
        """Return age of each cache entry in minutes."""
        now = time.time()
        return {
            k: round((now - v) / 60, 1)
            for k, v in self._cache_timestamps.items()
        }
