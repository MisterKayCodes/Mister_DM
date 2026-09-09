from data.models.campaign import Campaign
from data.models.target import Target

def campaign_to_dto(campaign: Campaign) -> dict:
    """
    Single source of truth for the Campaign DTO shape.
    """
    return {
        "id": campaign.id,
        "name": campaign.name,
        "account_id": campaign.account_id,
        "session_name": getattr(campaign, "session_name", None),
        "status": campaign.status,
        "created_at": campaign.created_at,
    }

def target_to_dto(target: Target) -> dict:
    """
    Single source of truth for the Target DTO shape (including Phase 3 Lead Intelligence fields).
    """
    return {
        "id": target.id,
        "campaign_id": target.campaign_id,
        "username": target.username,
        "telegram_user_id": target.telegram_user_id,
        "status": target.status,
        "note": target.note,
        "sent_at": target.sent_at.isoformat() if target.sent_at else None,
        "replied_at": target.replied_at.isoformat() if target.replied_at else None,
        "triage_status": getattr(target, "triage_status", "UNCLASSIFIED"),
        "triage_raw_chat": getattr(target, "triage_raw_chat", None),
        "profile_notes": getattr(target, "profile_notes", None),
        "profile_confidence": getattr(target, "profile_confidence", 0),
        "source_group": getattr(target, "source_group", None),
        "handoff_status": getattr(target, "handoff_status", None),
        "handoff_attempts": getattr(target, "handoff_attempts", 0),
        "handoff_last_attempt": target.handoff_last_attempt.isoformat() if getattr(target, "handoff_last_attempt", None) else None,
    }
