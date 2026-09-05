# ADR-010: Dedicated monitoring instance, not duplicated per ASG instance

## Status
Accepted

## Context
Migrating from a single EC2 instance to an Auto Scaling Group required 
deciding where Prometheus/Grafana/exporters run.
Docker Compose's `dns_sd_configs` (ADR-004) resolved container names on a
single host and cannot resolve across separate EC2 instances.

## Decision
Prometheus, Grafana, redis_exporter, and postgres_exporter move to one
dedicated, always-on EC2 instance outside the ASG. node_exporter stays
on every ASG instance as host-specific metrics can't be centralized.
Prometheus discovers ASG instances via `ec2_sd_configs` (EC2 API,
filtered by a `Role=app-server` tag with PropagateAtLaunch), replacing
dns_sd_configs — same underlying problem (don't hardcode targets that
change), different mechanism because the substrate changed from Docker
to EC2.

Rejected: running the full observability stack on every ASG instance.
This would produce N independent Grafanas each showing only its own
instance's metrics, defeating the centralized-dashboard purpose the
stack was built for in Phase 2, while wasting resources on N-1
redundant copies.

## Consequences
- Single pane of glass preserved across a dynamically scaling fleet.
- New dependency: the monitoring instance's IAM role needs
  ec2:DescribeInstances for service discovery to function.
- backend metrics (previously scraped via same-host Docker DNS) now
  reach Prometheus through nginx's new `/metrics` location (see
  ADR-012), and node_exporter's port is now published to the host
  (`9100:9100`) rather than Docker-internal only, since both need to be
  reachable across instances.
- postgres_exporter/redis_exporter relocating required new inbound
  security group rules on RDS and ElastiCache (existing resources from
  ADR-006/ADR-009), not just new rules for new resources.
- Monitoring instance is a new single point of observability failure —
  acceptable for this phase's scope; not the same as an app outage.