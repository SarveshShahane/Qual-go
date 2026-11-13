#!/usr/bin/env bash
set -e

echo "=== Starting QUALGO Backend Service ==="

# Optional database migration check
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Running database migrations with Alembic..."
    alembic upgrade head || {
        echo "Warning: Alembic migrations encountered an issue. Continuing startup..."
    }
fi

# Optional seed initial modules
if [ "${RUN_SEED:-false}" = "true" ]; then
    echo "Seeding initial quantum courseware modules..."
    python seed_modules.py || {
        echo "Warning: Seed script encountered an issue. Continuing startup..."
    }
fi

echo "Starting Uvicorn server on port ${PORT:-8000}..."
exec "$@"
