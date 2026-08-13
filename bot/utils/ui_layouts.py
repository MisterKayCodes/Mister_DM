from utils.telegram_utils import safe_html

def build_campaign_summary_text(summary: dict) -> str:
    """
    Builds the HTML display string for the campaign management screen.
    The Service returns raw integers and strings. The Mouth draws the HTML here.
    """
    if not summary:
        return "Campaign not found."
        
    return (
        f"Managing Campaign:\n<b>{safe_html(summary['name'])}</b>\n\n"
        f"Status: {safe_html(summary['status'].capitalize())}\n\n"
        f"Templates: {summary['templates_count']}\n"
        f"Targets: {summary['targets_count']}\n"
        f"Replies: Coming Soon\n"
    )

def build_templates_list_text(templates: list[dict]) -> str:
    """
    Builds the HTML display string for a list of templates.
    Lives here (Mouth) because it is presentation logic — it knows about HTML, emojis,
    and Telegram character limits.
    """
    if not templates:
        return "No templates found for this campaign."
        
    text = "📋 Templates for this Campaign:\n\n"
    for tpl in templates:
        text += f"<b>[Template #{tpl['id']}]</b>\n<pre>{safe_html(tpl['content'])}</pre>\n\n"
    return text
