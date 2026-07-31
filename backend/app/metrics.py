"""
Prometheus metrics definitions for the URL shortener backend.

Scraped via GET /metrics (see main.py). Not proxied through nginx —
same reasoning as ADR-003 (health endpoints not public): only
containers on the `public` Docker network can reach it, not the internet.
"""
from prometheus_client import Counter, Histogram, Gauge

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=(0.005, 0.010, 0.025, 0.050, 0.100, 0.250, 0.500, 1.0, 2.5),
)

CACHE_OPERATIONS = Counter(
    "cache_operations_total",
    "Total Redis cache operations",
    ["operation", "result"],  # operation: get|set — result: hit|miss|error
)

DB_ACTIVE_CONNECTIONS = Gauge(
    "db_active_connections",
    "Active connections in the SQLAlchemy pool",
)

DB_POOL_SIZE = Gauge(
    "db_pool_size",
    "Configured maximum size of the SQLAlchemy connection pool",
)