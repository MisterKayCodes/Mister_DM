import asyncio
import os
import sys

# Add project root to Python path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import AsyncSessionLocal
from data.models.account import Account
from data.models.campaign import Campaign
from data.models.target import Target

async def seed_data():
    print("🌱 Seeding test data...")
    async with AsyncSessionLocal() as session:
        # 1. Create a dummy account
        dummy_account = Account(
            name="TestAccount",
            session_string="dummy_session_string",
            delay_min=1,
            delay_max=3,
            is_active=True
        )
        session.add(dummy_account)
        await session.flush()
        print(f"✅ Created Account: {dummy_account.name} (ID: {dummy_account.id})")

        # 2. Create a dummy campaign
        dummy_campaign = Campaign(
            name="Test Campaign 1",
            account_id=dummy_account.id,
            status="draft"
        )
        session.add(dummy_campaign)
        await session.flush()
        print(f"✅ Created Campaign: {dummy_campaign.name} (ID: {dummy_campaign.id})")

        # 3. Add 3 dummy targets
        usernames = ["dummy1", "dummy2", "dummy3"]
        targets = []
        for uname in usernames:
            target = Target(
                campaign_id=dummy_campaign.id,
                username=uname,
                status="sent",  # Setting to sent so they can be marked replied
                telegram_user_id=123456789  # Fake telegram ID
            )
            session.add(target)
            targets.append(target)
            
        await session.commit()
        print(f"✅ Added {len(targets)} targets: {', '.join(usernames)}")
        print("🎉 Seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_data())
