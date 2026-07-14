#!/usr/bin/env bash
# Reset Postgres to a fresh state with the agentops user and seed data.
# Use when you see: Role "agentops" does not exist
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Stopping containers and removing orphan backend-db-1 if present..."
docker compose down --remove-orphans

echo "Removing postgres volume..."
docker volume rm backend_postgres_data 2>/dev/null || true

echo "Starting postgres..."
docker compose up -d postgres

echo "Waiting for postgres to initialize..."
for _ in $(seq 1 30); do
  if docker exec backend-postgres-1 psql -U agentops -d agentops -c "SELECT 1" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Verifying seed data..."
docker exec backend-postgres-1 psql -U agentops -d agentops -c "SELECT key_value FROM api_keys LIMIT 1;"

echo ""
echo "Postgres reset complete. Start ClickHouse if needed:"
echo "  docker compose up -d"
