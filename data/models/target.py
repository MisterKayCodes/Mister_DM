from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base


class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    username = Column(String, nullable=False)
    telegram_user_id = Column(BigInteger, nullable=True)
    status = Column(String, default="pending", nullable=False)
    note = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Phase 3: Lead Intelligence & Triage Columns
    triage_status = Column(String, default="UNCLASSIFIED", nullable=False)
    triage_raw_chat = Column(Text, nullable=True)
    profile_notes = Column(Text, nullable=True)
    profile_confidence = Column(Integer, default=0, nullable=False)
    source_group = Column(String, nullable=True)
    handoff_status = Column(String, nullable=True)
    handoff_attempts = Column(Integer, default=0, nullable=False)
    handoff_last_attempt = Column(DateTime, nullable=True)

    # Phase 2: Deep Relational & Engine Additions
    trust_score = Column(Integer, default=0, nullable=False)
    timezone = Column(String, default="Unknown", nullable=False)
    goal = Column(String, nullable=True)
    mirror_profile_json = Column(Text, nullable=True)
    mirror_confidence = Column(Integer, default=0, nullable=False)
    assigned_persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True)

    # Phase 8: War Room & Human Override
    needs_human = Column(Boolean, default=False, nullable=False)

    campaign = relationship("Campaign", back_populates="targets")
    pain_tags = relationship("PainTag", secondary="target_pain_tags", back_populates="targets")
    persona = relationship("Persona", back_populates="targets")

    # Uniqueness is enforced at the database level, not in application code.
    __table_args__ = (
        UniqueConstraint('campaign_id', 'username', name='uix_campaign_username'),
        UniqueConstraint('campaign_id', 'telegram_user_id', name='uix_campaign_tg_id'),
    )
