# ADR-007: Nginx Rate-Limit Visibility via Internal Marker Route

## Status
Accepted

## Context
Nginx's `limit_req` rejects requests with 429 before they ever reach
the backend (per ADR-002's rate limiting layer). Due to this
MetricsMiddleware and structlog had zero visibility into rate-limited
traffic. This made the "Requests by Status Code" dashboard panel
blind to one of the app's own protective mechanisms.

## Decision
Use nginx's `error_page 429 = @named_location` to internally route
429s through a tiny backend marker endpoint (`/api/internal/rate-limited`)
before the 429 is returned to the client, incrementing a
`rate_limited_total` counter there.

## Alternatives considered
- **A dedicated exporter/log-scraper for nginx's own access log**:
  rejected as disproportionate. It adds a new container purely to solve
  one metric, when the existing app-metrics pipeline can absorb it
  with a few lines of config and one new route.
- **Leave it as an unobserved gap, documented**: considered, but
  rejected once it was clear the fix was cheap and directly served the
  Phase 2 goal of demonstrating rate limiting's effect on dashboards.

## Consequences
- Named nginx locations disallow a URI part in `proxy_pass`. It required
  `rewrite ^ /api/internal/rate-limited break;` instead of a URI
  suffix, a different constraint than the /grafana/ proxy_pass fix,
  which needed the opposite (no rewrite, full URI passthrough).
- The marker route itself passes through the existing
  `http_request_duration_seconds{status="429"}` series via
  MetricsMiddleware. This meant that the `rate_limited_total` and the 
  status-code breakdown both capture the same event. Kept only in the 
  status-code panel to avoid a duplicate/overlapping series; 
  `rate_limited_total` remains available for a future dedicated panel or 
  alert rule.