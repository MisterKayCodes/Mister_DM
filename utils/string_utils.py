"""
This module provides string manipulation utilities.
It handles tasks like sanitizing filenames, cleaning up text inputs, 
and safely formatting strings so that the UI layer (bots) doesn't 
have to deal with regular expressions or data formatting logic.
"""

import re

def generate_safe_filename(name: str) -> str:
    """
    Converts a string into a safe filename by converting it to lowercase 
    and replacing any non-alphanumeric characters with an underscore.
    
    Example: "Trading Outreach!" -> "trading_outreach_"
    """
    return re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
