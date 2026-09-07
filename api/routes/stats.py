from fastapi import APIRouter
from data.database import AsyncSessionLocal
from data.repositories import stats_repo
from data.models.target import Target
from sqlalchemy import select, func

router = APIRouter(tags=["Stats"])

@router.get("/stats/global")
async def global_stats():
    async with AsyncSessionLocal() as session:
        global_data = await stats_repo.get_global_stats(session)
        return {"status": "success", "data": global_data}

@router.get("/stats/triage")
async def triage_stats():
    async with AsyncSessionLocal() as session:
        counts = {"UNCLASSIFIED": 0, "TRANSACTIONAL": 0, "RELATIONAL": 0, "DEAD": 0}
        if hasattr(Target, "triage_status"):
            res = await session.execute(
                select(Target.triage_status, func.count(Target.id))
                .group_by(Target.triage_status)
            )
            for status_val, count in res.all():
                if status_val in counts:
                    counts[status_val] = count
                else:
                    counts[status_val] = count
        return {"status": "success", "data": counts}
