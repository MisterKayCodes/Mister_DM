from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base

target_pain_tags = Table(
    'target_pain_tags',
    Base.metadata,
    Column('target_id', Integer, ForeignKey('targets.id'), primary_key=True),
    Column('pain_tag_id', Integer, ForeignKey('pain_tags.id'), primary_key=True)
)

class PainTag(Base):
    __tablename__ = "pain_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_normalized = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

    targets = relationship("Target", secondary=target_pain_tags, back_populates="pain_tags")
