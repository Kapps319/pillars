# Deployment guide

The stack is five processes: `api` (FastAPI/uvicorn), `worker` (Celery),
`frontend` (Next.js standalone), PostgreSQL and Redis. Both containers are
already production-shaped (`backend/Dockerfile`, `frontend/Dockerfile`).

## Shared pre-flight (any cloud)

1. **Secrets** — set a strong `SECRET_KEY`; put provider keys
   (`ANTHROPIC_API_KEY`, `REDDIT_*`, `GOOGLE_*`) in the platform's secret
   manager, never in the image.
2. **Config** — `SEED_ON_STARTUP=false`, `CORS_ORIGINS=https://app.yourdomain.com`,
   `NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1` (build arg for the
   frontend image — the browser calls the API directly).
3. **Migrations** — the API entrypoint runs `alembic upgrade head` on boot; for
   multi-instance deploys run migrations as a one-off task instead and strip it
   from the entrypoint.

---

## AWS — ECS/Fargate + RDS + ElastiCache

1. **Registry** — create two ECR repos and push:
   ```bash
   aws ecr create-repository --repository-name leadfinder-api
   aws ecr create-repository --repository-name leadfinder-frontend
   docker build -t $ECR/leadfinder-api backend/
   docker build -t $ECR/leadfinder-frontend \
     --build-arg NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1 frontend/
   docker push $ECR/leadfinder-api && docker push $ECR/leadfinder-frontend
   ```
2. **Data stores**
   - RDS PostgreSQL 16 (e.g. `db.t4g.small` to start), private subnets.
     `DATABASE_URL=postgresql+psycopg://user:pass@<rds-endpoint>:5432/leadfinder`
   - ElastiCache Redis 7 (e.g. `cache.t4g.micro`).
     `REDIS_URL=redis://<elasticache-endpoint>:6379/0`
3. **ECS cluster** (Fargate) with three services in one task-definition family
   each:
   - `api` — image `leadfinder-api`, port 8000, env from SSM/Secrets Manager,
     health check `GET /api/v1/health`.
   - `worker` — same image, command
     `celery -A app.workers.celery_app worker --loglevel=INFO`, no ports.
   - `frontend` — image `leadfinder-frontend`, port 3000.
4. **Load balancing** — an ALB with two target groups:
   `api.yourdomain.com → api:8000`, `app.yourdomain.com → frontend:3000`;
   ACM certificates on the HTTPS listeners.
5. **Security groups** — ALB → api/frontend only; api/worker → RDS 5432 and
   ElastiCache 6379; nothing public on the data stores.
6. **One-off tasks** — run migrations/seed as an ECS run-task:
   `alembic upgrade head` / `python -m app.db.seed`.

## GCP — Cloud Run + Cloud SQL + Memorystore

1. **Registry**
   ```bash
   gcloud artifacts repositories create leadfinder --repository-format=docker --location=$REGION
   gcloud builds submit backend/  --tag $REGION-docker.pkg.dev/$PROJECT/leadfinder/api
   gcloud builds submit frontend/ --tag $REGION-docker.pkg.dev/$PROJECT/leadfinder/frontend
   ```
2. **Data stores**
   - Cloud SQL for PostgreSQL 16; add a private IP or use the Cloud SQL
     connector. `DATABASE_URL=postgresql+psycopg://user:pass@/leadfinder?host=/cloudsql/<conn-name>`
   - Memorystore for Redis; note the private IP →
     `REDIS_URL=redis://<memorystore-ip>:6379/0`
   - Both need a **Serverless VPC Access connector** so Cloud Run can reach them.
3. **Services**
   ```bash
   gcloud run deploy leadfinder-api \
     --image .../api --port 8000 --vpc-connector leadfinder-vpc \
     --add-cloudsql-instances <conn-name> \
     --set-secrets SECRET_KEY=leadfinder-secret:latest \
     --set-env-vars REDIS_URL=...,CORS_ORIGINS=https://app.yourdomain.com

   gcloud run deploy leadfinder-frontend --image .../frontend --port 3000
   ```
4. **Worker** — Cloud Run doesn't idle background pollers well. Two options:
   - Simplest: set `CELERY_ENABLED=false` on the API — jobs run in-process
     (fine for the request volumes of an MVP).
   - Proper: run the Celery worker on a small GCE VM or GKE Autopilot pod with
     the same image/command as AWS.
5. **Domains** — map custom domains in Cloud Run; certs are automatic.

## Smoke test after deploy

```bash
curl https://api.yourdomain.com/api/v1/health          # {"status":"ok",...}
# register, login, create + run a campaign via /docs, watch the job stats
```
