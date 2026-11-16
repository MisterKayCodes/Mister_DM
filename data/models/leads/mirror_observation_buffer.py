from sqlalchemy import Column, Integer, Text, DateTime, Boolean, ForeignKey, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from data.models import Base

class MirrorObservationBuffer(Base):
    __tablename__ = 'mirror_observation_buffer'

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_id = Column(Integer, ForeignKey('targets.id'), nullable=False, index=True)
    relationship_message_id = Column(Integer, ForeignKey('relationship_messages.id'), nullable=True)
    message_text = Column(Text, nullable=False)
    observed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    is_analyzed = Column(Boolean, default=False, nullable=False, index=True)
    analysis_batch_id = Column(String(64), nullable=True, index=True)

    # Relationship back to Target
    target = relationship('Target', backref='mirror_observations')

    def to_dict(self):
        return {
            'id': self.id,
            'target_id': self.target_id,
            'relationship_message_id': self.relationship_message_id,
            'message_text': self.message_text,
            'observed_at': self.observed_at.isoformat() if self.observed_at else None,
            'is_analyzed': self.is_analyzed,
            'analysis_batch_id': self.analysis_batch_id
        }
