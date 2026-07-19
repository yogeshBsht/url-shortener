# ADR-003: Redis eviction policy — allkeys-lru

## Status: Accepted

## Context
Redis needs a bounded maxmemory to avoid OOM under traffic spikes.
Once full, an eviction policy is required.

## Decision
Use allkeys-lru over noeviction or volatile-lru.

## Rationale
Cached entries (url:{short_code}) are fully re-derivable — a miss
falls back to Postgres. Evicting a "hot but old" key costs one extra
DB query, not broken functionality. noeviction would instead reject
writes once full, surfacing as errors under exactly the load this
is meant to survive.

## At 10x scale
Move to ElastiCache with cluster mode; revisit whether volatile-lru
+ explicit TTLs is worth the complexity if dataset grows beyond
working-set size.