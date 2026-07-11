from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Boolean, Text, Index
from sqlalchemy.sql import func
from app.database import Base


class URL(Base):
    """URL mapping model."""
    
    __tablename__ = "urls"
    
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(50), unique=True, nullable=False, index=True)
    original_url = Column(Text, nullable=False)
    custom_alias = Column(String(50), unique=True, nullable=True)
    click_count = Column(BigInteger, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    creator_ip = Column(String(45), nullable=True)
    
    __table_args__ = (
        Index('idx_short_code_active', 'short_code', 'is_active'),
    )


class Click(Base):
    """Click tracking model."""
    
    __tablename__ = "clicks"
    
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(50), nullable=False, index=True)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    referer = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_clicks_short_code_time', 'short_code', 'clicked_at'),
    )