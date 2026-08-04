# ADR-006: postgres_exporter's Built-In stat_statements Collector

## Status
Accepted

## Context
"Slow queries" for the Database Health dashboard needed query-level
timing data. Two approaches existed: an app-level SQLAlchemy event
listener, or Postgres's own `pg_stat_statements` extension via
postgres_exporter.

## Decision
Use `pg_stat_statements` + `postgres_exporter`'s built-in
`--collector.stat_statements` flag.

## Alternatives considered
- **SQLAlchemy event-listener metric (app-level)**: rejected. Only
  sees queries issued through this app (misses migrations/manual
  psql), and query text as a label would need custom
  fingerprinting/normalization to avoid unbounded cardinality, a
  problem `pg_stat_statements` already solves natively via `queryid`.
- **postgres_exporter's queries.yaml / --extend.query-path**: this was
  the initial implementation, but discovered mid-setup to be deprecated
  in the pinned exporter version (v0.15.0); it silently doesn't wire
  up the custom query at all, logging "DEPRECATED" and failing with
  "relation pg_stat_statements does not exist" even after the extension
  was correctly installed. Replaced with the built-in collector flag.

## Consequences
- pg_stat_statements requires `shared_preload_libraries` (a Postgres
  restart) and a one-time `CREATE EXTENSION`, documented as a new EC2
  deployment step. This cost is expected to recur, in a lighter form,
  as an RDS parameter-group change in Phase 3, since RDS natively
  supports this extension. Choosing the DB-level approach now means
  Phase 3 is a config migration, not a rewrite.
- Query **text** (not just queryid) requires
  `--collector.stat_statements.include_query`, which isn't available
  in v0.15.0; the Slowest Queries panel shows queryid only. Manual
  cross-reference via `psql` documented as the workaround; upgrading
  the exporter version is a clean, isolated follow-up, not bundled
  into this change.
- Metric is a cumulative counter (`pg_stat_statements_seconds_total`,
  `_calls_total`), not a pre-computed mean; the dashboard panel
  divides the two directly (all-time average) rather than using
  `rate()`, since a low, sporadic local/test workload produces
  `NaN` under `rate()` when no query repeats within the window.
  Revisit for a `rate()`-based rolling average once Phase 4's
  sustained load testing exists.