import re
from typing import Optional
from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL string to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def sanitize_custom_alias(alias: str) -> Optional[str]:
    """
    Sanitize and validate custom alias.
    
    Args:
        alias: Custom alias string
    
    Returns:
        Sanitized alias or None if invalid
    """
    if not alias:
        return None
    
    # Remove whitespace
    alias = alias.strip()
    
    # Check length
    if len(alias) > 50 or len(alias) < 3:
        return None
    
    # Only allow alphanumeric, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', alias):
        return None
    
    return alias


def format_number(num: int) -> str:
    """
    Format large numbers with K, M, B suffixes.
    
    Args:
        num: Number to format
    
    Returns:
        Formatted string (e.g., "1.2K", "3.5M")
    """
    if num < 1000:
        return str(num)
    elif num < 1_000_000:
        return f"{num / 1000:.1f}K"
    elif num < 1_000_000_000:
        return f"{num / 1_000_000:.1f}M"
    else:
        return f"{num / 1_000_000_000:.1f}B"