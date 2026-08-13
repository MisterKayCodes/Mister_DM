from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    status = Column(String, default="draft", nullable=False)
    created_at = Column(DateTime, default=func.now())

    account = relationship("Account", back_populates="campaigns")
    templates = relationship("Template", back_populates="campaign", cascade="all, delete-orphan")
