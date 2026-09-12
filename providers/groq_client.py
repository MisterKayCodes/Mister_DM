import httpx
import logging
import config
from providers.groq_pool import groq_pool

logger = logging.getLogger(__name__)

class GroqClient:
    """
    Client for Groq LLM API.
    Uses groq_pool for round-robin key rotation and automatic rate-limit cooldown tracking.
    """
    def __init__(self):
        self.model = config.GROQ_TRIAGE_MODEL
        self.max_tokens = config.GROQ_MAX_TOKENS
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    def _is_placeholder(self, api_key: str) -> bool:
        return not api_key or "placeholder" in api_key.lower() or not api_key.startswith("gsk_")

    async def chat_complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a completion request to Groq API using key pool.
        """
        active_key = groq_pool.get_next_key()

        if self._is_placeholder(active_key):
            logger.info("[GROQ_CLIENT] Operating in Mock Mode (Placeholder API Key detected)")
            text = user_prompt.lower()
            if any(k in text for k in ["price", "buy", "tool", "cost", "software", "signal", "account"]):
                return "TRANSACTIONAL"
            elif any(k in text for k in ["friend", "hey", "hello", "relationship", "nice", "talk", "chat"]):
                return "RELATIONAL"
            else:
                return "DEAD"

        headers = {
            "Authorization": f"Bearer {active_key}",
            "Content-Type": "application/json"
        }
        
        req_model = self.model.replace("groq/", "") if self.model.startswith("groq/") else self.model
        if req_model in ("compound-mini", "compound", ""):
            req_model = "llama-3.3-70b-versatile"

        payload = {
            "model": req_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.0
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
                elif response.status_code == 429:
                    groq_pool.mark_cooling(active_key, cooldown_seconds=60)
                    logger.warning(f"[GROQ_CLIENT] Rate limited (429) on key ...{active_key[-4:]}. Marked cooling.")
                else:
                    logger.warning(f"[GROQ_CLIENT] Groq API returned status {response.status_code}. Falling back to default.")
        except Exception as exc:
            logger.warning(f"[GROQ_CLIENT] Groq API call failed ({exc}). Falling back to default.")

        text = user_prompt.lower()
        if any(k in text for k in ["price", "buy", "tool", "cost", "software", "signal", "account"]):
            return "TRANSACTIONAL"
        elif any(k in text for k in ["friend", "hey", "hello", "relationship", "nice", "talk", "chat"]):
            return "RELATIONAL"
        else:
            return "RELATIONAL"

    async def chat_complete_with_history(
        self,
        system_prompt: str,
        messages_history: list[dict],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.7
    ) -> str:
        """
        Sends multi-turn chat completions request to Groq API using key pool.
        """
        active_key = groq_pool.get_next_key()

        if self._is_placeholder(active_key):
            logger.info("[GROQ_CLIENT] Roleplay operating in Mock Mode (Placeholder Key)")
            return '{\n  "intent": "Mock response generated for testing.",\n  "confidence_score": 90,\n  "needs_human": false,\n  "message": "Hey! That is super interesting. Tell me more about what you do."\n}'

        headers = {
            "Authorization": f"Bearer {active_key}",
            "Content-Type": "application/json"
        }

        full_messages = [{"role": "system", "content": system_prompt}] + messages_history

        req_model = model or getattr(config, "GROQ_ROLEPLAY_MODEL", None) or getattr(config, "GROQ_TRIAGE_MODEL", "llama-3.3-70b-versatile")
        if req_model.startswith("groq/"):
            req_model = req_model.replace("groq/", "")
        if req_model in ("compound-mini", "compound", ""):
            req_model = "llama-3.3-70b-versatile"

        payload = {
            "model": req_model,
            "messages": full_messages,
            "max_tokens": max_tokens or getattr(config, "GROQ_ROLEPLAY_MAX_TOKENS", 512),
            "temperature": temperature
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
                elif response.status_code == 429:
                    groq_pool.mark_cooling(active_key, cooldown_seconds=60)
                    logger.warning(f"[GROQ_CLIENT] Rate limited (429) on roleplay key ...{active_key[-4:]}. Marked cooling.")
                else:
                    logger.warning(f"[GROQ_CLIENT] Groq API returned status {response.status_code}: {response.text}. Falling back to mock roleplay.")
        except Exception as exc:
            logger.warning(f"[GROQ_CLIENT] Groq API call failed: {exc}. Falling back to mock roleplay.")

        return '{\n  "intent": "Target expressed interest in mining hardware. Building emotional connection and establishing industry authority.",\n  "confidence_score": 88,\n  "needs_human": false,\n  "message": "Honestly? The hardware market has been chaotic lately. We are managing ASIC shipments out of Austin, but staying selective. What side of crypto are you operating in?"\n}'

groq_client = GroqClient()
