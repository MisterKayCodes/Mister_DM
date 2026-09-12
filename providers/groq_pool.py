import time
import logging
import config

logger = logging.getLogger(__name__)


class GroqPool:
    """
    Manages load balancing and automatic cooldown for Groq API keys.
    Supports single or multiple keys via GROQ_API_KEY_LIST in config.py.
    """

    def __init__(self, key_list: list[str] | None = None):
        self.keys = key_list or getattr(config, "GROQ_API_KEY_LIST", [config.GROQ_API_KEY])
        self.current_index = 0
        self.cooling_keys: dict[str, float] = {}  # {key: cooldown_until_timestamp}

    def get_next_key(self) -> str:
        """
        Returns the next active Groq API key in round-robin sequence.
        Skips keys currently on cooldown unless all keys are cooling.
        """
        if not self.keys:
            return config.GROQ_API_KEY

        now = time.time()
        total_keys = len(self.keys)

        # Clean expired cooling keys
        expired = [k for k, until in self.cooling_keys.items() if now >= until]
        for k in expired:
            del self.cooling_keys[k]
            logger.info(f"[GROQ_POOL] Key ending in ...{k[-4:]} has cooled down and is active again.")

        # Try finding an active key starting from current index
        for _ in range(total_keys):
            key = self.keys[self.current_index % total_keys]
            self.current_index = (self.current_index + 1) % total_keys

            if key not in self.cooling_keys:
                return key

        # Fallback: All keys on cooldown -> return the key that cools down earliest
        logger.warning("[GROQ_POOL] All Groq API keys are currently on cooldown! Returning earliest cooling key.")
        earliest_key = min(self.cooling_keys.keys(), key=lambda k: self.cooling_keys[k])
        return earliest_key

    def mark_cooling(self, key: str, cooldown_seconds: int = 60) -> None:
        """Marks a key as cooling (rate limited) for cooldown_seconds."""
        until = time.time() + cooldown_seconds
        self.cooling_keys[key] = until
        logger.warning(
            f"[GROQ_POOL] Key ending in ...{key[-4:]} marked cooling for {cooldown_seconds}s (until {time.strftime('%H:%M:%S', time.localtime(until))})."
        )


groq_pool = GroqPool()
