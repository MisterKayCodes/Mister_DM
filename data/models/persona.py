from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

class Persona(Base):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    core_identity = Column(Text, nullable=True)
    lore_branches_json = Column(Text, nullable=True)
    quotes_json = Column(Text, nullable=True)
    traits_json = Column(Text, nullable=True)
    dark_triad_json = Column(Text, nullable=True)
    rules_json = Column(Text, nullable=True)
    
    # Phase 10: Sleep Scheduling
    timezone = Column(String, default="UTC", nullable=False)
    active_hours = Column(String, default="08-22", nullable=False)
    
    created_at = Column(DateTime, default=func.now())

    targets = relationship("Target", back_populates="persona")
    chats = relationship("RelationshipChat", back_populates="persona")
