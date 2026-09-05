# ADR-012: Separate shallow endpoint for ALB target health, not /health/ready

## Status
Accepted

## Context
ADR-001 established that `/health/ready` (deep DB/Redis connectivity
check) is deliberately not proxied through nginx, reserved for
Docker's own container healthcheck. Introducing an ALB in front of
multiple instances (Phase 3) requires a target-group health
check endpoint reachable over HTTP.

## Decision
Added a new, shallow `/alb-health` location in nginx that returns a
static 200 with no upstream proxy_pass — confirms only that nginx
itself is alive and reachable, not that RDS/ElastiCache are. This
partially revises ADR-001's "no health endpoints through nginx" stance
by adding one, but preserves its intent: /health/ready still isn't
exposed publicly, and this new endpoint checks a narrower thing on
purpose.

Rejected: pointing the ALB target group at /health/ready directly.
Because ALB pulls unhealthy targets out of rotation fleet-wide, a
shared dependency having a transient blip (RDS/ElastiCache) would mark
every instance unhealthy simultaneously, turning a brief backend
degradation into a total outage — the opposite of what introducing an
ALB was meant to buy.

## Consequences
- ALB target health now reflects only "can this instance serve
  traffic," not "are this instance's dependencies fully healthy" —
  intentional separation of liveness (ALB's concern) from readiness
  (Docker's concern, already handled).
- A genuine RDS/ElastiCache outage will still surface as request-level
  errors from backend rather than instance removal from the ALB —
  acceptable, since removing instances wouldn't have fixed a shared
  dependency outage anyway.
- /metrics also newly proxied through nginx in the same change,
  IP-restricted to the monitoring instance rather than deep-checked or
  public — consistent narrow-exposure approach.