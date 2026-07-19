# ADR-002: Rate limiting at nginx layer (app layer deferred)

## Status: Accepted (partial — app layer deferred)

## Context
Need to protect backend/DB from abuse or spikes.

## Decision
Implement nginx limit_req_zone now. Leave existing app-layer
rate_limit_check() dependency unwired.

## Rationale
App-layer limiter uses an in-memory dict, broken under
deploy.replicas: 2 (each replica has an independent counter — a
client can get ~2x the limit). Shipping it as-is would give false
confidence. Nginx-layer limiting is real protection and doesn't
have this flaw (single nginx instance, IP-keyed).

## At 10x scale
Reimplement app-layer limiter backed by Redis (INCR+EXPIRE or
sliding window) for per-user/per-endpoint limits once shared state
works correctly across replicas.