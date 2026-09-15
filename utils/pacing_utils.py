import random
import asyncio
import logging

logger = logging.getLogger(__name__)

async def async_jitter_sleep(min_sec: float = 1.0, max_sec: float = 3.0) -> float:
    """
    Introduces a random micro-delay between min_sec and max_sec
    to mimic human typing latency and prevent Telethon / Groq API rate limits.
    """
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"[PACING] Jitter sleeping for {delay:.2f} seconds...")
    await asyncio.sleep(delay)
    return delay
