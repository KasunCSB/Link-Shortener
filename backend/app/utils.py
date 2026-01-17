import secrets
import string
import hashlib
import re
from urllib.parse import urlparse
from typing import Optional
from user_agents import parse as parse_user_agent  # type: ignore
from .config import settings


def generate_short_code(length: Optional[int] = None) -> str:
    """Generate a random short code using nanoid-style characters."""
    if length is None:
        length = settings.DEFAULT_CODE_LENGTH
    
    # URL-safe characters (similar to nanoid)
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_ip(ip: str) -> str:
    """Hash an IP address for privacy."""
    return hashlib.sha256(ip.encode()).hexdigest()


def is_reserved_code(code: str) -> bool:
    """Check if a code is reserved."""
    return code.lower() in [r.lower() for r in settings.RESERVED_CODES]


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None


def is_valid_url(url: str) -> bool:
    """Validate URL format."""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(url_pattern.match(url))


def detect_user_agent_type(user_agent_string: str) -> str:
    """Detect device type from user agent."""
    if not user_agent_string:
        return "unknown"
    
    try:
        user_agent = parse_user_agent(user_agent_string)
        
        if user_agent.is_bot:
            return "bot"
        elif user_agent.is_mobile:
            return "mobile"
        elif user_agent.is_tablet:
            return "tablet"
        elif user_agent.is_pc:
            return "desktop"
        else:
            return "other"
    except Exception:
        return "unknown"


def sanitize_referer(referer: str) -> Optional[str]:
    """Sanitize and truncate referer URL."""
    if not referer:
        return None
    
    # Remove query parameters for privacy
    try:
        parsed = urlparse(referer)
        sanitized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return sanitized[:500] if len(sanitized) > 500 else sanitized
    except Exception:
        return None


def format_short_url(code: str) -> str:
    """Format a short code into a full URL."""
    base = settings.BASE_URL.rstrip('/')
    return f"{base}/{code}"
