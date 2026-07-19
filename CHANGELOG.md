# Changelog

## [Phase 1] - Foundation
### Added
- Docker network segmentation: public (nginx↔api) and private (api↔redis↔postgres, internal: true)
- 2 backend replicas via deploy.replicas
- Structured JSON logging (structlog) with request_id/path/method/status_code/duration_ms per request
- Correlation ID middleware (X-Request-ID header, propagated via contextvars)
- Graceful shutdown (--timeout-graceful-shutdown 30, stop_grace_period: 35s)
- /health/live and /health/ready endpoints (replacing combined /health)
- Nginx-layer rate limiting (limit_req_zone, 10r/s, burst 20)
- Redis maxmemory (env-configurable) + allkeys-lru eviction policy
- docker-compose.prod.yml: resource limits + bounded log rotation
- cache_miss logging alongside existing cache_hit

### Fixed
- SQLAlchemy 2.0 raw SQL error in readiness check (text() wrapping)

### Removed
- Unused /health endpoint, HealthResponse schema, dead healthCheck() frontend export

## [Phase 0] - Baseline
### Added
- Initial FastAPI + React + Redis + Postgres stack on single EC2 via Docker Compose
### Fixed
- Env var sprawl consolidated to single .env source of truth
- Postgres/Redis ports no longer published to host (expose-only)
- Silent config defaults removed (debug/base_url/cors_origins now required)
- frontend Dockerfile npm ci --only=production bug (react-scripts missing)
- Apache2 EC2 port-80 conflict documented