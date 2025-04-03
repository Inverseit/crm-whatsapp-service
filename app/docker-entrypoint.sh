#!/bin/bash
set -e

# Wait for the database to be ready
echo "Waiting for database to be ready..."
for i in {1..30}; do
  pg_isready -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} && break
  sleep 1
  if [ $i -eq 30 ]; then
    echo "Database connection timed out"
    exit 1
  fi
done

echo "Database is ready!"

# Check if we can connect to the database
set +e
PGPASSWORD=${POSTGRES_PASSWORD} psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT 1" >/dev/null 2>&1
DB_CONNECT_RESULT=$?
set -e

if [ $DB_CONNECT_RESULT -ne 0 ]; then
  echo "Cannot connect to the database, creating database..."
  PGPASSWORD=${POSTGRES_PASSWORD} createdb -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} ${POSTGRES_DB}
  echo "Database created!"
fi

# Handle migrations
if [ "$INITIALIZE_DB" = "true" ]; then
  echo "INITIALIZE_DB is true, running full database initialization..."
  python scripts/reset_migration.py --drop-all
  alembic stamp head
  alembic revision --autogenerate -m "recreate_all"
  alembic upgrade head
  echo "Database initialization complete!"
else
  # Run migrations normally
  echo "Running database migrations..."
  alembic upgrade head
  echo "Migrations complete!"
fi

# Start the application
echo "Starting the application..."
exec "$@"
