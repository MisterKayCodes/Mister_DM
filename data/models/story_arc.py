from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

class StoryArc(Base):
    __tablename__ = "story_arcs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    delay_days = Column(Integer, default=0, nullable=False)
    theme_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

    persona = relationship("Persona", backref="story_arcs")
    media_items = relationship("ArcMedia", back_populates="story_arc", cascade="all, delete-orphan")
