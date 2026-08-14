# LAYER: Utilities — Pure functions, no external database dependencies.
import os
import tempfile

def _format_message(msg: dict) -> str:
    """Formats a single message dictionary into a readable string."""
    timestamp = msg.get("timestamp_str", "Unknown Date")
    direction = msg.get("direction", "UNKNOWN")
    msg_type = msg.get("message_type", "TEXT")
    text = msg.get("text") or ""
    
    header = f"[{timestamp}]\n{direction}:"
    
    if msg_type != "TEXT":
        content = f"[{msg_type}] {text}".strip()
    else:
        content = text
        
    return f"{header}\n{content}\n"

def generate_target_export(target_username: str, messages: list[dict]) -> str:
    """
    Generates a readable .txt file for a single target's conversation.
    Returns the absolute filepath to the generated file.
    """
    lines = [
        f"====================================",
        f"TARGET: @{target_username}",
        f"====================================\n\n"
    ]
    
    for msg in messages:
        lines.append(_format_message(msg))
        lines.append("\n")
        
    file_content = "".join(lines)
    
    # Create file in system temp dir
    fd, filepath = tempfile.mkstemp(suffix=".txt", prefix=f"export_{target_username}_")
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(file_content)
        
    return filepath

def generate_campaign_export(campaign_name: str, grouped_messages: dict[str, list[dict]]) -> str:
    """
    Generates a readable .txt file for a whole campaign.
    grouped_messages maps target_username -> list[dict].
    Returns the absolute filepath.
    """
    clean_name = "".join(c if c.isalnum() else "_" for c in campaign_name)
    
    lines = [
        f"CAMPAIGN EXPORT: {campaign_name}\n\n"
    ]
    
    for username, messages in grouped_messages.items():
        lines.append(f"====================================")
        lines.append(f"TARGET: @{username}")
        lines.append(f"====================================\n\n")
        
        for msg in messages:
            lines.append(_format_message(msg))
            lines.append("\n")
            
        lines.append("\n\n")
        
    file_content = "".join(lines)
    
    fd, filepath = tempfile.mkstemp(suffix=".txt", prefix=f"export_{clean_name}_")
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(file_content)
        
    return filepath
