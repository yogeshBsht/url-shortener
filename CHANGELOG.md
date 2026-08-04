# Changelog

## [Phase 2] - Observability
### Added
- Prometheus scraping FastAPI metrics: http_request_duration_seconds
  (Histogram, method/endpoint/status labels, endpoint labeled by route
  template not raw path to bound cardinality), cache_operations_total
  (Counter, get/set x hit/miss/success/error), db_active_connections
  and db_pool_size (Gauges)
- Per-replica Prometheus scraping via dns_sd_configs against the
  `backend` DNS name, so both replicas are scraped as distinct targets
  instead of one flip-flopping target via round-robin DNS
- Grafana, reverse-proxied through nginx at /grafana/, gated behind
  nginx basic-auth in front of Grafana's own login (defense in depth)
- node_exporter (EC2 host CPU/memory/network/disk), dual-homed
  redis_exporter and postgres_exporter (private+public networks, same
  as backend) for Redis and Postgres-level metrics
- postgres_exporter's built-in --collector.stat_statements enabled
  (pg_stat_statements extension) for query-performance metrics
- rate_limited_total counter + internal /api/internal/rate-limited
  marker route, giving nginx-level 429 rejections visibility in
  Grafana (previously invisible to the app's own metrics/logging)
- 4 Grafana dashboards, auto-provisioned: Request Performance, Cache
  Effectiveness, Database Health, System Resources
- Resource limits (mem_limit/cpus) extended in docker-compose.prod.yml
  to cover all 5 new observability containers
- ADR-004 through ADR-007 documenting Phase 2's key design decisions

### Fixed
- postgres_exporter's queries.yaml/--extend.query-path mechanism
  found deprecated/non-functional in v0.15.0; replaced with the
  built-in --collector.stat_statements flag (query text label
  unavailable in this exporter version — queryid only)
- Grafana nginx proxy_pass self-redirect loop (trailing URI on
  proxy_pass was stripping the /grafana prefix before Grafana saw it,
  conflicting with GF_SERVER_SERVE_FROM_SUB_PATH)

### Known Limitations
- t3.micro found insufficient under Phase 2's load-test pattern;
  confirmed host-level OOM via dmesg correlated against the test
  window, even though all containers stayed healthy. t3.small
  confirmed sufficient (load average <1, >1GB available memory)
  under the same test. Minimum recommended instance size updated
  accordingly.
- Query text unavailable in the Slowest Queries dashboard panel
  (queryid only); the exporter flag for this wasn't available in
  the pinned exporter version; deferred rather than bumping versions
  mid-phase.


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