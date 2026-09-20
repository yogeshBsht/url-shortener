# URL Shortener

A production-grade URL shortener built in phases to demonstrate
backend engineering fundamentals — observability, scalability,
and reliability on AWS.

## Roadmap

| Phase | Focus                          | Status      | Tag                  |
|-------|---------------------------------|-------------|-----------------------|
| 0     | Baseline monolith on EC2        | ✅ Done      | `phase-0-baseline`    |
| 1     | Production-ready foundation     | ✅ Done   |       `phase-1-foundation`                |
| 2     | Observability                   | ✅ Done   |       `phase-2-observability`                |
| 3     | AWS managed services            | 🚧 In Progress (RDS, ElastiCache, ALB/ASG done; ECS/Fargate pending)   | —                      |
| 4     | Load testing                    | ⏳ Planned   | —                      |

## Project Structure

- `backend/` — FastAPI application (Python)
- `frontend/` — React interface
- `infra/` — Terraform for Phase 3's AWS infra (VPC, RDS,
  ElastiCache, ALB/ASG, monitoring instance, IAM, VPC endpoints)
- `docker-compose.yml` / `docker-compose.prod.yml` — Local development
  and prod-like local testing (single-host, unchanged since Phase 2)
- `docker-compose.app.yml` / `docker-compose.app.prod.yml` — The
  app-only stack (pgbouncer, backend, frontend, node_exporter) that
  runs on each AWS Auto Scaling Group instance
- `docker-compose.monitoring.yml` / `docker-compose.monitoring.prod.yml`
  — The observability stack (Prometheus, Grafana, exporters), relocated
  to one dedicated monitoring EC2 instance in Phase 3
- `.env.example` — Template for all required environment variables
- `docs/architecture/` — Architecture diagrams, one per phase
- `docs/decisions/` — [Architecture Decision Records](docs/decisions/) explaining key tradeoffs

## Quick Start

Prerequisites: Docker and Docker Compose installed.

```bash
cp .env.example .env
docker compose up
```

Then open `http://localhost` in your browser.

See `.env.example` for all required variables (database, Redis, CORS, feature flags).

## Running in prod-like mode locally
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Applies resource limits (mem_limit/cpus) and bounded log rotation
(max 10MB × 3 files per container), approximating the target EC2
instance's constraints — useful for catching resource-starvation or
log-growth issues.

## AWS Deployment (Phase 3: RDS + ElastiCache + ALB/ASG, via Terraform)

This supersedes the single-EC2 deployment below for any tag from
`phase-3` onward. Infrastructure is provisioned with Terraform
(`infra/`); application/monitoring containers run via Docker Compose,
pulled from ECR onto EC2 instances launched from a pre-baked "golden"
AMI.

### Prerequisites
- Terraform >= 1.5, AWS CLI, Docker
- An IAM identity with broad provisioning permissions (VPC, EC2, RDS,
  ElastiCache, IAM, S3, SSM, ELB, Auto Scaling); don't reuse a
  narrowly-scoped service credential for this; create a dedicated
  deployer identity
- Images pushed to ECR: `urlshortener-backend`, `urlshortener-frontend`
  (built from this repo), plus mirrors of `edoburu/pgbouncer`,
  `prom/node-exporter`, `prom/prometheus`, `grafana/grafana`,
  `oliver006/redis_exporter`, `prometheuscommunity/postgres-exporter`
  — private subnets have no internet route, so third-party images must
  be re-hosted in ECR, not pulled from Docker Hub at boot
- A "golden" AMI with Docker and the AWS CLI pre-installed, built once
  via a throwaway public-subnet builder instance (private subnets
  can't reach `apt`/Docker's/AWS CLI's download URLs at boot either)
- `app-config.tar.gz` / `monitoring-config.tar.gz` — tarballs of the
  respective `docker-compose*.yml` files (+ `prometheus/`,
  `grafana/provisioning/` for the monitoring bundle), uploaded to the
  Terraform-managed S3 bucket

### Steps

1. Copy and fill in `infra/terraform.tfvars.example` as
   `infra/terraform.tfvars` (account ID, golden AMI ID, RDS/Redis
   credentials, Grafana admin/proxy credentials). This file is
   gitignored — never commit real credentials here.

2. A single `apply` provisions the full stack and correctly sequences
   the app's `.env` (rendered from `templates/env.tftpl`) to be created
   only after the ALB, RDS, and ElastiCache exist — their real
   endpoints are interpolated directly into the SSM parameter, no
   manual patching required.
   ```bash
   cd infra
   terraform init
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

3. Verify:
   ```bash
   terraform output alb_dns_name
   curl http://$(terraform output -raw alb_dns_name)/alb-health
   curl http://$(terraform output -raw alb_dns_name)/api/docs
   curl -i http://$(terraform output -raw alb_dns_name)/grafana/
   ```

4. To scale down for cost control between sessions:
   ```bash
   terraform plan -destroy -out=destroy.tfplan
   terraform apply destroy.tfplan
   ```
   ECR images, the golden AMI, and (if you choose to keep them) the S3
   config bundles are unaffected by `destroy` — they're not tracked in
   Terraform state and cost negligibly to leave in place, avoiding a
   full rebuild-from-scratch on the next `apply`.

### Notes
- Debugging a running instance: no SSH/bastion — use **Session
  Manager** (`EC2 Console → instance → Connect → Session Manager`),
  enabled via each instance's IAM role.
- Inspecting Prometheus directly: SSM port-forward to the monitoring
  instance rather than opening port 9090 in any security group, same
  principle as the Phase 2 SSH-tunnel convention.
- If a launch template or the monitoring instance's `instance_type`
  changes, existing instances aren't updated automatically — terminate
  ASG instances manually (or use `aws autoscaling start-instance-refresh`)
  to roll them onto the new configuration.

## AWS EC2 Deployment (Phase ≤2, historical — single instance, no managed services)

Retained for reference when checking out `phase-0-baseline` through
`phase-2-observability`. Superseded by the Terraform-based deployment
above from Phase 3 onward.

### Prerequisites
- EC2 instance running Ubuntu, with Docker and Docker Compose installed.
  **t3.small (2GB) minimum recommended** as t3.micro (1GB) was found to
  hit host-level OOM under the Phase 2 observability stack's load
  testing (Prometheus + Grafana + 3 exporters add real memory pressure
  on top of the app itself); confirmed via dmesg correlated against
  the test window
- Security Group inbound rules: port 80 (HTTP) and port 22 (SSH) open

### Steps

1. Clone the repo and check out the tag you want to deploy:
   ```bash
   git clone <repo-url>
   cd url-shortener
   git checkout phase-2-observability
   ```

2. Some Ubuntu AMIs ship with Apache pre-installed and bound to port 80,
   which will conflict with the frontend container. Check and disable it:
   ```bash
   sudo lsof -i :80
   sudo systemctl stop apache2 && sudo systemctl disable apache2   # if present
   ```

3. Copy the env template and fill in your EC2 public IP:
   ```bash
   cp .env.example .env
   # set BASE_URL, FRONTEND_BASE_URL, API_BASE_URL to http://<EC2_PUBLIC_IP>
   # set CORS_ORIGINS to include http://<EC2_PUBLIC_IP>
   ```

4. Generate the nginx basic-auth file that gates Grafana:
   ```bash
   sudo apt-get update && sudo apt-get install -y apache2-utils
   htpasswd -c frontend/.htpasswd admin
   ```
   This step must be repeated on every fresh EC2 instance; 
   it will not come from `git pull` as `frontend/.htpasswd` is gitignored.

   (From Phase 3 onward, this is generated automatically at container
   startup instead — see the AWS Deployment section above.)

5. Enable memory overcommit for Redis background saves:
   ```bash
   sudo sysctl vm.overcommit_memory=1
   echo 'vm.overcommit_memory = 1' | sudo tee -a /etc/sysctl.conf
   ```

6. Build and start:
   ```bash
   docker compose up --build -d
   ```

7. Enable `pg_stat_statements` for query-performance metrics (one-time
   per fresh database volume. It is required for the Database Health
   dashboard's slow-query panel; `postgres_exporter` will log
   `relation "pg_stat_statements" does not exist` until this is run):
   ```bash
   docker compose exec postgres env | grep POSTGRES   # confirm actual user/db values
   docker compose exec postgres psql -U <actual_user> -d <actual_db> \
     -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
   docker compose restart postgres_exporter
   ```
   Use the literal values from the `env` check above, not shell
   variables like `${POSTGRES_USER}` — those are only auto-exported
   inside the container via `env_file`, not in your interactive shell,
   and silently expand to empty/default values otherwise.

   (From Phase 3 onward, this runs automatically at backend startup —
   see `ensure_extensions()` in `database.py`.)

8. Verify:
   ```bash
   docker compose ps                       # all services should show "Up"
   curl http://<EC2_PUBLIC_IP>/api/docs    # should return the FastAPI docs page
   curl -i http://<EC2_PUBLIC_IP>/grafana/            # should return 401 (basic auth required)
   curl -i -u admin:<password> http://<EC2_PUBLIC_IP>/grafana/   # should return 200
   ```

9. Open `http://<EC2_PUBLIC_IP>` in a browser, and
   `http://<EC2_PUBLIC_IP>/grafana/` for dashboards (basic-auth
   prompt, then Grafana login).

### Notes
- Do not open ports 9090 (Prometheus) or 3000 (Grafana) in the
  Security Group as both are reachable only through nginx on port 80,
  by design. To inspect Prometheus's `/targets` page directly, use an
  SSH tunnel instead of opening a port:
```bash
  ssh -L 9090:localhost:9090 ec2-user@<ec2-public-ip>
```
  then browse `http://localhost:9090/targets` locally.

## Architecture Evolution

This project is being built in 4 phases.

### Phase 0: Baseline Architecture

<img src="docs/architecture/phase-0.png" alt="Phase 0 architecture" width="600"/>

#### Known Limitations
- Nginx and the React build share one container (will separate in a later phase)
- No network segmentation — Redis/Postgres share the app's Docker network (Phase 1)
- Single EC2 instance — no redundancy at the infra level (Phase 3)

### Phase 1: Production-Ready Foundation

<img src="docs/architecture/phase-1.png" alt="Phase 1 architecture" width="600"/>

#### Known Limitations
- Nginx and the React build share one container
- Single EC2 instance — no redundancy at the infra level
- App-layer rate limiting, though unused, is broken if multiple backend replicas are deployed.
- docker-compose.prod.yml resource limit values are placeholders. To be updated after load testing.

### Phase 2: Observability

<img src="docs/architecture/phase-2.png" alt="Phase 2 architecture" width="600"/>

#### Known Limitations
- Nginx and the React build still share one container
- Single EC2 instance — no redundancy at the infra level (Phase 3)
- Slowest Queries dashboard shows queryid only, not query text due to
  exporter version limitation
- docker-compose.prod.yml resource limit values (including the new
  observability containers) are still placeholders pending Phase 4's
  real load-test numbers
- t3.small confirmed sufficient for Phase 2's light/moderate load
  testing; not yet validated under Phase 4's heavier load scenarios

### Phase 3: AWS Managed Services (in progress)

<!-- <img src="docs/architecture/phase-3.png" alt="Phase 3 architecture" width="600"/> -->

RDS PostgreSQL (with PgBouncer), ElastiCache Redis, and an ALB + Auto
Scaling Group replace the single EC2 instance's containerized Postgres,
Redis, and app hosting. A dedicated monitoring instance hosts
Prometheus/Grafana/exporters, discovering ASG instances dynamically via
EC2 tags rather than Docker DNS. Nginx and the React build still share
one container. ECS/Fargate (replacing the EC2/ASG layer) is the
remaining part of this phase.

#### Known Limitations
- RDS and ElastiCache are single-AZ (free-tier cost tradeoff); an
  AZ-b app instance takes a cross-AZ hop to reach both. Multi-AZ not
  yet enabled, and app-level retry behavior during an RDS-failover-
  style DNS repoint is untested as a result
- Monitoring instance is a single point of observability failure and
  is not in an Auto Scaling Group — requires manual relaunch if it
  fails, unlike app instances
- VPC interface endpoints (~$43/month) are the real, ongoing cost of
  the NAT-Gateway-free, bastion-free network design
- Golden AMI (Docker + AWS CLI pre-baked) requires manual rebuilding
  on any tooling version bump — not yet automated
- ASG's scaling target value (1000 requests/target) is a placeholder
  pending Phase 4's real load-test data
- Nginx and the React build still share one container (deferred again)

## Architecture Decisions

Key technical tradeoffs are documented as ADRs in [`docs/decisions/`](docs/decisions/).

## License

MIT