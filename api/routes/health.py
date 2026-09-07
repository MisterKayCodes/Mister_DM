from fastapi import APIRouter
from data.database import AsyncSessionLocal
from sqlalchemy import text

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    db_status = "disconnected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "service": "mister_dm",
        "version": "1.0.0",
        "database": db_status
    }
