# ADR-008: PgBouncer transaction-mode pooling in front of RDS

## Status
Accepted

## Context
RDS db.t3.micro caps max_connections at ~87 (derived from instance memory,
not independently configurable past the parameter group formula). Backend
runs 2 replicas × (pool_size=10 + max_overflow=20) = up to 60 direct
connections at peak, before adding postgres_exporter or ASG scale-out. 
Direct connection exhaustion was assessed as a near-term risk,
not theoretical — Phase 4's load test plan would likely hit it.

## Decision
Added PgBouncer (edoburu/pgbouncer) as a new container between backend and
RDS, in transaction pooling mode, with DEFAULT_POOL_SIZE=15 backend
connections to RDS regardless of replica count.

Transaction mode was chosen over session mode because the codebase uses
psycopg2 (simple query protocol, no server-side prepared statements) via
SQLAlchemy, and every DB session in database.py (get_db, get_db_context) is
scoped to a single request/transaction with no cross-request session state,
advisory locks, or LISTEN/NOTIFY usage. Session mode was ruled out as
unnecessarily conservative given no feature actually requires it.

postgres_exporter was kept on a direct RDS connection, not routed through
PgBouncer, since it's a single low-frequency admin-level connection where
pooling adds no value and directly querying pg_stat_statements is simpler
to reason about.

## Consequences
- Real backend connections to RDS are now bounded and predictable regardless
  of how many app replicas exist — directly enables ASG later
  without revisiting this decision.
- New failure mode: PgBouncer itself is a single point of connectivity for
  all backend replicas. Acceptable for now (matches Phase 1's tolerance of
  single-EC2 as a known limitation); revisited when this becomes an ECS
  sidecar.
- App-level DATABASE_POOL_SIZE/MAX_OVERFLOW settings are now connections to
  PgBouncer, not to Postgres directly — cheap, can stay generous.
- This container is deliberately throwaway infrastructure: expected to be
  re-expressed as a per-task ECS sidecar in later part of Phase 3, not carried
  forward as-is.