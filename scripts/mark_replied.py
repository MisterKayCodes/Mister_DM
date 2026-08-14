import asyncio
import os
import sys

# Add project root to Python path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select
from sqlalchemy import update, func
from data.database import AsyncSessionLocal
from data.models.target import Target

async def mark_targets_replied():
    print("🔄 Marking all 'sent' targets as 'replied'...")
    async with AsyncSessionLocal() as session:
        # Update all targets that have been sent
        stmt = (
            update(Target)
            .where(Target.status == "sent")
            .values(status="replied", replied_at=func.now())
        )
        result = await session.execute(stmt)
        await session.commit()
        
        print(f"✅ Marked {result.rowcount} target(s) as 'replied'.")
        print("💬 You can now see them in the 'Replies' menu in the bot!")

if __name__ == "__main__":
    asyncio.run(mark_targets_replied())
