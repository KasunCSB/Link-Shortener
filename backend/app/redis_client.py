import redis
from typing import Optional, Any, cast
from .config import settings

# Redis connection pool
pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    decode_responses=True,
    max_connections=20
)

redis_client = redis.Redis(connection_pool=pool)


class RedisService:
    """Redis service for caching and rate limiting."""
    
    LINK_CACHE_PREFIX = "link:"
    CODES_SET = "codes:used"
    RATE_LIMIT_PREFIX = "ratelimit:ip:"
    STATS_PREFIX = "stats:"
    
    CACHE_TTL = 86400  # 24 hours
    RATE_LIMIT_TTL = 3600  # 1 hour
    
    @staticmethod
    def cache_link(code: str, url: str) -> bool:
        """Cache a short code to URL mapping."""
        try:
            redis_client.setex(
                f"{RedisService.LINK_CACHE_PREFIX}{code}",
                RedisService.CACHE_TTL,
                url
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_cached_link(code: str) -> Optional[str]:
        """Get cached URL for a short code."""
        try:
            result = redis_client.get(f"{RedisService.LINK_CACHE_PREFIX}{code}")
            return cast(Optional[str], result)
        except Exception:
            return None
    
    @staticmethod
    def delete_cached_link(code: str) -> bool:
        """Delete cached link."""
        try:
            redis_client.delete(f"{RedisService.LINK_CACHE_PREFIX}{code}")
            return True
        except Exception:
            return False
    
    @staticmethod
    def add_code_to_set(code: str) -> bool:
        """Add a code to the set of used codes."""
        try:
            redis_client.sadd(RedisService.CODES_SET, code)
            return True
        except Exception:
            return False
    
    @staticmethod
    def code_exists(code: str) -> bool:
        """Check if a code exists in the set."""
        try:
            return bool(redis_client.sismember(RedisService.CODES_SET, code))
        except Exception:
            return False
    
    @staticmethod
    def remove_code_from_set(code: str) -> bool:
        """Remove a code from the set."""
        try:
            redis_client.srem(RedisService.CODES_SET, code)
            return True
        except Exception:
            return False
    
    @staticmethod
    def check_rate_limit(ip: str, limit: Optional[int] = None) -> tuple[bool, int]:
        """
        Check and increment rate limit for an IP.
        Returns (is_allowed, remaining_requests).
        """
        if limit is None:
            limit = settings.RATE_LIMIT_PER_HOUR
        
        key = f"{RedisService.RATE_LIMIT_PREFIX}{ip}"
        
        try:
            current_val = redis_client.get(key)
            
            if current_val is None:
                redis_client.setex(key, RedisService.RATE_LIMIT_TTL, 1)
                return True, limit - 1
            
            current = int(str(current_val))
            
            if current >= limit:
                ttl = redis_client.ttl(key)
                return False, 0
            
            redis_client.incr(key)
            return True, limit - current - 1
            
        except Exception:
            # If Redis fails, allow the request
            return True, limit
    
    @staticmethod
    def increment_click_stats(code: str) -> bool:
        """Increment click stats for a code."""
        try:
            redis_client.incr(f"{RedisService.STATS_PREFIX}{code}:clicks")
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_click_stats(code: str) -> int:
        """Get click stats from Redis."""
        try:
            clicks = redis_client.get(f"{RedisService.STATS_PREFIX}{code}:clicks")
            return int(str(clicks)) if clicks else 0
        except Exception:
            return 0
    
    @staticmethod
    def sync_codes_from_db(codes: list) -> bool:
        """Sync all codes from database to Redis set."""
        try:
            if codes:
                redis_client.delete(RedisService.CODES_SET)
                redis_client.sadd(RedisService.CODES_SET, *codes)
            return True
        except Exception:
            return False
    
    @staticmethod
    def health_check() -> bool:
        """Check Redis connection health."""
        try:
            return bool(redis_client.ping())
        except Exception:
            return False
