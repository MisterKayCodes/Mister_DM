import logging
import config
from clients.base_client import BaseClient

logger = logging.getLogger(__name__)

class MisterAIClient(BaseClient):
    """
    HTTP Client for communicating with Mister AI API (Port 8014).
    Transfers RELATIONAL leads for long-term roleplay/relationship arcs.
    """
    def __init__(self):
        super().__init__(
            base_url=config.MISTER_AI_URL,
            api_key=config.MISTER_AI_API_KEY,
            service_name="Mister AI"
        )

    def _is_placeholder(self) -> bool:
        return not self.api_key or "placeholder" in self.api_key.lower()

    async def check_health(self) -> bool:
        """Pings Mister AI health endpoint."""
        if self._is_placeholder():
            return True
        try:
            res = await self._request("GET", "/api/v1/health", max_retries=1)
            return res.get("status") == "ok"
        except Exception:
            return False

    async def intake_lead(self, payload: dict) -> dict:
        """
        Pushes a RELATIONAL lead profile to Mister AI.
        Calls POST /api/v1/leads/intake
        """
        # Mock mode fallback for testing without real running Mister AI instance
        if self._is_placeholder():
            logger.info(f"[MISTER_AI_CLIENT] Mock Mode: Lead '{payload.get('username')}' transferred to Mister AI successfully.")
            return {
                "status": "success",
                "message": f"Lead @{payload.get('username')} received by Mister AI (Mock)",
                "ai_lead_id": 101
            }

        return await self._request("POST", "/api/v1/leads/intake", json=payload)

mister_ai_client = MisterAIClient()
