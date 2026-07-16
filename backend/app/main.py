from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
import structlog
from app.config import get_settings
from app.database import engine, Base, redis_client
from app.api.routes import router
from app.logging_config import configure_logging
from app.middleware import RequestLoggingMiddleware

settings = get_settings()

# Configure structlog — every log line is now a single JSON object
# (or a readable console line in debug mode).
configure_logging(debug=settings.debug, log_level=settings.log_level)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("application_starting")

    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("database_tables_created")
    except Exception as e:
        logger.error("database_tables_creation_failed", error=str(e))

    # Test Redis connection
    try:
        redis_client.ping()
        logger.info("redis_connection_established")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))

    yield

    # Shutdown
    logger.info("application_shutting_down")
    redis_client.close()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A scalable URL shortening service with analytics",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Request logging middleware — assigns request_id, logs one JSON line
# per request with path/method/status_code/duration_ms
app.add_middleware(RequestLoggingMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning("validation_error", errors=errors, path=request.url.path)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors,
        }
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors."""
    logger.error("database_error", error=str(exc), path=request.url.path)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred",
            "error_code": "DATABASE_ERROR",
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error("unexpected_error", error=str(exc), path=request.url.path, exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "error_code": "INTERNAL_SERVER_ERROR",
        }
    )


# Include routes
app.include_router(router, prefix="")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Disabled in production",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )