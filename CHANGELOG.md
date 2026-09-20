# Changelog

## [Phase 3] - AWS Managed Services (in progress — RDS, ElastiCache, ALB/ASG done; ECS/Fargate pending)
### Added
- RDS PostgreSQL (db.t3.micro) replacing the containerized `postgres`
  service. PgBouncer added in front (transaction pooling) — RDS's
  ~87 connection ceiling vs. 2 backend replicas' potential 60 direct
  connections was a near-term risk, not theoretical (ADR-008)
- ElastiCache Redis (cache.t3.micro, cluster mode disabled) replacing
  the containerized `redis` service, with in-transit + at-rest
  encryption and an AUTH token (ADR-009); `redis_ssl` config flag
  added to `database.py`, opt-in so local dev against a plain
  container still works unchanged
- ALB + Auto Scaling Group (min=1/desired=1/max=3) replacing the
  single EC2 instance; target-tracking scaling on ALB requests-per-
  target, chosen over CPU given this app's I/O-bound shape
- Dedicated monitoring EC2 instance (fixed private IP) hosting
  Prometheus/Grafana/redis_exporter/postgres_exporter, separated from
  app instances (ADR-010). Prometheus `ec2_sd_configs` (EC2 tag-based
  discovery, filtered on `Role=app-server`) replaces `dns_sd_configs`
  for the `fastapi-backend`/`node_exporter` jobs — same "don't
  hardcode targets that change" problem as ADR-004, new mechanism
  since the substrate moved from Docker to EC2
- ECR mirrors of all third-party images (pgbouncer, node_exporter,
  prometheus, grafana, redis_exporter, postgres_exporter) alongside
  backend/frontend builds, pulled via IAM instance-profile auth
  through VPC interface endpoints (ecr.api, ecr.dkr, ssm, ssmmessages,
  ec2messages, ec2) + an S3 gateway endpoint — private subnets, no NAT
  Gateway, no bastion/SSH (Session Manager instead) (ADR-011)
- `nginx.conf`: `/alb-health` (shallow liveness check for the ALB
  target group, deliberately distinct from the deep `/health/ready`
  Docker check — avoids a shared RDS/ElastiCache blip taking the
  whole fleet out of rotation at once, ADR-012) and `/metrics`
  (proxied to `backend:8000/metrics`, IP-restricted to the monitoring
  instance)
- `docker-compose.app.yml` / `docker-compose.monitoring.yml` (+
  matching `.prod.yml` overlays) splitting the original single-host
  stack for the ASG/monitoring-instance topology
- Runtime rendering of `nginx.conf` (`envsubst`, `MONITORING_PRIVATE_IP`)
  and `frontend/.htpasswd` (`htpasswd` at container start from
  `GRAFANA_PROXY_USER`/`PASSWORD`), replacing build-time baking —
  removes the "regenerate before every build" manual step and the
  "monitoring instance must exist before the frontend image can be
  built" sequencing dependency
- `ensure_extensions()` startup hook in `database.py`, called
  alongside the existing table-creation hook — auto-creates
  `pg_stat_statements`, replacing the manual per-instance `psql` step
- Terraform (`infra/`) covering the full stack introduced in this
  phase: VPC/subnets/VPC endpoints, security groups, IAM roles, S3
  config bucket, an SSM-parameter-backed `.env` rendered via
  `templates/env.tftpl` directly from real resource attributes (ALB
  DNS name, RDS/ElastiCache endpoints) so a single `apply` produces a
  fully working deployment with no manual endpoint patching, RDS,
  ElastiCache, the monitoring instance, and the ALB/launch
  template/ASG/scaling policy
- ADR-008 through ADR-012

### Fixed
- Several deploy-time bugs only surfaced under real AWS conditions,
  not local testing: PgBouncer's healthcheck used `bash`, missing
  from its image; `LISTEN_PORT` defaulted to 5432 while everything
  else assumed 6432; PgBouncer on the `private`-only Docker network
  couldn't resolve/reach RDS at all (`internal: true` blocks all
  external routing) — required dual-homing onto `public` too, a
  narrower version of Phase 1's network segmentation; PgBouncer's
  `AUTH_TYPE` defaulted to `md5`, incompatible with RDS's
  `scram-sha-256`; a hardcoded `REDIS_HOST: redis` override in
  `backend`'s `environment:` block silently beat the correct value in
  `.env` (`environment:` takes precedence over `env_file:`); frontend
  `API_BASE_URL`/`FRONTEND_BASE_URL` missing the `http://` scheme
  caused the browser to treat the ALB hostname as a relative path,
  producing 405s instead of reaching `/api/`

### Known Limitations
- RDS and ElastiCache are single-AZ (free-tier cost tradeoff) — an
  AZ-b app instance takes a cross-AZ hop to reach both; Multi-AZ not
  yet enabled
- App-level connection retry behavior during an RDS-failover-style DNS
  repoint is untested, since Multi-AZ isn't enabled yet
- Monitoring instance is a single point of observability failure and
  is not in an ASG — a failed/terminated monitoring instance requires
  manual relaunch, unlike app instances
- VPC interface endpoints (~$43/month) are the ongoing, real cost of
  the NAT-Gateway-free/bastion-free design — not free, stated plainly
  rather than glossed over
- Golden AMI (Docker + AWS CLI pre-baked, required since private
  subnets have no route to `apt`/Docker Hub/AWS's download URLs) needs
  manual rebuilding via a throwaway public-subnet builder instance on
  any tooling version bump; not yet automated (e.g. via Packer —
  deliberately deferred, same reasoning as choosing SSM over Packer
  for secrets)
- ASG's target-tracking scaling target value (1000 requests/target) is
  a placeholder pending Phase 4's real load-test data
- `.htpasswd`/`nginx.conf` now render at container startup rather than
  build time, but `GRAFANA_PROXY_USER`/`PASSWORD` must be present in
  `.env`/SSM or Grafana access silently breaks with empty credentials
- `aws_ssm_parameter.env`'s `lifecycle { ignore_changes = [value] }`
  combined with `terraform import` on a pre-existing parameter is a
  known rough edge — the ignored attribute doesn't reconcile on that
  first import, requiring a manual temporary removal of the lifecycle
  block to force the templated value through once


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