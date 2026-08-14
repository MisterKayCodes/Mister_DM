from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    session_string = Column(String, nullable=False)
    delay_min = Column(Integer, nullable=False, default=1)
    delay_max = Column(Integer, nullable=False, default=3)
    is_active = Column(Boolean, default=True)
    
    # Phase 10B: Daily Send Limits
    daily_limit = Column(Integer, default=40)
    messages_sent_today = Column(Integer, default=0)
    last_reset_date = Column(Date, default=func.current_date())

    created_at = Column(DateTime, default=func.now())

    campaigns = relationship("Campaign", back_populates="account")
