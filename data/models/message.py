# LAYER: Memory (Model) — ORM table definitions only. No business logic.
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

class MessageLog(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_message_id = Column(Integer, nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    
    # "OUTBOUND" or "INBOUND"
    direction = Column(String, nullable=False)
    
    # "TEXT", "PHOTO", "VOICE", "DOCUMENT", "STICKER", "OTHER"
    message_type = Column(String, nullable=False, default="TEXT")
    
    text = Column(String, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    # Phase 5: Template performance tracking
    # Stores which template was used for OUTBOUND messages so Phase 8 can
    # compute reply rates per template (e.g. Template #2 → 24% reply rate)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)

    # Relationships
    target = relationship("Target", backref="messages")
    account = relationship("Account", backref="messages")
    campaign = relationship("Campaign", backref="messages")
    template = relationship("Template", backref="messages")
