import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from data.database import AsyncSessionLocal, engine, Base
from data.models import Campaign, Target
from services.relationship_service import RelationshipService
from data.repositories import relationship_chats_repo, relationship_messages_repo, intents_repo, intel_repo

async def run_test():
    print("🚀 Starting Phase 5 Relationship Service Verification Test...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    async with AsyncSessionLocal() as session:
        # 1. Ensure test campaign exists
        campaign = Campaign(name=f"Test Campaign Phase 5 {ts}")
        session.add(campaign)
        await session.flush()

        # 2. Create test target
        target = Target(
            campaign_id=campaign.id,
            username=f"test_lead_{ts}",
            telegram_user_id=123456789,
            triage_status="RELATIONAL",
            status="replied"
        )
        session.add(target)
        await session.commit()
        await session.refresh(target)

        print(f"✅ Created test target ID: {target.id} (@{target.username})")

        # 3. Simulate inbound reply through RelationshipService
        inbound_msg = "Hey Elena, I saw your post about mining hardware. How's the market treating you?"
        print(f"📩 Simulating inbound message: '{inbound_msg}'")

        res = await RelationshipService.handle_reply(
            target_id=target.id,
            inbound_message=inbound_msg,
            session_name="test_session"
        )

        print(f"✨ RelationshipService result: {res}")

        # 4. Verify DB records created
        chat = await relationship_chats_repo.get_chat(session, target.id)
        assert chat is not None, "RelationshipChat should exist"
        print(f"✅ Created RelationshipChat ID: {chat.id} (Week {chat.current_week})")

        msgs = await relationship_messages_repo.get_recent_messages(session, chat.id)
        assert len(msgs) >= 2, "Should have saved at least 2 messages (user + assistant)"
        print(f"✅ Message history saved ({len(msgs)} messages)")

        # Verify assistant message has logged intent
        asst_msg = [m for m in msgs if m.role == "assistant"][-1]
        intent = await intents_repo.get_intent_by_message_id(session, asst_msg.id)
        assert intent is not None, "AIIntent should be logged for assistant message"
        print(f"✅ Logged AI Intent: '{intent.intent_text}' (Confidence: {intent.confidence_score}%)")

        print("\n🎉 Phase 5 Verification Test Passed 100%!")

if __name__ == "__main__":
    asyncio.run(run_test())
