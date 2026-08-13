"""
String helper utilities for the Mister DM project.

This module handles text sanitization and formatting so that no other layer
(bot handlers, repositories, models) ever needs to deal with regex or
raw string manipulation directly. One place for all text cleaning rules.
"""

import re

# Simple regex — nothing more.
# We are not trying to replicate Telegram's full username validation here.
# Telegram itself is the real validator. Phase 5 (Scheduler) will discover
# bad usernames organically when the actual DM send fails.
# Over-validating here means rejecting valid usernames we haven't anticipated.
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{5,32}$')


def clean_username(raw: str) -> str | None:
    """
    Strips whitespace and the leading '@' from a raw username string.
    Returns the cleaned string if it passes the basic regex check,
    or None if it should be treated as invalid and skipped.
    """
    cleaned = raw.strip().lstrip('@')
    if USERNAME_REGEX.match(cleaned):
        return cleaned
    return None


def generate_safe_filename(name: str) -> str:
    """
    Converts a string into a safe filename by converting it to lowercase
    and replacing any non-alphanumeric characters with an underscore.

    Example: "Trading Outreach!" -> "trading_outreach_"
    """
    return re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
