def render_target_profile(target: dict) -> str:
    """
    Consistently formats the target profile for display.
    Expects a detailed target DTO.
    """
    tags_text = ", ".join([pt["display_name"] for pt in target.get("pain_tags", [])]) if target.get("pain_tags") else "None"
    note_text = target.get("note") if target.get("note") else "No notes."
    
    return (
        f"👤 <b>Target Profile</b>\n\n"
        f"<b>Username:</b> @{target.get('username')}\n"
        f"<b>Status:</b> {target.get('status')}\n\n"
        f"<b>🏷 Assigned Pain Tags:</b>\n{tags_text}\n\n"
        f"<b>📝 Notes:</b>\n{note_text}"
    )
