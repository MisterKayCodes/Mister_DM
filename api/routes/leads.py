from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from data.database import AsyncSessionLocal
from data.repositories import target_repo
from data.models.target import Target
from utils.dto_builders import target_to_dto
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
        if triage_status:
            query = query.where(Target.triage_status == triage_status)
        
        query = query.limit(limit).offset(offset)
        res = await session.execute(query)
        targets = res.scalars().all()
        
        items = [target_to_dto(t) for t in targets]
        return {"status": "success", "count": len(items), "data": items}

@router.get("/leads/{lead_id}")
async def get_lead(lead_id: int):
    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, lead_id)
        if not target:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        return {"status": "success", "data": target_to_dto(target)}

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
                await target_repo.update_profile(
                    session=session,
                    target_id=target.id,
                    profile_notes=payload.profile_notes,
                    profile_confidence=payload.profile_confidence or 0,
                    source_group=payload.source_group
                )
                if payload.telegram_user_id:
                    target.telegram_user_id = payload.telegram_user_id
                await session.commit()
                return {"status": "success", "result": "created", "lead_id": target.id}
            return {"status": "success", "result": "created"}
        else:
            # Merge strategy using repo method
            new_confidence = max(existing.profile_confidence or 0, payload.profile_confidence or 0)
            notes_to_use = payload.profile_notes if payload.profile_notes else existing.profile_notes
            source_to_use = payload.source_group if (payload.source_group and not existing.source_group) else existing.source_group
            
            await target_repo.update_profile(
                session=session,
                target_id=existing.id,
                profile_notes=notes_to_use,
                profile_confidence=new_confidence,
                source_group=source_to_use
            )
            await session.commit()
            return {"status": "success", "result": "merged", "lead_id": existing.id}

@router.post("/leads/{lead_id}/triage/override")
async def override_triage(lead_id: int, payload: TriageOverrideRequest):
    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, lead_id)
        if not target:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        await target_repo.update_triage(session, lead_id, payload.triage_status)
        await session.commit()
        return {"status": "success", "message": f"Triage status updated to {payload.triage_status}"}

@router.post("/leads/{lead_id}/handoff/approve")
async def approve_handoff(lead_id: int):
    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, lead_id)
        if not target:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        target.handoff_status = "approved"
        await session.commit()
        return {"status": "success", "message": "Handoff approved"}

@router.post("/leads/{lead_id}/handoff/reject")
async def reject_handoff(lead_id: int):
    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, lead_id)
        if not target:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        target.handoff_status = "rejected"
        await session.commit()
        return {"status": "success", "message": "Handoff rejected"}
