import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.metrics import REQUEST_DURATION

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


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Records http_request_duration_seconds for every request.

    Uses the matched route *template* (e.g. "/api/{short_code}") as the
    `endpoint` label, not the raw path — labeling by raw path would create
    one time series per short code ever generated, an unbounded-cardinality
    problem in Prometheus. Unmatched routes (404s) fall back to the raw
    path since there's no route object; low-traffic enough not to worry
    about for now.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        route = request.scope.get("route")
        endpoint = route.path if route is not None else request.url.path

        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).observe(duration)

        return response