from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

class RelationshipChat(Base):
    __tablename__ = "relationship_chats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)
    current_week = Column(Integer, default=1, nullable=False)
    goal = Column(String, nullable=True)
    started_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

    target = relationship("Target")
    persona = relationship("Persona", back_populates="chats")
    messages = relationship("RelationshipMessage", back_populates="chat", cascade="all, delete-orphan")
