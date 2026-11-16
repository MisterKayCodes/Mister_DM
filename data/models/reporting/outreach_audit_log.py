from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from data.models import Base

class OutreachAuditLog(Base):
    """
    Tracks every DM dispatch attempt, outcomes, gap times, and daily sequence
    for session health telemetry and risk pattern detection.
    """
    __tablename__ = "outreach_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_name = Column(String(100), index=True, nullable=False)
    target_username = Column(String(100), nullable=True)
    template_id = Column(Integer, nullable=True)
    daily_index = Column(Integer, default=1)
    gap_minutes = Column(Integer, default=0)
    outcome = Column(String(50), nullable=False)  # 'sent', 'flood_wait', 'peer_flood', 'banned', 'error', etc.
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_name": self.session_name,
            "target_username": self.target_username,
            "template_id": self.template_id,
            "daily_index": self.daily_index,
            "gap_minutes": self.gap_minutes,
            "outcome": self.outcome,
            "error_details": self.error_details,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
