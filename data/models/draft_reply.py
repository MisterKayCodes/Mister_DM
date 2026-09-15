from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from . import Base

class DraftReply(Base):
    """
    ORM model for storing AI-generated reply drafts awaiting human approval
    when APPROVAL_MODE (Training Wheels) is enabled.
    """
    __tablename__ = "draft_replies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("relationship_chats.id"), nullable=False)
    draft_text = Column(Text, nullable=False)
    intent_text = Column(Text, nullable=True)
    confidence_score = Column(Integer, default=75)
    session_name = Column(String(100), nullable=True)
    pending_arc_chapter = Column(Integer, nullable=True)
    pending_media_json = Column(Text, nullable=True)
    war_room_message_id = Column(Integer, nullable=True)
    status = Column(String(50), default="pending", nullable=False)
    processed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
