from datetime import datetime

# Shared in-memory state registries
# Track sessions that returned HTTP 403 (can_dm=False) along with restriction timestamp
restricted_sessions: dict[str, datetime] = {}
