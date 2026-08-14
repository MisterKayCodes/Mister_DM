# LAYER: Memory (Model) — ORM table definitions only. No business logic.
from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from sqlalchemy.sql import func
from . import Base

class Blacklist(Base):
    __tablename__ = "blacklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=True)
    username = Column(String, unique=True, nullable=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
