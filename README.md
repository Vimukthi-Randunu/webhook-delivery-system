# Webhook Delivery System

A production-grade webhook delivery system built to demonstrate end-to-end DevOps engineering — infrastructure provisioning, containerization, CI/CD pipelines, secrets management, and observability.

## What It Does

Accepts incoming webhook events via a REST API, queues them in Redis, and delivers them via HTTP POST to a target URL. Failed deliveries are retried automatically. Every event and delivery attempt is persisted in PostgreSQL. The full system is observable via Prometheus and Grafana.

**Flow:** `POST /events` → API saves to PostgreSQL → job pushed to Redis queue → worker picks up job → HTTP POST to target URL → delivery attempt recorded

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │           EC2 Instance 1                │
Internet ──► Route 53 ──► Nginx (80/443)                          │
                        │   ├── API (FastAPI, port 8000)          │
                        │   ├── Worker (RQ)                       │
                        │   ├── Redis                             │
                        │   ├── redis-exporter (port 9121)        │
                        │   └── node-exporter (port 9100)         │
                        └──────────────┬──────────────────────────┘
                                       │ Private VPC (10.0.0.0/16)
                        ┌──────────────▼──────────────────────────┐
                        │           EC2 Instance 2                │
                        │   ├── PostgreSQL (port 5432)            │
                        │   ├── Prometheus (port 9090)            │
                        │   └── Grafana (port 3000)               │
                        └─────────────────────────────────────────┘
```

Two EC2 instances communicate over a private VPC network. Instance 1 runs the application layer. Instance 2 runs the data and observability layer. All inter-service communication uses private IPs — nothing crosses the public internet internally.

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Uvicorn |
| Queue | Redis, RQ |
| Database | PostgreSQL |
| HTTP client | httpx |
| Reverse proxy | Nginx with Let's Encrypt |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Secrets | AWS Parameter Store |
| Observability | Prometheus, Grafana, node-exporter, redis-exporter |
| Cloud | AWS EC2, VPC, Route 53, IAM |

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/events` | Create a webhook event |
| GET | `/events/{id}/deliveries` | Get delivery attempts for an event |
| GET | `/metrics` | Prometheus metrics scrape endpoint |

## Project Structure

```
webhook-delivery-system/
├── app/
│   ├── main.py          # FastAPI app, endpoints, startup
│   ├── worker.py        # RQ worker entrypoint
│   ├── jobs.py          # Webhook delivery logic
│   ├── models.py        # SQLAlchemy models
│   ├── database.py      # PostgreSQL connection layer
│   ├── schemas.py       # Pydantic request/response schemas
│   └── metrics.py       # Custom Prometheus metrics
├── tests/
│   └── test_main.py     # Pytest tests, mocked dependencies
├── scripts/
│   └── fetch-secrets.sh # Fetches secrets from AWS Parameter Store
├── nginx/
│   └── nginx.conf       # Nginx reverse proxy config
├── prometheus/
│   └── prometheus.yml   # Prometheus scrape config
├── grafana/
│   └── dashboards/      # Grafana dashboard definitions
├── Dockerfile
├── docker-compose.instance1.yml
├── docker-compose.instance2.yml
└── .github/
    └── workflows/
        └── pipeline.yml
```

## CI/CD Pipeline

Push to `main` triggers a four-job GitHub Actions pipeline:

```
test → build → deploy-staging → [manual approval] → deploy-production
```

- **test** — runs pytest with mocked infrastructure dependencies
- **build** — builds Docker image for `linux/amd64`, tags with git SHA, pushes to Docker Hub
- **deploy-staging** — SSHes into Instance 1, fetches fresh secrets from Parameter Store, pulls new image, restarts containers, runs health check against `staging.api.radianceits.com`
- **deploy-production** — same as staging, gated behind GitHub Environment manual approval, targets `api.radianceits.com`

Single Docker image serves both API and worker — different entrypoint commands, same build artifact.

## Secrets Management

Runtime secrets are stored in AWS Parameter Store as SecureString values under the `/webhook/production/` path hierarchy. EC2 instances are assigned an IAM role with `AmazonSSMReadOnlyAccess`. At deploy time, `scripts/fetch-secrets.sh` fetches all parameters and writes them to `.env` before containers start. No secrets are stored on disk permanently or committed to the repository.

GitHub Secrets are used only for CI/CD pipeline operations — Docker Hub credentials, SSH key, EC2 hostnames.

## Observability

Prometheus scrapes four targets every 15 seconds:

| Target | Port | What it measures |
|---|---|---|
| webhook-api | 9090 | HTTP request rates, latencies, status codes |
| node-exporter | 9100 | CPU, memory, disk, network for Instance 1 |
| redis-exporter | 9121 | Redis connected clients, memory, operations |
| prometheus | 9090 | Prometheus self-metrics |

Grafana dashboards display target health and API request totals. Two alert rules are active:

**Target Down** — fires when any Prometheus scrape target returns `up == 0`. Evaluated every minute. Notification sent to configured contact point immediately.

**High Error Rate** — fires when the ratio of 4xx/5xx responses to total requests exceeds 5% over a 5-minute window. PromQL: `(sum(rate(http_requests_total{status=~"4xx|5xx"}[5m])) or vector(0)) / sum(rate(http_requests_total[5m]))`.

## Key Design Decisions

**Single image, two roles** — API and worker use the same Docker image with different entrypoint commands. One build artifact, two responsibilities. Simplifies CI/CD and ensures version consistency between API and worker.

**Decoupled delivery** — the API returns a response immediately after saving the event and pushing to Redis. The worker delivers asynchronously. If the worker is down, events queue in Redis and are processed when the worker restarts. The API never waits for delivery.

**Private IP communication** — all internal traffic (API to PostgreSQL, Prometheus to API) uses stable private VPC IPs. Public IPs change on instance restart; private IPs do not.

**No Elastic IPs** — AWS charges for Elastic IPs regardless of attachment. Manual Route 53 update on instance restart was chosen as a cost-conscious alternative.

**Parameter Store over .env files** — manual `.env` files have no audit trail, no access control, and are lost if an instance is terminated. Parameter Store provides encryption at rest, IAM-controlled access, and centralised secret management.

## Running Locally

```bash
# Copy example env
cp .env.example .env
# Edit .env with local values

# Start all services
docker compose -f docker-compose.local.yml up -d

# Run tests
PYTHONPATH=. pytest tests/ -v
```

## Future Improvements

- **Queue depth alerting** — the worker has no Prometheus scrape target. Adding custom RQ metrics would enable alerting on queue depth, job failure rate, and worker health directly
- **Staging infrastructure separation** — staging and production currently share Instance 1, routed by Nginx Host header. True environment isolation requires separate instances or containers
- **Dead letter queue** — events that exhaust all retries are marked failed in PostgreSQL but not requeued or alerted on. A dead letter queue with alerting would improve reliability visibility
- **Database on managed service** — PostgreSQL runs on a self-managed EC2 instance. Moving to RDS would add automated backups, failover, and patch management
- **Kubernetes deployment** — current Docker Compose deployment does not support horizontal scaling. A Kubernetes manifests option would enable autoscaling based on queue depth
- **mTLS between services** — internal VPC communication is unencrypted. Adding mutual TLS between API, worker, and PostgreSQL would harden the security posture