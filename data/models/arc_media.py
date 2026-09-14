from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

class ArcMedia(Base):
    __tablename__ = "arc_media"

    id = Column(Integer, primary_key=True, autoincrement=True)
    arc_id = Column(Integer, ForeignKey("story_arcs.id"), nullable=False)
    telegram_file_id = Column(String, nullable=False)
    media_type = Column(String, default="photo", nullable=False) # photo, video, voice
    created_at = Column(DateTime, default=func.now())

    story_arc = relationship("StoryArc", back_populates="media_items")
