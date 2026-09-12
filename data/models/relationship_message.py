from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

class RelationshipMessage(Base):
    __tablename__ = "relationship_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("relationship_chats.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())

    chat = relationship("RelationshipChat", back_populates="messages")
    intent = relationship("AIIntent", back_populates="message", uselist=False, cascade="all, delete-orphan")
