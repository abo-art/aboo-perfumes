"""
External Perfume API Adapter (e.g., Scento API / Fragrance API integration).
Provides fallback and enrichment capabilities when external credentials are provided.
"""

import logging
from typing import Optional, Dict, Any, List
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class ScentoApiClient:
    """
    Client for interacting with Scento API or similar external perfume fragrance APIs.
    """
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or settings.scento_api_url).rstrip("/")
        self.api_key = api_key or settings.scento_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def search_perfume(self, query: str) -> List[Dict[str, Any]]:
        """Searches external perfume catalog."""
        if not self.is_configured:
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/fragrances/search",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    params={"query": query, "limit": 5}
                )
                if resp.status_code == 200:
                    return resp.json().get("data", [])
        except Exception as e:
            logger.warning(f"External Scento API search failed: {e}")
        return []

    async def get_fragrance_notes(self, fragrance_id: str) -> Optional[Dict[str, Any]]:
        """Fetches olfactory notes and pyramid from external API."""
        if not self.is_configured:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/fragrances/{fragrance_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"External Scento API details failed: {e}")
        return None


scento_client = ScentoApiClient()
