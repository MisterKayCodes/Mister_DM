import time
import math
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GroqTracker:
    """
    In-memory singleton tracking Groq API token usage,
    call counts, rate-limit headers, and backoff timers.
    """
    def __init__(self):
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0
        self.call_count: int = 0
        
        self.rate_limit_info: Dict[str, Any] = {}
        self.pause_until: float = 0.0

    def record_usage(self, usage_data: dict, response_headers: dict = None):
        """Records token usage and extracts rate-limit headers from a Groq API response."""
        self.prompt_tokens += usage_data.get("prompt_tokens", 0)
        self.completion_tokens += usage_data.get("completion_tokens", 0)
        self.total_tokens += usage_data.get("total_tokens", 0)
        self.call_count += 1

        if response_headers:
            try:
                t_limit = response_headers.get("x-ratelimit-limit-tokens")
                t_rem = response_headers.get("x-ratelimit-remaining-tokens")
                r_limit = response_headers.get("x-ratelimit-limit-requests")
                r_rem = response_headers.get("x-ratelimit-remaining-requests")
                r_reset = response_headers.get("x-ratelimit-reset-requests")
                t_reset = response_headers.get("x-ratelimit-reset-tokens")

                if t_limit and t_rem:
                    self.rate_limit_info["tokens_limit"] = int(t_limit)
                    self.rate_limit_info["tokens_remaining"] = int(t_rem)
                if r_limit and r_rem:
                    self.rate_limit_info["requests_limit"] = int(r_limit)
                    self.rate_limit_info["requests_remaining"] = int(r_rem)
                if r_reset:
                    self.rate_limit_info["reset_requests"] = str(r_reset)
                if t_reset:
                    self.rate_limit_info["reset_tokens"] = str(t_reset)
            except Exception as exc:
                logger.warning(f"[GROQ_TRACKER] Error parsing response headers: {exc}")

    def set_backoff(self, seconds: float):
        """Sets a local pause timer if HTTP 429 rate limit error occurs."""
        self.pause_until = time.time() + seconds

    def get_stats(self) -> dict:
        """Returns session stats, rate limits, and radar health calculations."""
        now = time.time()
        is_paused = now < self.pause_until
        backoff_sec = max(0, int(self.pause_until - now)) if is_paused else 0

        t_limit = self.rate_limit_info.get("tokens_limit", 70000)
        t_rem = self.rate_limit_info.get("tokens_remaining", t_limit)
        r_limit = self.rate_limit_info.get("requests_limit", 250)
        r_rem = self.rate_limit_info.get("requests_remaining", r_limit)

        # Calculate quota health percentage based on remaining tokens and requests
        t_pct = (t_rem / t_limit) * 100 if t_limit > 0 else 100.0
        r_pct = (r_rem / r_limit) * 100 if r_limit > 0 else 100.0
        overall_pct = min(t_pct, r_pct)

        if is_paused:
            status_badge = f"⛔ EXHAUSTED / PAUSED ({backoff_sec}s left)"
        elif overall_pct > 40:
            status_badge = f"🟢 SAFE ({overall_pct:.1f}% Quota Available)"
        elif overall_pct > 15:
            status_badge = f"🟡 MEDIUM ({overall_pct:.1f}% Quota Available)"
        else:
            status_badge = f"🔴 NEAR EXHAUSTION ({overall_pct:.1f}% Quota Available)"

        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
            "rate_limits": self.rate_limit_info,
            "is_paused": is_paused,
            "backoff_sec": backoff_sec,
            "overall_pct": overall_pct,
            "status_badge": status_badge,
            "tokens_limit": t_limit,
            "tokens_remaining": t_rem,
            "requests_limit": r_limit,
            "requests_remaining": r_rem,
            "reset_requests": self.rate_limit_info.get("reset_requests", "1m 0s"),
            "reset_tokens": self.rate_limit_info.get("reset_tokens", "0ms")
        }

# Global singleton instance
groq_tracker = GroqTracker()
