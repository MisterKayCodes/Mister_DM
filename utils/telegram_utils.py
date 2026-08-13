"""
Telegram message formatting utilities.

This module exists because Telegram's Markdown parser (both V1 and V2) will crash
on any user-generated content that contains special characters like underscores,
asterisks, or backticks. Since we display usernames, campaign names, and template
content written by the user, we must NEVER use parse_mode="Markdown" on those
messages without escaping first.

The safest rule for this project: use HTML mode for all bot messages.
HTML is less likely to break on user-generated content because the only
dangerous characters are < > & — all of which are rare in Telegram usernames.
"""


def safe_html(text: str) -> str:
    """
    Escapes a string so it is safe to embed inside an HTML-parsed Telegram message.

    # We use HTML parse_mode instead of Markdown for any message that contains
    # user-generated content (usernames, campaign names, template bodies).
    # Markdown V1 treats underscores as italic markers — a username like 'john_doe'
    # will crash the parser with: "Can't find end of the entity starting at byte offset X".
    # Markdown V2 requires escaping 18+ special characters which is fragile.
    # HTML only requires escaping 3 characters (<, >, &) which almost never appear
    # in Telegram usernames or campaign names. One util, zero parser crashes.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def bold(text: str) -> str:
    """Wraps text in HTML bold tags. Safe for any content after safe_html()."""
    return f"<b>{safe_html(text)}</b>"


def italic(text: str) -> str:
    """Wraps text in HTML italic tags. Safe for any content after safe_html()."""
    return f"<i>{safe_html(text)}</i>"


def code(text: str) -> str:
    """Wraps text in HTML code tags."""
    return f"<code>{safe_html(text)}</code>"
