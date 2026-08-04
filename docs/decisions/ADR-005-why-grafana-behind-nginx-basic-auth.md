# ADR-005: Grafana Reverse-Proxied Through Nginx with Basic-Auth Gate

## Status
Accepted

## Context
Grafana dashboards need to be reachable (unlike /health/* and /metrics,
which are deliberately kept off nginx per ADR-001) but they expose
real traffic/business data (RPS, cache hit rates, DB query patterns)
and are operator-facing, not end-user-facing.

## Decision
Reverse-proxy Grafana through nginx at /grafana/, with `auth_basic`
gating that path in front of Grafana's own login page. Grafana itself
has no ports mapping; it is only reachable via nginx.

## Alternatives considered
- **Open, relying only on Grafana's own login**: rejected. Anyone
  reaching port 80 could see the login page itself (version fingerprint,
  confirms Prometheus+Grafana are running) and brute-force a single
  admin account with no rate limiting in front of it; the app's
  existing `limit_req_zone` is scoped to /api/, not /grafana/.

## Consequences
- Two independent layers before Grafana's login is even reached.
- One more credential (`frontend/.htpasswd`) to generate per-instance
  and keep out of git (gitignored, regenerated manually per EC2 host).
- GF_SERVER_ROOT_URL + GF_SERVER_SERVE_FROM_SUB_PATH required for
  Grafana's own asset/redirect URLs to resolve correctly under the
  /grafana/ prefix.
- At 10x scale / multi-user scale, this should be replaced with
  Grafana's own user/team model (or OAuth) rather than a single shared
  basic-auth credential; deferred as out of scope for a single-operator
  portfolio deployment.