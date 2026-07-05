#!/bin/sh
set -e

# Wait for Postgres, run migrations, then hand off to the container command.
echo "Waiting for database..."
python - <<'PY'
import sys, time
from sqlalchemy import create_engine, text
from app.core.config import get_settings

engine = create_engine(get_settings().database_url)
for attempt in range(30):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        sys.exit(0)
    except Exception:
        time.sleep(1)
print("Database not reachable after 30s", file=sys.stderr)
sys.exit(1)
PY

echo "Running migrations..."
alembic upgrade head

# Seeding also runs on app startup when SEED_ON_STARTUP=true; running it here
# too keeps the worker container consistent and is idempotent either way.
if [ "$SEED_ON_STARTUP" = "true" ]; then
  echo "Seeding demo data..."
  python -m app.db.seed || echo "Seeding failed (continuing)"
fi

exec "$@"
