"""
Core Package — Brain Domain Master Barrel
Re-exports core engines, triage rules, arcs, and state.
"""

from .triage import (
    TriageEngine,
    parse_intel_response,
    build_roleplay_prompt,
    build_intel_extraction_prompt,
    build_personalized_opener_prompt,
    build_classification_prompt,
)
from .arcs import (
    calculate_day_and_week,
    get_week_label,
    get_week_tone,
)
from .state import restricted_sessions
from .constants import VALID_CAMPAIGN_TRANSITIONS

__all__ = [
    "TriageEngine",
    "parse_intel_response",
    "build_roleplay_prompt",
    "build_intel_extraction_prompt",
    "build_personalized_opener_prompt",
    "build_classification_prompt",
    "calculate_day_and_week",
    "get_week_label",
    "get_week_tone",
    "restricted_sessions",
    "VALID_CAMPAIGN_TRANSITIONS",
]
