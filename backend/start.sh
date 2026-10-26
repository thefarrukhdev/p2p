#!/bin/bash
set -e

export PORT="${PORT:-8000}"

# ── Start PostgreSQL (only if local) ──────────────────────────────────────────
if [[ -z "$DATABASE_URL" ]] || [[ "$DATABASE_URL" == *"localhost"* ]] || [[ "$DATABASE_URL" == *"127.0.0.1"* ]]; then
    echo "Starting local PostgreSQL..."
    su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data -l /var/lib/postgresql/logfile start" || true
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='peerlearn'\" | grep -q 1 || psql -c \"CREATE USER peerlearn WITH PASSWORD 'strongpassword';\"" || true
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='peer_learn'\" | grep -q 1 || psql -c \"CREATE DATABASE peer_learn OWNER peerlearn;\"" || true
else
    echo "External PostgreSQL configured, skipping local PostgreSQL."
fi

# ── Start Redis ──────────────────────────────────────────────────────────────
echo "Starting Redis..."
redis-server --daemonize yes

# ── Run Alembic migrations ───────────────────────────────────────────────────
echo "Running Alembic migrations..."
cd /app
alembic upgrade head || echo "Migration warning — check logs"

# ── Start all services via supervisord ───────────────────────────────────────
echo "Starting API + Bot + Celery..."
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
