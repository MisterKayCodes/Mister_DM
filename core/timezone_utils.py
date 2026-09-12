"""
🧠 Brain — Timezone & Schedule logic.

Pure sync. Handles persona timezone offset and formatting.
Returns formatted strings — no bot or DB imports.
"""

from datetime import datetime, timezone, timedelta


def _utc_offset(tz_name: str = "America/Chicago") -> int:
    """Return UTC offset in hours for a given timezone name. Defaults to US Central (CDT -5 / CST -6)."""
    month = datetime.now(timezone.utc).month
    if tz_name.lower() in ("america/chicago", "us/central", "cst", "cdt"):
        # US DST: CDT (UTC-5) Mar–Nov, CST (UTC-6) otherwise
        return -5 if 3 <= month <= 11 else -6
    elif tz_name.lower() in ("utc", "gmt"):
        return 0
    elif tz_name.lower() in ("wat", "africa/lagos"):
        return 1
    # Fallback to -5 (CDT)
    return -5


def get_persona_time(tz_name: str = "America/Chicago") -> datetime:
    """Return current time in persona's timezone."""
    offset = timedelta(hours=_utc_offset(tz_name))
    return datetime.now(timezone.utc) + offset


def format_time_display(persona_name: str = "Persona", tz_name: str = "America/Chicago", user_utc_offset: int = 1) -> str:
    """
    Returns a formatted time display string.
    user_utc_offset: WAT = UTC+1
    """
    p_now = get_persona_time(tz_name)
    offset = _utc_offset(tz_name)
    offset_label = f"UTC{offset:+d}"

    user_time = datetime.now(timezone.utc) + timedelta(hours=user_utc_offset)

    return (
        f"🕐 {persona_name}'s Time: *{p_now.strftime('%I:%M %p')} {offset_label}* "
        f"({user_time.strftime('%I:%M %p')} WAT)"
    )


def get_schedule_display(persona_name: str = "Persona", tz_name: str = "America/Chicago", user_utc_offset: int = 1) -> str:
    """
    Returns persona's full daily schedule with WAT conversion.
    user_utc_offset: WAT = UTC+1 (West Africa Time)
    """
    p_offset = _utc_offset(tz_name)
    offset_label = f"UTC{p_offset:+d}"
    diff = user_utc_offset - p_offset

    def convert(p_hour: int, p_min: int = 0) -> str:
        user_h = (p_hour + diff) % 24
        p_dt = datetime(2000, 1, 1, p_hour, p_min)
        user_dt = datetime(2000, 1, 1, user_h, p_min)
        return f"{p_dt.strftime('%I:%M %p')} {offset_label}  →  {user_dt.strftime('%I:%M %p')} WAT"

    lines = [
        f"📅 *{persona_name}'s Daily Schedule*",
        f"_{offset_label} → Your Time (WAT)_\n",
        f"🌅 *Morning*",
        f"  {convert(7, 0)}  — Wake up",
        f"  {convert(7, 20)}  — Morning routine",
        f"  {convert(8, 30)}  — Get ready",
        f"\n💼 *Work*",
        f"  {convert(9, 0)}   — Check messages & market",
        f"  {convert(9, 30)}  — Deep work block",
        f"  {convert(12, 30)} — Lunch break",
        f"  {convert(17, 0)}  — Done for the day ✅",
        f"\n🌆 *Evening*",
        f"  {convert(19, 0)}  — Dinner",
        f"  {convert(23, 0)}  — 😴 Sleep",
    ]

    return "\n".join(lines)
