import pytest
import pytest_asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from data.models import Base, Campaign, Target, Persona
from data.repositories.target_repo import get_target_by_id, add_targets_bulk
from data.repositories.mirror_observations_repo import MirrorObservationsRepository
from services.intelligence_service import IntelligenceService, intelligence_service

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def async_session():
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

        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_trivial_message_filtering(async_session):
    assert IntelligenceService.is_trivial_message("") is True
    assert IntelligenceService.is_trivial_message("   ") is True
    assert IntelligenceService.is_trivial_message("!") is True
    assert IntelligenceService.is_trivial_message("damn") is False
    assert IntelligenceService.is_trivial_message("wow") is False
    assert IntelligenceService.is_trivial_message("seriously?") is False

@pytest.mark.asyncio
async def test_local_features_extraction():
    messages = [
        "yeah bro that's crazy 😂",
        "nahhh seriously?",
        "you can't be serious lol"
    ]
    stats = IntelligenceService.extract_local_features(messages)
    assert stats["avg_word_count"] > 0
    assert stats["emoji_count"] == 1
    assert stats["question_ratio"] == 0.33

@pytest.mark.asyncio
async def test_style_drift_detection():
    casual_profile = {"formality": "casual"}
    assert IntelligenceService.detect_style_drift(casual_profile, "Good afternoon. I would like to discuss the proposal.") is True
    assert IntelligenceService.detect_style_drift(casual_profile, "yeah fr lol") is False

    formal_profile = {"formality": "formal"}
    assert IntelligenceService.detect_style_drift(formal_profile, "bruh that is crazy lmao") is True

@pytest.mark.asyncio
async def test_observation_buffer_and_batch_claiming(async_session):
    repo = MirrorObservationsRepository(async_session)

    # Insert 3 observations
    await repo.add_observation(target_id=1, message_text="hello world")
    await repo.add_observation(target_id=1, message_text="how are you")
    await repo.add_observation(target_id=1, message_text="nice to meet you")

    pending = await repo.get_pending_observations(target_id=1)
    assert len(pending) == 3

    # Claim batch
    claimed = await repo.claim_pending_batch(target_id=1, batch_id="batch-123")
    assert len(claimed) == 3
    assert claimed[0].analysis_batch_id == "batch-123"

    # Verify pending is now empty
    pending_after = await repo.get_pending_observations(target_id=1)
    assert len(pending_after) == 0

    # Mark batch analyzed
    await repo.mark_batch_analyzed("batch-123")
    assert claimed[0].is_analyzed is True

@pytest.mark.asyncio
async def test_high_information_override(async_session):
    target = await get_target_by_id(async_session, 1)
    long_msg = "Bro I just got back from Dubai and the mining operations there are insane. We were looking at setting up 500 ASIC units near the free zone, but power agreements are super complicated right now. What do you think about hosting options in North America instead?"
    
    # Process high info message (>50 words)
    profile = await intelligence_service.process_inbound_message(
        session=async_session,
        target_id=target.id,
        message_text=long_msg
    )
    assert profile is not None
    assert "formality" in profile
