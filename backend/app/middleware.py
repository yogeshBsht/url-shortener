import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Binds a request_id to structlog's contextvars for the duration
    of the request (so every log line emitted anywhere during handling
    inherits it), times the request, and logs one line with path,
    method, status_code, and duration_ms. Echoes the id back as
    X-Request-ID so a client-reported error can be traced to a
    specific backend log line.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "request_failed",
                path=request.url.path,
                method=request.method,
                status_code=500,
                duration_ms=duration_ms,
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_handled",
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response