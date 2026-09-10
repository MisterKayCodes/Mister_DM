from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from data.database import AsyncSessionLocal
from data.repositories import target_repo
from data.models.target import Target
from utils.dto_builders import target_to_dto
from services.handoff_service import HandoffService
from services.intake_service import IntakeService
from sqlalchemy import select

router = APIRouter(tags=["Leads"])

class LeadIntakeRequest(BaseModel):
    campaign_id: Optional[int] = None
    username: str
    telegram_user_id: Optional[int] = None
    source_group: Optional[str] = None
    profile_notes: Optional[str] = None
    profile_confidence: Optional[int] = 0

class LeadBulkIntakeRequest(BaseModel):
    leads: List[LeadIntakeRequest]

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
    """Single lead intake from Mister Profiler or API."""
    campaign_id = payload.campaign_id
    if not campaign_id and payload.source_group:
        campaign_id = await IntakeService.find_campaign_for_group(payload.source_group)
        
    if not campaign_id:
        raise HTTPException(status_code=400, detail="campaign_id is required or source_group must match an active campaign")

    res = await IntakeService.process_single(
        campaign_id=campaign_id,
        username=payload.username,
        telegram_user_id=payload.telegram_user_id,
        source_group=payload.source_group,
        profile_notes=payload.profile_notes,
        profile_confidence=payload.profile_confidence or 0
    )
    return {"status": "success", "data": res}

@router.post("/leads/intake/bulk")
async def bulk_intake_leads(payload: LeadBulkIntakeRequest):
    """Batch lead intake (up to 100 profiled leads) from Mister Profiler."""
    if not payload.leads:
        return {"status": "success", "summary": {"total": 0, "created": 0, "merged": 0, "failed": 0}}
        
    if len(payload.leads) > 100:
        raise HTTPException(status_code=400, detail="Batch size limit exceeded. Maximum 100 leads per request.")

    raw_items = [item.model_dump() for item in payload.leads]
    summary = await IntakeService.process_bulk(raw_items)
    return {"status": "success", "summary": summary}

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
        
    success, msg = await HandoffService.execute_handoff(lead_id)
    if not success:
        raise HTTPException(status_code=502, detail=f"Handoff failed: {msg}")
    return {"status": "success", "message": "Handoff approved and transferred to Mister AI"}

@router.post("/leads/{lead_id}/handoff/reject")
async def reject_handoff(lead_id: int):
    async with AsyncSessionLocal() as session:
        target = await target_repo.get_target_by_id(session, lead_id)
        if not target:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        target.handoff_status = "rejected"
        await session.commit()
        return {"status": "success", "message": "Handoff rejected"}

@router.post("/leads/handoff/retry")
async def retry_failed_handoffs():
    count = await HandoffService.retry_failed_handoffs()
    return {"status": "success", "retried_successes": count}
