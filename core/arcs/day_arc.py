"""
🧠 Brain — Day & Week Arc Calculator.

Pure sync logic. Calculates elapsed days/weeks from a chat start date.
No imports from data/, services/, bot/, or providers/.
"""

from datetime import datetime, timezone


def calculate_day_and_week(started_at: str) -> dict:
    """
    Given an ISO timestamp string, calculate elapsed days and which week we are in.

    Returns:
        {
            "total_days": int,       # Days since chat started (day 1 = first day)
            "week": int,             # 1–5
            "day_of_week": int,      # 1–7
            "started_date": str,     # "Jun 30"
        }
    """
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        # Make start timezone-aware if it isn't
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    except Exception:
        return {"total_days": 1, "week": 1, "day_of_week": 1, "started_date": "Unknown"}

    now = datetime.now(timezone.utc)
    delta = (now - start).days
    total_days = delta + 1  # Day 1 = the day the chat started

    week = min(5, max(1, ((total_days - 1) // 7) + 1))
    day_of_week = ((total_days - 1) % 7) + 1

    started_date = start.strftime("%b %d")

    return {
        "total_days": total_days,
        "week": week,
        "day_of_week": day_of_week,
        "started_date": started_date,
    }


def format_day_label(arc: dict) -> str:
    """Returns a display string like 'Week 1 · Day 3'."""
    return f"Week {arc['week']} · Day {arc['day_of_week']}"
