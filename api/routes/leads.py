from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from data.database import AsyncSessionLocal
from data.repositories import target_repo
from data.models.target import Target
from sqlalchemy import select

router = APIRouter(tags=["Leads"])

class LeadIntakeRequest(BaseModel):
    campaign_id: int
    username: str
    telegram_user_id: Optional[int] = None
    source_group: Optional[str] = None
    profile_notes: Optional[str] = None
    profile_confidence: Optional[int] = 0

class TriageOverrideRequest(BaseModel):
    triage_status: str

@router.get("/leads")
async def list_leads(
    campaign_id: Optional[int] = None,
    status: Optional[str] = None,
    triage_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    async with AsyncSessionLocal() as session:
        query = select(Target)
        if campaign_id:
            query = query.where(Target.campaign_id == campaign_id)
        if status:
            query = query.where(Target.status == status)
        if hasattr(Target, "triage_status") and triage_status:
            query = query.where(getattr(Target, "triage_status") == triage_status)
        
        query = query.limit(limit).offset(offset)
        res = await session.execute(query)
        targets = res.scalars().all()
        
        items = []
        for t in targets:
            items.append({
                "id": t.id,
                "campaign_id": t.campaign_id,
                "username": t.username,
                "telegram_user_id": t.telegram_user_id,
                "status": t.status,
                "sent_at": t.sent_at.isoformat() if t.sent_at else None,
                "replied_at": t.replied_at.isoformat() if t.replied_at else None,
                "triage_status": getattr(t, "triage_status", "UNCLASSIFIED"),
                "profile_notes": getattr(t, "profile_notes", None),
                "profile_confidence": getattr(t, "profile_confidence", 0),
                "source_group": getattr(t, "source_group", None),
                "handoff_status": getattr(t, "handoff_status", None),
            })
        return {"status": "success", "count": len(items), "data": items}

@router.get("/leads/{lead_id}")
async def get_lead(lead_id: int):
    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, lead_id)
        if not target:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        data = {
            "id": target.id,
            "campaign_id": target.campaign_id,
            "username": target.username,
            "telegram_user_id": target.telegram_user_id,
            "status": target.status,
            "note": target.note,
            "sent_at": target.sent_at.isoformat() if target.sent_at else None,
            "replied_at": target.replied_at.isoformat() if target.replied_at else None,
            "triage_status": getattr(target, "triage_status", "UNCLASSIFIED"),
            "profile_notes": getattr(target, "profile_notes", None),
            "profile_confidence": getattr(target, "profile_confidence", 0),
            "source_group": getattr(target, "source_group", None),
            "handoff_status": getattr(target, "handoff_status", None),
        }
        return {"status": "success", "data": data}

@router.post("/leads/intake")
async def intake_lead(payload: LeadIntakeRequest):
    async with AsyncSessionLocal() as session:
        clean_user = payload.username.lstrip("@").strip()
        existing = await target_repo.get_target_by_campaign_and_username(session, payload.campaign_id, clean_user)
        
        if not existing:
            added = await target_repo.add_targets_bulk(session, payload.campaign_id, [clean_user])
            await session.commit()
            target = await target_repo.get_target_by_campaign_and_username(session, payload.campaign_id, clean_user)
            if target:
                if payload.telegram_user_id:
                    target.telegram_user_id = payload.telegram_user_id
                if hasattr(target, "profile_notes") and payload.profile_notes:
                    target.profile_notes = payload.profile_notes
                if hasattr(target, "profile_confidence") and payload.profile_confidence:
                    target.profile_confidence = payload.profile_confidence
                if hasattr(target, "source_group") and payload.source_group:
                    target.source_group = payload.source_group
                await session.commit()
                return {"status": "success", "result": "created", "lead_id": target.id}
            return {"status": "success", "result": "created"}
        else:
            # Merge strategy
            if hasattr(existing, "profile_notes") and payload.profile_notes:
                existing.profile_notes = payload.profile_notes
            if hasattr(existing, "profile_confidence") and payload.profile_confidence > getattr(existing, "profile_confidence", 0):
                existing.profile_confidence = payload.profile_confidence
            if hasattr(existing, "source_group") and payload.source_group and not getattr(existing, "source_group", None):
                existing.source_group = payload.source_group
            await session.commit()
            return {"status": "success", "result": "merged", "lead_id": existing.id}

@router.post("/leads/{lead_id}/triage/override")
async def override_triage(lead_id: int, payload: TriageOverrideRequest):
    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, lead_id)
        if not target:
            raise HTTPException(status_code=404, detail="Lead not found")
        if hasattr(target, "triage_status"):
            target.triage_status = payload.triage_status
            await session.commit()
        return {"status": "success", "message": f"Triage status updated to {payload.triage_status}"}

@router.post("/leads/{lead_id}/handoff/approve")
async def approve_handoff(lead_id: int):
    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, lead_id)
        if not target:
            raise HTTPException(status_code=404, detail="Lead not found")
        if hasattr(target, "handoff_status"):
            target.handoff_status = "approved"
            await session.commit()
        return {"status": "success", "message": "Handoff approved"}

@router.post("/leads/{lead_id}/handoff/reject")
async def reject_handoff(lead_id: int):
    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, lead_id)
        if not target:
            raise HTTPException(status_code=404, detail="Lead not found")
        if hasattr(target, "handoff_status"):
            target.handoff_status = "rejected"
            await session.commit()
        return {"status": "success", "message": "Handoff rejected"}
