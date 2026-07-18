from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import URLCreate, URLResponse, AnalyticsResponse, ErrorResponse, LivenessResponse, ReadinessResponse
from app.services.url_service import URLService
from app.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()
router = APIRouter()


@router.get("/health/live", response_model=LivenessResponse, tags=["Health"])
async def liveness_check():
    """
    Liveness probe — answers only 'is the process running and able
    to respond at all?'. Deliberately does NOT touch the database or
    Redis: a slow/down dependency should not cause an orchestrator to
    kill and restart a perfectly healthy process (that would just
    compound an outage). Should always return 200 as long as the
    event loop is alive and this endpoint can execute.
    """
    return LivenessResponse(status="alive")


@router.get("/health/ready", response_model=ReadinessResponse, tags=["Health"])
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe — answers 'can this instance actually serve
    traffic right now?'. Checks the dependencies a request would
    need: DB and Redis. Returns 503 (not 200) when not ready, so an
    orchestrator/load balancer can correctly stop routing traffic to
    this instance without restarting it — the process itself may be
    fine, it just can't do useful work yet (e.g. DB still starting,
    Redis briefly unreachable).
    """
    checks = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        logger.error("database_readiness_check_failed", error=str(e))
        checks["database"] = "unhealthy"

    try:
        from app.database import redis_client
        redis_client.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        logger.error("redis_readiness_check_failed", error=str(e))
        checks["redis"] = "unhealthy"

    is_ready = all(v == "healthy" for v in checks.values())

    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ReadinessResponse(status="not_ready", version=settings.app_version, checks=checks).model_dump(),
        )

    return ReadinessResponse(status="ready", version=settings.app_version, checks=checks)


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