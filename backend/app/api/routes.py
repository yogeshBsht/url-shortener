from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import URLCreate, URLResponse, AnalyticsResponse, HealthResponse, ErrorResponse
from app.services.url_service import URLService
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    
    # Check database
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Check Redis
    try:
        from app.database import redis_client
        redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
    
    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"
    
    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        database=db_status,
        redis=redis_status,
    )


@router.post(
    "/api/shorten",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Custom alias already taken"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
    },
    tags=["URLs"]
)
async def shorten_url(
    url_data: URLCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create a short URL.
    
    - **url**: Original URL to shorten (required)
    - **custom_alias**: Custom alias (optional, alphanumeric + hyphens/underscores)
    """
    client_ip = request.client.host if request.client else None
    return URLService.create_short_url(db, url_data, client_ip)

# Deprecated method
# @router.get(
#     "/api/{short_code}",
#     responses={
#         404: {"model": ErrorResponse, "description": "Short URL not found"},
#         410: {"model": ErrorResponse, "description": "Short URL expired"},
#     },
#     tags=["URLs"]
# )
async def redirect_url(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Redirect to original URL.
    
    - **short_code**: Short code or custom alias
    """
    # Get original URL
    original_url = URLService.get_original_url(db, short_code)
    
    # Track click (async, non-blocking)
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None
    referer = request.headers.get("referer")
    
    URLService.track_click(db, short_code, user_agent, client_ip, referer)
    
    # RedirectResponse is not working when integrated with reactJS as the browser hides the location during fetch()
    # the browser intentionally filters out all headers including Location for an opaqueredirect response
    return RedirectResponse(url=original_url, status_code=status.HTTP_301_MOVED_PERMANENTLY)


@router.get(
    "/api/{short_code}",
    responses={
        404: {"model": ErrorResponse, "description": "Short URL not found"},
        410: {"model": ErrorResponse, "description": "Short URL expired"},
    },
    tags=["URLs"]
)
async def redirect_url(
    short_code: str,
    request: Request,
    referer: str = "",
    db: Session = Depends(get_db)
):
    """
    Resolve short code to original URL and track the click.
    Returns JSON instead of redirecting — used by the React frontend
    to perform a client-side redirect while still tracking clicks.

    - **short_code**: Short code or custom alias
    - **referer**: Referer URL passed as query param by the frontend
    """
    # Resolve original URL (raises 404/410 if not found/expired)
    original_url = URLService.get_original_url(db, short_code)

    # Mirror the same click tracking as the /{short_code} redirect endpoint.
    # User-Agent comes from X-Forwarded-User-Agent (set by frontend fetch)
    # with a fallback to the standard header.
    user_agent = (
        request.headers.get("x-forwarded-user-agent")
        or request.headers.get("user-agent")
    )
    client_ip = request.client.host if request.client else None

    URLService.track_click(db, short_code, user_agent, client_ip, referer or None)

    return {"original_url": original_url}


@router.get(
    "/api/analytics/{short_code}",
    response_model=AnalyticsResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Short URL not found"},
        403: {"model": ErrorResponse, "description": "Analytics disabled"},
    },
    tags=["Analytics"]
)
async def get_analytics(short_code: str, db: Session = Depends(get_db)):
    """
    Get analytics for a short URL.
    
    - **short_code**: Short code or custom alias
    """
    return URLService.get_analytics(db, short_code)