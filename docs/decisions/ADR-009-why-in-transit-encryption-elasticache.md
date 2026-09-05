# ADR-009: Encryption in transit and AUTH token for ElastiCache Redis

## Status
Accepted

## Context
Migrating Redis from a Docker container to ElastiCache removed the 
implicit network isolation the `private` internal Docker network
provided. RDS's own migration already enabled `sslmode=require`
for postgres_exporter's direct connection — leaving the cache connection
unencrypted would apply an inconsistent security posture across two
services migrated in the same phase.

## Decision
Enabled ElastiCache in-transit encryption, at-rest encryption, and an AUTH
token. Added a new `redis_ssl` setting (default False) to config.py and
conditional `ssl/ssl_cert_reqs` kwargs to the redis.Redis() client
construction in database.py, rather than making TLS unconditional — this
keeps local development against a plain redis:7-alpine container
(if ever needed) working without code changes, consistent with the
env-driven configuration pattern already used for database_url.

redis_exporter's REDIS_ADDR was switched to the `rediss://` scheme with
REDIS_PASSWORD set, matching the direct-to-managed-service pattern
already established for postgres_exporter against RDS.

## Consequences
- Consistent in-transit encryption posture across both managed data
  stores introduced in Phase 3.
- New potential failure mode: TLS certificate validation against
  ElastiCache's cert chain, from both the backend and redis_exporter —
  flagged as unverified until first deploy, same category of risk as the
  PgBouncer SCRAM/port issues hit during the RDS step.
- AUTH token now lives in .env / container environment, same category of
  concern as the RDS master password — reinforces rather than introduces
  the motivating case already noted for a future Secrets Manager migration.