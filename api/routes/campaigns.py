from fastapi import APIRouter, HTTPException, status
from services.campaign_service import CampaignService
from services.scheduler_service import SchedulerService
from data.database import AsyncSessionLocal
from data.repositories import campaign_repo, stats_repo
from utils.dto_builders import campaign_to_dto

router = APIRouter(tags=["Campaigns"])

@router.get("/campaigns")
async def list_campaigns():
    async with AsyncSessionLocal() as session:
        campaigns = await campaign_repo.get_all_campaigns(session)
        result = []
        for c in campaigns:
            counts = await stats_repo.get_campaign_target_counts(session, c.id)
            dto = campaign_to_dto(c)
            dto["target_counts"] = counts
            result.append(dto)
        return {"status": "success", "data": result}

@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int):
    async with AsyncSessionLocal() as session:
        campaign = await campaign_repo.get_campaign_by_id(session, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        counts = await stats_repo.get_campaign_target_counts(session, campaign_id)
        dto = campaign_to_dto(campaign)
        dto["target_counts"] = counts
        return {"status": "success", "data": dto}

@router.post("/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: int):
    success, msg, actual_status = await SchedulerService.start_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg, "campaign_status": actual_status}

@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: int):
    success, msg, actual_status = await SchedulerService.pause_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg, "campaign_status": actual_status}

@router.post("/campaigns/{campaign_id}/stop")
async def stop_campaign(campaign_id: int):
    success, msg, actual_status = await SchedulerService.stop_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg, "campaign_status": actual_status}
