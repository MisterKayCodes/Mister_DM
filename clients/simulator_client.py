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
        """Fetches all active sessions tagged explicitly with 'dm' or 'dm_warrior' role."""
        res = await self._request("GET", "/api/v1/sessions")
        sessions = res.get("sessions", []) if isinstance(res, dict) and "sessions" in res else (res.get("data", []) if isinstance(res, dict) else res)
        
        dm_warriors = []
        for s in sessions:
            roles = [r.lower() for r in s.get("roles", [])]
            s_name = s.get("session_name") or s.get("name", "")
            
            # Match role strictly to 'dm' or 'dm_warrior'
            is_dm_session = ("dm" in roles or "dm_warrior" in roles)
            if is_dm_session and s.get("status", "online") in ("online", "active"):
                if persona_tag:
                    clean_tag = persona_tag.lower().strip()
                    if s_name.lower().startswith(clean_tag):
                        dm_warriors.append(s)
                else:
                    dm_warriors.append(s)
        return dm_warriors

    async def get_dm_warriors_detailed_status(self) -> list[dict]:
        """
        Fetches all DM Warrior sessions with full detail from Mister Simulator API,
        cross-referenced with bonded campaigns in Mister DM.
        """
        from services.campaigns import CampaignService
        from services.account_service import AccountService
        from core.state import restricted_sessions
        from datetime import datetime, timezone

        try:
            res = await self._request("GET", "/api/v1/sessions")
            all_sessions = res.get("sessions", []) if isinstance(res, dict) and "sessions" in res else (res.get("data", []) if isinstance(res, dict) else res)
        except Exception:
            all_sessions = []

        all_campaigns = await CampaignService.get_all_campaigns()
        local_accounts = await AccountService.get_all_accounts()
        local_acc_map = {acc["id"]: acc for acc in local_accounts}

        warriors_status = []
        now_utc = datetime.now(timezone.utc)

        for s in all_sessions:
            roles = [r.lower() for r in s.get("roles", [])]
            s_name = s.get("session_name") or s.get("name", "")
            if not ("dm" in roles or "dm_warrior" in roles):
                continue

            # Check if benched / restricted in scheduler dict
            is_benched = s_name in restricted_sessions
            ttl_remaining_mins = 0
            if is_benched:
                benched_time = restricted_sessions[s_name]
                elapsed_sec = (now_utc - benched_time).total_seconds()
                ttl_remaining_mins = max(0, int((1200 - elapsed_sec) / 60))

            # Find bonded campaign
            bonded_campaign = next((c for c in all_campaigns if c.get("session_name") == s_name), None)

            # Match local account metrics
            matching_acc = next((acc for acc in local_accounts if acc["name"] == s_name or acc["name"] == f"{s_name} (Simulator)"), None)
            sent_today = matching_acc["messages_sent_today"] if matching_acc else 0
            daily_limit = matching_acc["daily_limit"] if matching_acc else 50
            delay_min = matching_acc["delay_min"] if matching_acc else 60
            delay_max = matching_acc["delay_max"] if matching_acc else 120

            warriors_status.append({
                "session_name": s_name,
                "status": s.get("status", "online"),
                "is_restricted": s.get("is_restricted", False) or is_benched,
                "ttl_remaining_mins": ttl_remaining_mins,
                "bonded_campaign": bonded_campaign.get("name") if bonded_campaign else None,
                "campaign_status": bonded_campaign.get("status") if bonded_campaign else None,
                "sent_today": sent_today,
                "daily_limit": daily_limit,
                "delay_range": f"{delay_min}s - {delay_max}s"
            })

        return warriors_status

    async def get_least_loaded_dm_warrior(self, persona_tag: str | None = None) -> str | None:
        """
        Finds all active DM Warriors matching the persona_tag (e.g., 'elena'),
        queries Mister DM database for each warrior's active target load,
        and returns the session_name of the warrior with the lowest load.
        """
        from services.leads import TargetService
        
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

    async def get_session_detail(self, session_name: str) -> dict | None:
        """Fetches profile, status, and capability mask for a single session from Simulator API."""
        try:
            res = await self._request("GET", f"/api/v1/sessions/{session_name}")
            return res if isinstance(res, dict) and res.get("success") else None
        except Exception:
            return None

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
