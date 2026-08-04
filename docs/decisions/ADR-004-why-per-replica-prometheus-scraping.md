# ADR-004: Per-Replica Prometheus Scraping via dns_sd_configs

## Status
Accepted

## Context
The backend runs as 2 replicas (`deploy.replicas: 2`), discovered via
Docker's embedded DNS, which round-robins the `backend` hostname across
both replica IPs. A naive Prometheus scrape config using a single
static target (`backend:8000`) would scrape whichever replica DNS
resolves to on that tick i.e. a different, independent process each time.

## Decision
Use `dns_sd_configs` (DNS-based service discovery) against the `backend`
name, with `type: A`, so Prometheus resolves and scrapes **both**
replica IPs as distinct targets every cycle.

## Alternatives considered
- **Single static target**: rejected; it produces oscillating/discontinuous
  counters as the scraped replica changes between cycles, and silently
  masks a single replica's failure (the other replica keeps answering).
- **docker_sd_config** (Docker API-based discovery): would also work,
  but requires mounting `/var/run/docker.sock` into the Prometheus
  container — effectively host-root access. Rejected for a 2-replica
  setup where DNS-based discovery is sufficient and avoids that
  privilege-escalation surface.

## Consequences
- Verified via a `backend` restart: both targets independently show
  DOWN then UP on Prometheus's `/targets` page, confirming Prometheus
  tracks 2 distinct instances rather than one flip-flopping target.
- Dashboards using replica-level metrics (`db_active_connections`,
  `db_pool_size`) show one series per replica by default; aggregated
  with `sum()` where a single combined view is preferred for
  readability (e.g. Database Health dashboard).
- At 10x scale (many more replicas, or a move to ECS in Phase 3), this
  same DNS-discovery approach doesn't scale cleanly. Phase 3 will need
  ECS-native service discovery (ECS SD / Cloud Map) instead.