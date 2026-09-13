import datetime
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

def is_persona_active(timezone_str: str, active_hours_str: str) -> bool:
    """
    Checks if the current time in the given timezone falls within the active hours.
    active_hours_str should be in "HH-HH" format (e.g. "08-22").
    Supports overnight wrap-around (e.g. "20-06").
    """
    if not timezone_str or not active_hours_str:
        return True # Default to active if missing config
        
    try:
        tz = zoneinfo.ZoneInfo(timezone_str)
    except Exception:
        # Fallback to UTC if timezone is invalid
        tz = datetime.timezone.utc
        
    now = datetime.datetime.now(tz)
    current_hr = now.hour
    
    try:
        start_str, end_str = active_hours_str.split('-')
        start_hr = int(start_str.strip())
        end_hr = int(end_str.strip())
    except Exception:
        return True # Default to active if format is invalid
        
    if start_hr < end_hr:
        # Normal daytime shift (e.g. 08-22)
        return start_hr <= current_hr < end_hr
    elif start_hr > end_hr:
        # Overnight shift with wrap-around (e.g. 20-06)
        return current_hr >= start_hr or current_hr < end_hr
    else:
        # start == end (0 hours active? Or 24 hours active?)
        return False
