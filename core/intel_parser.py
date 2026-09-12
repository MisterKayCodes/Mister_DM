"""
🧠 Brain — Intel response parser.

Pure synchronous. Zero IO. Never raises — returns [] on any failure.
Parses Groq's JSON intel extraction response into clean entry dicts.
"""

import json
import logging

logger = logging.getLogger(__name__)

_VALID_CATEGORIES = frozenset({
    "family", "hobbies", "career", "finances",
    "fears", "desires", "beliefs", "relationships", "misc",
})


def parse_intel_response(raw: str) -> list[dict]:
    """
    Extract a list of intel entries from a raw Groq response string.

    Args:
        raw: The raw string returned by Groq, expected to contain a JSON array.

    Returns:
        List of dicts with keys: category, key, value.
        Returns [] on any parse failure — never raises.
    """
    try:
        cleaned = _extract_json_array(raw)
        entries = json.loads(cleaned)

        if not isinstance(entries, list):
            return []

        valid: list[dict] = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category", "misc")).lower().strip()
            key = str(item.get("key", "")).strip()
            value = str(item.get("value", "")).strip()

            if not key or not value:
                continue

            if category not in _VALID_CATEGORIES:
                category = "misc"

            valid.append({"category": category, "key": key, "value": value})

        return valid

    except Exception as exc:
        logger.warning("Intel parse failed (%s) — raw snippet: %r", exc, raw[:200])
        return []


def _extract_json_array(text: str) -> str:
    """Strip markdown code fences and locate the JSON array bounds."""
    text = text.strip()
    # Strip markdown fences
    if "```" in text:
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    # Find array bounds
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return "[]"
