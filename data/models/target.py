from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey, UniqueConstraint
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

    campaign = relationship("Campaign", back_populates="targets")
    pain_tags = relationship("PainTag", secondary="target_pain_tags", back_populates="targets")

    # Uniqueness is enforced at the database level, not in application code.
    # Two simultaneous imports could both pass a Python-level check and both insert,
    # creating duplicates. A database constraint is atomic — it cannot be raced.
    __table_args__ = (
        UniqueConstraint('campaign_id', 'username', name='uix_campaign_username'),
    )
