# Pure data — no imports, no logic.
# Lives in core/ because it defines system-wide business rules, not just utility constants.

# Valid campaign status transitions.
# Source of truth for what state changes are legally allowed.
VALID_CAMPAIGN_TRANSITIONS: dict[str, set[str]] = {
    "draft":     {"running"},
    "running":   {"paused", "completed"},
    "paused":    {"running"},
    "completed": set(),
}
