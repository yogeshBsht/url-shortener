# ADR-011: Container images from ECR via VPC endpoints, not git clone

## Status
Accepted

## Context
ASG instances launch automatically with no manual SSH setup, and were
placed in private subnets (no route to the internet) to match the
target architecture's defense-in-depth posture. New instances need the
application code and, separately, several third-party images
(pgbouncer, node_exporter, and the monitoring stack) with no internet
egress available. A NAT Gateway would provide egress but reintroduces
real recurring cost (~$32/month+) specifically to route around a
problem that has a cheaper, more scoped fix.

## Decision
Build backend/frontend images and mirror all required third-party
images (`edoburu/pgbouncer`, `prom/node-exporter`, `prom/prometheus`,
`grafana/grafana`, `oliver006/redis_exporter`,
`prometheuscommunity/postgres-exporter`) into ECR. Instances pull via
IAM instance-profile authentication (no stored credentials) through
VPC interface endpoints (ecr.api, ecr.dkr) plus the S3 gateway
endpoint (free) that backs ECR layer storage — no NAT Gateway, no
internet route from private subnets at all.

Rejected: plain git clone from a public repo (works for code, not for
third-party images — doesn't solve the whole problem) and a private
repo with a deploy key/PAT (introduces a bootstrap secret to fetch the
code that would fetch other secrets, solving nothing a public repo +
ECR doesn't already solve more simply).

## Consequences
- ~$43/month in VPC interface endpoint costs (`ecr.api`, `ecr.dkr`, `ssm`,
  `ssmmessages`, `ec2messages`, `ec2`) — stated plainly as the real price of
  zero NAT Gateways and zero SSH/bastion exposure, not a free win.
- backend/frontend switch from build: to image: in compose files —
  faster, more consistent ASG scale-out (identical bits on every
  instance) versus rebuilding from source on every boot.
- Directly forward-compatible with Phase 3 (ECS Fargate task
  definitions reference ECR image URIs natively) — this is build-once
  work, not a throwaway step like PgBouncer's EC2-container phase.
- New one-time maintenance task: third-party image mirrors need
  manual re-pull/push on upstream version bumps, unlike a direct
  Docker Hub pull.