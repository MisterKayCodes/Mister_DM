"""
scripts/seed_messages.py
Inserts mock OUTBOUND + INBOUND messages for all seeded targets.
Run AFTER seed_data.py. Used for testing the Export feature without real Telegram.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

# Project root on path so imports resolve
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import AsyncSessionLocal
from data.models.message import MessageLog
from data.models.target import Target
from data.models.campaign import Campaign
from data.models.account import Account
from sqlalchemy.future import select

# Mock conversation templates — one per target for variety
MOCK_CONVERSATIONS = [
    [
        ("OUTBOUND", "TEXT", "Hey {username}! Saw your profile and thought you'd be a great fit for our VIP program. Interested?"),
        ("INBOUND",  "TEXT", "Hey! Yeah I'm interested, what's it about?"),
        ("OUTBOUND", "TEXT", "It's an exclusive trading signals group. 95% accuracy last month. Want the details?"),
        ("INBOUND",  "TEXT", "Sure send me more info"),
    ],
    [
        ("OUTBOUND", "TEXT", "Hi {username}, quick question — are you still looking for consistent monthly returns?"),
        ("INBOUND",  "TEXT", "Yes actually, what do you have?"),
        ("OUTBOUND", "TEXT", "We run a private Forex signals channel. $3k avg per member last month."),
        ("INBOUND",  "PHOTO", None),  # They sent a screenshot (no text)
    ],
    [
        ("OUTBOUND", "TEXT", "Hey {username}! Reaching out about something exciting in the trading space."),
        ("INBOUND",  "TEXT", "Not interested thanks"),
        ("OUTBOUND", "TEXT", "No worries! If you change your mind, we're here. 🙏"),
        ("INBOUND",  "TEXT", "Actually wait, tell me more"),
    ],
]

async def seed_messages():
    print("📨 Seeding mock messages...")
    
    async with AsyncSessionLocal() as session:
        # Fetch all targets that exist
        result = await session.execute(
            select(Target).join(Campaign).join(Account)
        )
        targets = result.scalars().all()
        
        if not targets:
            print("❌ No targets found. Run seed_data.py first!")
            return

        total = 0
        for i, target in enumerate(targets):
            # Pick a conversation template, cycling through them
            convo = MOCK_CONVERSATIONS[i % len(MOCK_CONVERSATIONS)]
            
            print(f"  💬 Seeding conversation for @{target.username} (ID: {target.id})")
            
            # Space messages 5 minutes apart for realistic timestamps
            base_time = datetime.utcnow() - timedelta(hours=2)
            
            for j, (direction, msg_type, text) in enumerate(convo):
                # Fill in username placeholder if present
                if text:
                    text = text.format(username=target.username)
                
                msg = MessageLog(
                    telegram_message_id=1000 + (i * 10) + j,
                    account_id=target.campaign.account_id,
                    campaign_id=target.campaign_id,
                    target_id=target.id,
                    direction=direction,
                    message_type=msg_type,
                    text=text,
                    timestamp=base_time + timedelta(minutes=j * 5)
                )
                session.add(msg)
                total += 1
        
        await session.commit()
        print(f"\n✅ Seeded {total} messages across {len(targets)} targets.")
        print("🎉 Ready to test Export Chat and Export Campaign!")

if __name__ == "__main__":
    asyncio.run(seed_messages())
