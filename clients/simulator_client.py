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

    async def get_dm_warrior_sessions(self, persona_tag: str | None = None) -> list[dict]:
        """Fetches all active sessions tagged with 'dm_warrior' role, optionally matching persona_tag prefix."""
        res = await self._request("GET", "/api/v1/sessions")
        sessions = res.get("sessions", []) if isinstance(res, dict) and "sessions" in res else (res.get("data", []) if isinstance(res, dict) else res)
        
        # Filter for dm_warrior role and optional persona_tag prefix (e.g. "elena_" or "marcus_")
        dm_warriors = []
        for s in sessions:
            roles = s.get("roles", ["dm_warrior"]) # fallback to treating session as warrior if listed
            s_name = s.get("session_name") or s.get("name", "")
            
            # Match role
            is_warrior = "dm_warrior" in roles or not roles
            if is_warrior and s.get("is_active", True):
                if persona_tag:
                    clean_tag = persona_tag.lower().strip()
                    if s_name.lower().startswith(clean_tag):
                        dm_warriors.append(s)
                else:
                    dm_warriors.append(s)
        return dm_warriors

    async def get_least_loaded_dm_warrior(self, persona_tag: str | None = None) -> str | None:
        """
        Finds all active DM Warriors matching the persona_tag (e.g., 'elena'),
        queries Mister DM database for each warrior's active target load,
        and returns the session_name of the warrior with the lowest load.
        """
        from services.target_service import TargetService
        
        warriors = await self.get_dm_warrior_sessions(persona_tag=persona_tag)
        if not warriors and persona_tag:
            # Fallback to any active warrior if no tag prefix match
            warriors = await self.get_dm_warrior_sessions(persona_tag=None)
            
        if not warriors:
            return None
            
        lowest_load = float("inf")
        best_session = None
        
        for w in warriors:
            s_name = w.get("session_name") or w.get("name")
            if not s_name:
                continue
            load = await TargetService.get_session_active_load(s_name)
            if load < lowest_load:
                lowest_load = load
                best_session = s_name
                
        return best_session or (warriors[0].get("session_name") or warriors[0].get("name"))

    async def send_dm(
        self,
        session_name: str,
        target_username: str | None,
        message_text: str,
        telegram_user_id: int | None = None
    ) -> dict:
        """
        Delegates DM send execution to Simulator's Telethon engine.
        Calls POST /api/v1/telethon/send-message
        Supports both target_username and telegram_user_id.
        """
        payload = {
            "session_name": session_name,
            "target": target_username or str(telegram_user_id),
            "text": message_text
        }
        res = await self._request("POST", "/api/v1/telethon/send-message", json=payload)
        
        # Normalize the Simulator's response shape for Mister DM
        is_success = res.get("success", False)
        return {
            "status": "success" if is_success else "error",
            "ok": is_success,
            "message_id": res.get("message_id"),
            "user_id": telegram_user_id,
            "telegram_user_id": telegram_user_id
        }

    async def send_media(
        self,
        session_name: str,
        target_username: str | None,
        telegram_file_id: str,
        media_type: str = "photo",
        telegram_user_id: int | None = None
    ) -> dict:
        """
        Delegates media (photo/video/voice) send execution to Simulator's Telethon engine.
        Calls POST /api/v1/telethon/send-media
        """
        payload = {
            "session_name": session_name,
            "target": target_username or str(telegram_user_id),
            "file_id": telegram_file_id,
            "media_type": media_type
        }
        res = await self._request("POST", "/api/v1/telethon/send-media", json=payload)
        is_success = res.get("success", False) if isinstance(res, dict) else False
        return {
            "status": "success" if is_success else "error",
            "ok": is_success,
            "message_id": res.get("message_id") if isinstance(res, dict) else None
        }

    async def push_reply_webhook(
        self,
        session_name: str,
        from_username: str,
        from_user_id: int,
        message_text: str
    ) -> dict:
        """
        Helper method used by Simulator to forward inbound Telethon DMs to Mister DM.
        Calls POST http://localhost:8013/api/v1/webhook/reply
        """
        payload = {
            "session_name": session_name,
            "from_username": from_username,
            "from_user_id": from_user_id,
            "message_text": message_text
        }
        # Local DM API Webhook URL
        dm_webhook_url = f"http://localhost:{config.DM_API_PORT}/api/v1/webhook/reply"
        return await self._request("POST", "/api/v1/webhook/reply", json=payload)

simulator_client = SimulatorClient()
