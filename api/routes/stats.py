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

@router.get("/stats/templates")
async def template_stats():
    """Returns reply rate performance breakdown per opening template."""
    async with AsyncSessionLocal() as session:
        templates_data = await stats_repo.get_template_performance_stats(session)
        return {"status": "success", "data": templates_data}


@router.get("/api/v1/empire-ledger")
async def get_empire_ledger(limit: int = 50):
    """
    👑 Empire Standard Ledger Route for Mister DM.
    Exposes outbound & inbound DM actions formatted for Mister Chief aggregation.
    """
    from data.models.message import MessageLog
    from data.models.target import Target
    from data.models.campaign import Campaign
    from sqlalchemy.orm import selectinload

    async with AsyncSessionLocal() as session:
        stmt = (
            select(MessageLog)
            .options(
                selectinload(MessageLog.target),
                selectinload(MessageLog.campaign)
            )
            .order_by(MessageLog.id.desc())
            .limit(limit)
        )
        res = await session.execute(stmt)
        messages = res.scalars().all()

        formatted_entries = []
        for msg in messages:
            t_name = msg.target.username if msg.target and msg.target.username else (msg.target.phone if msg.target else "N/A")
            c_name = msg.campaign.name if msg.campaign and msg.campaign.name else "General"
            action_name = f"DM_{msg.direction}"

            formatted_entries.append({
                "service": "mister_dm",
                "campaign": c_name,
                "target_type": "DM",
                "target_name": f"@{t_name}" if not t_name.startswith("@") else t_name,
                "action": action_name,
                "session": "Mister_DM",
                "status": "SUCCESS",
                "error": None,
                "timestamp": str(msg.timestamp) if msg.timestamp else ""
            })

        return {
            "service": "mister_dm",
            "total": len(formatted_entries),
            "entries": formatted_entries
        }
