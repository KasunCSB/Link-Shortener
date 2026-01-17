from pydantic import BaseModel, HttpUrl, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime
import re


class ShortenRequest(BaseModel):
    """Request schema for creating a short link."""
    model_config = {"extra": "allow"}
    
    url: str = Field(..., description="The URL to shorten")
    custom_code: Optional[str] = Field(
        None,
        min_length=3,
        max_length=20,
        description="Custom short code (optional)"
    )
    expires_in_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Days until link expires (optional)"
    )
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError('Invalid URL format. Must start with http:// or https://')
        
        if len(v) > 2048:
            raise ValueError('URL too long. Maximum 2048 characters.')
        
        return v
    
    @field_validator('custom_code')
    @classmethod
    def validate_custom_code(cls, v):
        if v is None:
            return v
        
        # Only allow alphanumeric and hyphens
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$', v):
            raise ValueError(
                'Custom code must contain only letters, numbers, and hyphens. '
                'Cannot start or end with a hyphen.'
            )
        
        return v.lower()

    @model_validator(mode='before')
    @classmethod
    def map_legacy_fields(cls, values):
        # Allow frontend to send older keys: `custom_suffix` and `expires_at`.
        # Map them to `custom_code` and `expires_in_days` respectively.
        if not isinstance(values, dict):
            return values

        # Map custom_suffix -> custom_code
        if 'custom_suffix' in values and 'custom_code' not in values:
            try:
                values['custom_code'] = values.pop('custom_suffix')
            except Exception:
                pass

        # Map expires_at (ISO date) -> expires_in_days
        if 'expires_at' in values and 'expires_in_days' not in values:
            try:
                from datetime import datetime, timezone
                raw = values.get('expires_at')
                # Accept date-only like YYYY-MM-DD or full ISO
                if isinstance(raw, str):
                    # If only date provided, append time to parse
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
                        selected = datetime.fromisoformat(raw + 'T00:00:00')
                    else:
                        selected = datetime.fromisoformat(raw)
                    today = datetime.now(selected.tzinfo or timezone.utc)
                    diff = selected - today
                    diff_days = int(diff.total_seconds() // 86400)
                    if diff_days < 1:
                        diff_days = 1
                    values['expires_in_days'] = min(diff_days, 365)
            except Exception:
                # If parsing fails, ignore and let validation handle it
                pass

        return values


class ShortenResponse(BaseModel):
    """Response schema for created short link."""
    
    short_url: str
    short_code: str
    original_url: str
    expires_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class LinkStatsResponse(BaseModel):
    """Response schema for link statistics."""
    
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True


class LinkPreviewResponse(BaseModel):
    """Response schema for link preview."""
    
    short_code: str
    original_url: str
    is_safe: bool = True
    warning: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    database: bool
    redis: bool
    version: str
