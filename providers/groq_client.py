import httpx
import logging
import config

logger = logging.getLogger(__name__)

class GroqClient:
    """
    Client for Groq LLM API (llama-3.3-70b-versatile).
    Includes automatic fallback mock mode when using placeholder API key.
    """
    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        self.model = config.GROQ_TRIAGE_MODEL
        self.max_tokens = config.GROQ_MAX_TOKENS
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    def _is_placeholder(self) -> bool:
        return not self.api_key or "placeholder" in self.api_key.lower() or not self.api_key.startswith("gsk_")

    async def chat_complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a completion request to Groq LLM API.
        Returns the raw model completion string.
        """
        # Mock mode fallback for testing without real key
        if self._is_placeholder():
            logger.info("[GROQ_CLIENT] Operating in Mock Mode (Placeholder API Key detected)")
            text = user_prompt.lower()
            if any(k in text for k in ["price", "buy", "tool", "cost", "software", "signal", "account"]):
                return "TRANSACTIONAL"
            elif any(k in text for k in ["friend", "hey", "hello", "relationship", "nice", "talk", "chat"]):
                return "RELATIONAL"
            else:
                return "DEAD"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.0
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"[GROQ_CLIENT] Groq API returned status {response.status_code}: {response.text}")
                raise RuntimeError(f"Groq API Error: {response.status_code}")
                
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content

groq_client = GroqClient()
