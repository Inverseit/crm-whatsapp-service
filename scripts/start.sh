#!/bin/bash
set -e

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting the application..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
