from pydantic import BaseModel, HttpUrl, Field, validator
from datetime import datetime
from typing import Optional, List
import re


class URLCreate(BaseModel):
    """Request schema for creating short URL."""
    
    url: HttpUrl = Field(..., description="Original URL to shorten")
    custom_alias: Optional[str] = Field(None, max_length=50, description="Custom alias (optional)")
    frontend_base_url: Optional[str] = None
    
    @validator('custom_alias')
    def validate_custom_alias(cls, v):
        """Validate custom alias format."""
        if v is None:
            return v
        
        # Only allow alphanumeric, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Custom alias can only contain letters, numbers, hyphens, and underscores')
        
        # Reserved words
        reserved = ['api', 'admin', 'analytics', 'health', 'docs', 'qr']
        if v.lower() in reserved:
            raise ValueError(f'"{v}" is a reserved word and cannot be used')
        
        return v


class URLResponse(BaseModel):
    """Response schema for created short URL."""
    
    short_url: str
    short_code: str
    original_url: str
    qr_code: Optional[str] = None  # Base64 encoded QR code
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ClickStats(BaseModel):
    """Click statistics schema."""
    
    date: str
    clicks: int


class AnalyticsResponse(BaseModel):
    """Analytics response schema."""
    
    short_code: str
    original_url: str
    total_clicks: int
    created_at: datetime
    daily_clicks: List[ClickStats] = []
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    detail: str
    error_code: Optional[str] = None


class LivenessResponse(BaseModel):
    """Liveness probe response — process is running, nothing more."""
    status: str


class ReadinessResponse(BaseModel):
    """Readiness probe response — can the instance serve traffic?"""
    status: str
    version: str
    checks: dict[str, str]