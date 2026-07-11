from fastapi import Header, HTTPException, status
from app.config import get_settings
import time

settings = get_settings()

# Simple in-memory rate limiter (use Redis in production)
_rate_limit_store = {}


def rate_limit_check(x_forwarded_for: str = Header(None)):
    """
    Rate limiting dependency.
    
    Args:
        x_forwarded_for: Client IP from header
    
    Raises:
        HTTPException: If rate limit exceeded
    """
    if not settings.enable_rate_limiting:
        return
    
    client_ip = x_forwarded_for or "unknown"
    current_time = int(time.time())
    window_start = current_time - settings.rate_limit_window
    
    # Clean old entries
    if client_ip in _rate_limit_store:
        _rate_limit_store[client_ip] = [
            timestamp for timestamp in _rate_limit_store[client_ip]
            if timestamp > window_start
        ]
    
    # Check rate limit
    request_count = len(_rate_limit_store.get(client_ip, []))
    
    if request_count >= settings.rate_limit_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {settings.rate_limit_requests} requests per {settings.rate_limit_window} seconds."
        )
    
    # Record request
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []
    _rate_limit_store[client_ip].append(current_time)