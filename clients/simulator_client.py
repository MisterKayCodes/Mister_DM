import config
from clients.base_client import BaseClient

class SimulatorClient(BaseClient):
    """
    HTTP Client for communicating with Mister Simulator API (Port 8012).
    Delegates session management and Telethon message execution.
    """
    def __init__(self):
        super().__init__(
            base_url=config.SIMULATOR_API_URL,
            api_key=config.SIMULATOR_API_KEY,
            service_name="Mister Simulator"
        )

    async def check_health(self) -> bool:
        """Pings Simulator health endpoint."""
        try:
            res = await self._request("GET", "/api/v1/health", max_retries=1)
            return res.get("status") == "ok"
        except Exception:
            return False

    async def get_dm_warrior_sessions(self) -> list[dict]:
        """Fetches all active sessions tagged with 'dm_warrior' role."""
        res = await self._request("GET", "/api/v1/sessions")
        sessions = res.get("data", []) if isinstance(res, dict) else res
        
        # Filter for dm_warrior role
        dm_warriors = []
        for s in sessions:
            roles = s.get("roles", [])
            if "dm_warrior" in roles and s.get("is_active", True):
                dm_warriors.append(s)
        return dm_warriors

    async def send_dm(self, session_name: str, target_username: str, message_text: str) -> dict:
        """
        Delegates DM send execution to Simulator's Telethon engine.
        Calls POST /api/v1/telethon/dm
        """
        payload = {
            "session_name": session_name,
            "username": target_username,
            "message": message_text
        }
        return await self._request("POST", "/api/v1/telethon/dm", json=payload)

simulator_client = SimulatorClient()
