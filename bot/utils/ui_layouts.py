from utils.telegram_utils import safe_html

def build_campaign_summary_text(summary: dict) -> str:
    """
    Builds the HTML display string for the campaign management screen.
    Includes a dynamic step-by-step setup wizard guiding the user to the next action.
    """
    if not summary:
        return "Campaign not found."

    status_str = summary.get('status', 'draft').lower()
    templates_count = summary.get('templates_count', 0)
    targets_count = summary.get('targets_count', 0)

    text = (
        f"🎯 <b>Campaign: {safe_html(summary['name'])}</b>\n\n"
        f"<b>Status:</b> {safe_html(status_str.capitalize())}\n"
        f"<b>Targets:</b> {targets_count}\n"
        f"<b>Templates:</b> {templates_count}\n"
    )

    # Dynamic Step-by-Step Setup Wizard Checklist
    checklist = []
    if targets_count == 0:
        checklist.append("1️⃣ Tap <b>👥 Targets</b> to add leads (or scout a group)")
    if templates_count == 0:
        checklist.append("2️⃣ Tap <b>📝 Templates</b> to write your outreach opener")

    if checklist:
        text += "\n📋 <b>Next Setup Steps:</b>\n"
        for step in checklist:
            text += f"• {step}\n"
    else:
        if status_str in ["draft", "paused"]:
            text += "\n✅ <b>Ready to Launch!</b>\n👉 Tap <b>▶️ Start Campaign</b> below to begin outreach.\n"
        elif status_str == "running":
            text += "\n🚀 <b>Campaign is actively dispatching DMs.</b>\n"

    return text

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
