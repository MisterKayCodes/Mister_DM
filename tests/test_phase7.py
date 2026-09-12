import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from data.models import Base, Campaign, Target
from data.repositories.target_repo import get_target_by_id
from data.repositories.mirror_observations_repo import MirrorObservationsRepository
from services.intelligence_service import IntelligenceService, intelligence_service

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async def test_suite():
    print("--- Running IntelligenceService Test Suite ---")

    # 1. Trivial Message Filtering
    assert IntelligenceService.is_trivial_message("") is True
    assert IntelligenceService.is_trivial_message("   ") is True
    assert IntelligenceService.is_trivial_message("!") is True
    assert IntelligenceService.is_trivial_message("damn") is False
    assert IntelligenceService.is_trivial_message("wow") is False
    assert IntelligenceService.is_trivial_message("seriously?") is False
    print("[PASS] test_trivial_message_filtering PASSED")

    # 2. Local Features Extraction
    messages = [
        "yeah bro that's crazy",
        "nahhh seriously?",
        "you can't be serious lol"
    ]
    stats = IntelligenceService.extract_local_features(messages)
    assert stats["avg_word_count"] > 0
    assert stats["question_ratio"] == 0.33
    print("[PASS] test_local_features_extraction PASSED")

    # 3. Style Drift Detection
    casual_profile = {"formality": "casual"}
    assert IntelligenceService.detect_style_drift(casual_profile, "Good afternoon. I would like to discuss the proposal.") is True
    assert IntelligenceService.detect_style_drift(casual_profile, "yeah fr lol") is False

    formal_profile = {"formality": "formal"}
    assert IntelligenceService.detect_style_drift(formal_profile, "bruh that is crazy lmao") is True
    print("[PASS] test_style_drift_detection PASSED")

    # DB Integration Tests
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Seed campaign & target
        camp = Campaign(name="Test Campaign", status="active")
        session.add(camp)
        await session.commit()

        target = Target(campaign_id=camp.id, username="test_mirror_user")
        session.add(target)
        await session.commit()

        # 4. Observation Buffer & Batch Claiming
        repo = MirrorObservationsRepository(session)
        await repo.add_observation(target_id=target.id, message_text="hello world")
        await repo.add_observation(target_id=target.id, message_text="how are you")
        await repo.add_observation(target_id=target.id, message_text="nice to meet you")

        pending = await repo.get_pending_observations(target_id=target.id)
        assert len(pending) == 3

        claimed = await repo.claim_pending_batch(target_id=target.id, batch_id="batch-123")
        assert len(claimed) == 3
        assert claimed[0].analysis_batch_id == "batch-123"

        pending_after = await repo.get_pending_observations(target_id=target.id)
        assert len(pending_after) == 0

        await repo.mark_batch_analyzed("batch-123")
        assert claimed[0].is_analyzed is True
        print("[PASS] test_observation_buffer_and_batch_claiming PASSED")

        # 5. High Information Override
        long_msg = "Bro I just got back from Dubai and the mining operations there are insane. We were looking at setting up 500 ASIC units near the free zone, but power agreements are super complicated right now. What do you think about hosting options in North America instead?"
        profile = await intelligence_service.process_inbound_message(
            session=session,
            target_id=target.id,
            message_text=long_msg
        )
        assert profile is not None
        assert "formality" in profile
        print("[PASS] test_high_information_override PASSED")

    await engine.dispose()
    print("\n[SUCCESS] ALL PHASE 7 INTELLIGENCE SERVICE TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    asyncio.run(test_suite())
