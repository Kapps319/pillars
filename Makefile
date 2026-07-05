.PHONY: up down logs seed test test-backend lint migrate dev-api dev-frontend dev-worker

# --- Docker (the happy path) ---
up:            ## Boot the full stack (frontend :3000, api :8000, db, redis, worker)
	cp -n .env.example .env || true
	docker compose up --build

down:          ## Stop and remove containers
	docker compose down

logs:          ## Tail all service logs
	docker compose logs -f

seed:          ## Re-run the idempotent demo seed inside the api container
	docker compose exec api python -m app.db.seed

migrate:       ## Apply migrations inside the api container
	docker compose exec api alembic upgrade head

# --- Local development (no Docker) ---
dev-api:       ## Run the API with auto-reload (needs local Postgres + .env)
	cd backend && uvicorn app.main:app --reload --port 8000

dev-worker:    ## Run the Celery worker locally
	cd backend && celery -A app.workers.celery_app worker --loglevel=INFO

dev-frontend:  ## Run the Next.js dev server
	cd frontend && npm run dev

# --- Quality ---
test: test-backend

test-backend:  ## Backend test suite (golden classifier tests included)
	cd backend && python -m pytest tests -q

lint:          ## Ruff over the backend
	cd backend && ruff check app tests
