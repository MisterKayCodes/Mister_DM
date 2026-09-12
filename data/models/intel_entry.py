from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

class IntelEntry(Base):
    __tablename__ = "intel_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    category = Column(String, nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=False)
    source = Column(String, default="chat")
    created_at = Column(DateTime, default=func.now())

    target = relationship("Target")
