from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

class AIIntent(Base):
    __tablename__ = "ai_intents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("relationship_messages.id"), nullable=False)
    intent_text = Column(Text, nullable=False)
    confidence_score = Column(Integer, nullable=False)
    needs_human = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    message = relationship("RelationshipMessage", back_populates="intent")
