from datetime import datetime, timedelta, timezone
from typing import Optional, Any, cast
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import Link, Click, BlockedDomain
from .redis_client import RedisService
from .utils import (
    generate_short_code,
    hash_ip,
    is_reserved_code,
    extract_domain,
    detect_user_agent_type,
    sanitize_referer,
    format_short_url
)
from .config import settings


class LinkService:
    """Service for managing shortened links."""
    
    @staticmethod
    def create_link(
        db: Session,
        original_url: str,
        custom_code: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        creator_ip: Optional[str] = None
    ) -> tuple[Optional[Link], Optional[str]]:
        """
        Create a new shortened link.
        Returns (link, error_message).
        """
        # Check for blocked domain
        domain = extract_domain(original_url)
        if domain:
            blocked = db.query(BlockedDomain).filter(
                BlockedDomain.domain == domain
            ).first()
            if blocked:
                return None, f"This domain is blocked: {blocked.reason or 'spam'}"
        
        # Generate or validate short code
        if custom_code:
            code = custom_code.lower()
            
            # Check reserved words
            if is_reserved_code(code):
                return None, "This short code is reserved"
            
            # Check length
            if len(code) < settings.MIN_CUSTOM_CODE_LENGTH:
                return None, f"Code must be at least {settings.MIN_CUSTOM_CODE_LENGTH} characters"
            if len(code) > settings.MAX_CUSTOM_CODE_LENGTH:
                return None, f"Code must be at most {settings.MAX_CUSTOM_CODE_LENGTH} characters"
            
            # Check if code exists (Redis first, then DB)
            if RedisService.code_exists(code):
                return None, "This short code is already taken"
            
            existing = db.query(Link).filter(Link.short_code == code).first()
            if existing:
                return None, "This short code is already taken"
        else:
            # Generate random code
            max_attempts = 10
            code = None
            for _ in range(max_attempts):
                candidate = generate_short_code()
                if not RedisService.code_exists(candidate):
                    existing = db.query(Link).filter(
                        Link.short_code == candidate
                    ).first()
                    if not existing:
                        code = candidate
                        break
            
            if not code:
                return None, "Failed to generate unique code. Please try again."
        
        # Calculate expiry
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        elif settings.DEFAULT_EXPIRY_DAYS:
            expires_at = datetime.now(timezone.utc) + timedelta(days=settings.DEFAULT_EXPIRY_DAYS)
        
        # Create link
        link = Link(
            short_code=code,
            original_url=original_url,
            expires_at=expires_at,
            creator_ip_hash=hash_ip(creator_ip) if creator_ip else None
        )
        
        db.add(link)
        db.commit()
        db.refresh(link)
        
        # Cache in Redis
        RedisService.cache_link(code, original_url)
        RedisService.add_code_to_set(code)
        
        return link, None
    
    @staticmethod
    def get_link_by_code(db: Session, code: str) -> Optional[Link]:
        """Get a link by its short code."""
        return db.query(Link).filter(
            and_(
                Link.short_code == code,
                Link.is_active == True
            )
        ).first()
    
    @staticmethod
    def get_original_url(db: Session, code: str) -> Optional[str]:
        """
        Get original URL for a short code.
        Checks Redis cache first, falls back to DB.
        """
        # Check cache first
        cached = RedisService.get_cached_link(code)
        if cached:
            return cached
        
        # Check database
        link = db.query(Link).filter(
            and_(
                Link.short_code == code,
                Link.is_active == True
            )
        ).first()
        
        if not link:
            return None
        
        # Check expiry
        expires_at_val = cast(Optional[datetime], link.expires_at)
        if expires_at_val and expires_at_val < datetime.now(timezone.utc):
            link.is_active = False  # type: ignore
            db.commit()
            RedisService.delete_cached_link(code)
            RedisService.remove_code_from_set(code)
            return None
        
        # Cache for future requests
        original_url = cast(str, link.original_url)
        RedisService.cache_link(code, original_url)
        
        return original_url
    
    @staticmethod
    def record_click(
        db: Session,
        link: Link,
        ip: Optional[str] = None,
        country: Optional[str] = None,
        referer: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Record a click on a link."""
        # Increment click count
        link.click_count += 1  # type: ignore
        
        # Create click record
        click = Click(
            link_id=link.id,
            ip_hash=hash_ip(ip) if ip else None,
            country=country[:2] if country else None,
            referer=sanitize_referer(referer) if referer else None,
            user_agent_type=detect_user_agent_type(user_agent) if user_agent else None
        )
        
        db.add(click)
        db.commit()
        
        # Update Redis stats
        short_code = cast(str, link.short_code)
        RedisService.increment_click_stats(short_code)
    
    @staticmethod
    def get_link_stats(db: Session, code: str) -> Optional[dict[str, Any]]:
        """Get statistics for a link."""
        link = db.query(Link).filter(Link.short_code == code).first()
        
        if not link:
            return None
        
        short_code = cast(str, link.short_code)
        return {
            "short_code": short_code,
            "original_url": cast(str, link.original_url),
            "short_url": format_short_url(short_code),
            "click_count": cast(int, link.click_count),
            "created_at": cast(datetime, link.created_at),
            "expires_at": cast(Optional[datetime], link.expires_at),
            "is_active": cast(bool, link.is_active)
        }
    
    @staticmethod
    def deactivate_link(db: Session, code: str) -> bool:
        """Deactivate a link."""
        link = db.query(Link).filter(Link.short_code == code).first()
        
        if not link:
            return False
        
        link.is_active = False  # type: ignore
        db.commit()
        
        RedisService.delete_cached_link(code)
        RedisService.remove_code_from_set(code)
        
        return True
    
    @staticmethod
    def cleanup_expired_links(db: Session) -> int:
        """Deactivate all expired links. Returns count of deactivated links."""
        now = datetime.now(timezone.utc)
        
        expired_links = db.query(Link).filter(
            and_(
                Link.expires_at < now,
                Link.is_active == True
            )
        ).all()
        
        count = 0
        for link in expired_links:
            link.is_active = False  # type: ignore
            short_code = cast(str, link.short_code)
            RedisService.delete_cached_link(short_code)
            RedisService.remove_code_from_set(short_code)
            count += 1
        
        db.commit()
        return count
