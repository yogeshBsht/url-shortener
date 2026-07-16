import hashlib
import string
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models import URL, Click
from app.schemas import URLCreate, URLResponse, AnalyticsResponse, ClickStats
from app.database import get_redis
from app.config import get_settings
from app.services.qr_service import generate_qr_code
import structlog

logger = structlog.get_logger()
settings = get_settings()
redis_client = get_redis()


class URLService:
    """Service for URL shortening operations."""
    
    @staticmethod
    def generate_short_code(url: str, length: int = None) -> str:
        """
        Generate short code from URL hash.
        
        Args:
            url: Original URL
            length: Desired code length (default from settings)
        
        Returns:
            Short code string
        """
        if length is None:
            length = settings.short_code_length
        
        # Hash-based generation (deterministic)
        hash_object = hashlib.md5(url.encode())
        hash_hex = hash_object.hexdigest()
        
        # Convert to base62 (alphanumeric)
        characters = string.ascii_letters + string.digits
        short_code = ""
        
        for i in range(length):
            index = int(hash_hex[i * 2:i * 2 + 2], 16) % len(characters)
            short_code += characters[index]
        
        return short_code
    
    @staticmethod
    def generate_random_code(length: int = None) -> str:
        """Generate random short code (non-deterministic)."""
        if length is None:
            length = settings.short_code_length
        
        characters = string.ascii_letters + string.digits
        return ''.join(random.choices(characters, k=length))
    
    @staticmethod
    def create_short_url(db: Session, url_data: URLCreate, client_ip: str = None) -> URLResponse:
        """
        Create a new short URL.
        
        Args:
            db: Database session
            url_data: URL creation data
            client_ip: Client IP address
        
        Returns:
            URLResponse with short URL details
        
        Raises:
            HTTPException: If custom alias already exists
        """
        original_url = str(url_data.url)
        
        # Determine short code
        if url_data.custom_alias:
            if not settings.enable_custom_alias:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Custom aliases are disabled"
                )
            
            # Check if alias already exists
            existing = db.query(URL).filter(URL.custom_alias == url_data.custom_alias).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Custom alias '{url_data.custom_alias}' is already taken"
                )
            
            short_code = url_data.custom_alias
        else:
            # Generate short code
            short_code = URLService.generate_short_code(original_url)
            
            # Handle collision (rare with MD5)
            attempts = 0
            while db.query(URL).filter(URL.short_code == short_code).first():
                if attempts > 5:
                    # Fallback to random generation
                    short_code = URLService.generate_random_code()
                else:
                    # Try longer hash
                    short_code = URLService.generate_short_code(original_url, length=8)
                attempts += 1
        
        # Create URL record
        url_obj = URL(
            short_code=short_code,
            original_url=original_url,
            custom_alias=url_data.custom_alias,
            creator_ip=client_ip,
        )
        
        db.add(url_obj)
        db.commit()
        db.refresh(url_obj)
        
        # Cache in Redis
        cache_key = f"url:{short_code}"
        try:
            redis_client.setex(
                cache_key,
                settings.redis_cache_ttl,
                original_url
            )
        except Exception as e:
            logger.warning("redis_cache_write_failed", error=str(e))
        
        # Use the frontend domain if provided, otherwise fall back to settings.base_url
        base = url_data.frontend_base_url.rstrip('/') if url_data.frontend_base_url else settings.base_url

        # Generate QR code if enabled
        qr_code_data = None
        if settings.enable_qr_code:
            try:
                short_url = f"{base}/{short_code}"
                qr_code_data = generate_qr_code(short_url)
            except Exception as e:
                logger.error("qr_code_generation_failed", error=str(e))

        return URLResponse(
            short_url=f"{base}/{short_code}",
            short_code=short_code,
            original_url=original_url,
            qr_code=qr_code_data,
            created_at=url_obj.created_at,
            expires_at=url_obj.expires_at,
        )
    
    @staticmethod
    def get_original_url(db: Session, short_code: str) -> str:
        """
        Get original URL from short code.
        
        Args:
            db: Database session
            short_code: Short code
        
        Returns:
            Original URL
        
        Raises:
            HTTPException: If short code not found or expired
        """
        # Check Redis cache first
        cache_key = f"url:{short_code}"
        try:
            cached_url = redis_client.get(cache_key)
            if cached_url:
                logger.info("cache_hit", short_code=short_code)
                return cached_url
        except Exception as e:
            logger.warning("redis_cache_read_failed", error=str(e))
        
        # Cache miss - query database
        url_obj = db.query(URL).filter(
            URL.short_code == short_code,
            URL.is_active == True
        ).first()
        
        if not url_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Short URL '{short_code}' not found"
            )
        
        # Check expiration
        if url_obj.expires_at and url_obj.expires_at < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This short URL has expired"
            )
        
        # Update cache
        try:
            redis_client.setex(
                cache_key,
                settings.redis_cache_ttl,
                url_obj.original_url
            )
        except Exception as e:
            logger.warning("redis_cache_update_failed", error=str(e))
        
        return url_obj.original_url
    
    @staticmethod
    def track_click(db: Session, short_code: str, user_agent: str = None, 
                   ip_address: str = None, referer: str = None):
        """
        Track click event.
        
        Args:
            db: Database session
            short_code: Short code that was clicked
            user_agent: User agent string
            ip_address: Client IP
            referer: HTTP referer
        """
        if not settings.enable_analytics:
            return
        
        try:
            # Increment click count (async, don't block)
            db.query(URL).filter(URL.short_code == short_code).update(
                {URL.click_count: URL.click_count + 1}
            )
            
            # Log click
            click = Click(
                short_code=short_code,
                user_agent=user_agent,
                ip_address=ip_address,
                referer=referer,
            )
            db.add(click)
            db.commit()
        except Exception as e:
            logger.error("click_tracking_failed", error=str(e))
            db.rollback()
    
    @staticmethod
    def get_analytics(db: Session, short_code: str) -> AnalyticsResponse:
        """
        Get analytics for a short URL.
        
        Args:
            db: Database session
            short_code: Short code
        
        Returns:
            AnalyticsResponse with statistics
        
        Raises:
            HTTPException: If analytics disabled or URL not found
        """
        if not settings.enable_analytics:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Analytics are disabled"
            )
        
        # Get URL record
        url_obj = db.query(URL).filter(URL.short_code == short_code).first()
        
        if not url_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Short URL '{short_code}' not found"
            )
        
        # Get daily click stats (last 7 days)
        daily_stats = db.query(
            func.date(Click.clicked_at).label('date'),
            func.count(Click.id).label('clicks')
        ).filter(
            Click.short_code == short_code,
            # Click.clicked_at >= func.now() - func.cast('7 days', type_=func.Interval)
            Click.clicked_at >= func.now() - timedelta(days=7)
        ).group_by(
            func.date(Click.clicked_at)
        ).order_by(
            func.date(Click.clicked_at)
        ).all()
        
        daily_clicks = [
            ClickStats(date=str(row.date), clicks=row.clicks)
            for row in daily_stats
        ]
        
        return AnalyticsResponse(
            short_code=short_code,
            original_url=url_obj.original_url,
            total_clicks=url_obj.click_count,
            created_at=url_obj.created_at,
            daily_clicks=daily_clicks,
        )