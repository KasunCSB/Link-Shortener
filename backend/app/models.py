from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, BigInteger, Index
from sqlalchemy.sql import func
from .database import Base


class Link(Base):
    """Model for storing shortened links."""
    
    __tablename__ = "links"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    short_code = Column(String(20), unique=True, nullable=False, index=True)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    click_count = Column(BigInteger, default=0, nullable=False)
    creator_ip_hash = Column(String(64), nullable=True)  # SHA-256 hash for privacy
    
    __table_args__ = (
        Index('idx_short_code_active', 'short_code', 'is_active'),
        Index('idx_expires_at', 'expires_at'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Link(code={self.short_code}, url={self.original_url[:50]}...)>"


class Click(Base):
    """Model for storing click analytics."""
    
    __tablename__ = "clicks"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    link_id = Column(BigInteger, nullable=False, index=True)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_hash = Column(String(64), nullable=True)  # SHA-256 hash for privacy
    country = Column(String(2), nullable=True)  # ISO country code from Cloudflare
    referer = Column(String(500), nullable=True)
    user_agent_type = Column(String(20), nullable=True)  # desktop, mobile, tablet, bot
    
    __table_args__ = (
        Index('idx_link_clicked', 'link_id', 'clicked_at'),
    )
    
    def __repr__(self):
        return f"<Click(link_id={self.link_id}, at={self.clicked_at})>"


class BlockedDomain(Base):
    """Model for blocked/spam domains."""
    
    __tablename__ = "blocked_domains"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    reason = Column(String(255), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<BlockedDomain(domain={self.domain})>"
