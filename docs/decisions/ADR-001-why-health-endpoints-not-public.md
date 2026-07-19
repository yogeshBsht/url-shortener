# ADR-001: /health/live and /health/ready kept internal-only

## Status: Accepted

## Context
Split combined /health into /health/live (liveness) and
/health/ready (readiness, checks DB+Redis, returns 503 when not
ready). Question: expose via nginx publicly?

## Decision
No nginx location for /health/*. Consumed only via direct container
port access (Docker healthcheck now, ALB target group in Phase 3).

## Rationale
Nothing in the architecture needs it public — frontend doesn't call
it (dead code removed), nginx doesn't actively health-check backend.
Public exposure would leak DB/Redis connectivity state as free
reconnaissance. Falls through to the SPA shell via existing catch-all,
same as any unmatched route.