#!/bin/bash
set -e

export PORT="${PORT:-8000}"
TARGET="${1:-${SERVICE_TYPE}}"

# ── Explicit Role Guard ───────────────────────────────────────────────────────
# Render services and production containers must explicitly specify a role.
# Monolithic 'all' mode cannot be selected by default or omission.
if [[ -z "$TARGET" ]]; then
    echo "FATAL: No process role specified." >&2
    echo "Render services must set an explicit Start Command or SERVICE_TYPE." >&2
    echo "Available roles: api | bot | worker | beat | migrate" >&2
    echo "Examples: /start.sh api, /start.sh bot, /start.sh migrate" >&2
    exit 1
fi

# ── Validate Allowed Roles ────────────────────────────────────────────────────
case "$TARGET" in
    api|web|bot|worker|beat|migrate|all)
        ;;
    *)
        echo "FATAL: Unknown service role '$TARGET'. Allowed roles: api | bot | worker | beat | migrate" >&2
        exit 1
        ;;
esac

# ── Monolithic 'all' Mode Guard (Strictly Local with Explicit Opt-in) ─────────
if [[ "$TARGET" == "all" ]]; then
    if [[ -n "$RENDER" ]] || [[ "$ENVIRONMENT" == "production" ]]; then
        echo "FATAL: Monolithic 'all' mode is strictly forbidden in Render/production environments." >&2
        exit 1
    fi
    if [[ "${ALLOW_MONOLITHIC_LOCAL:-0}" != "1" ]]; then
        echo "FATAL: Monolithic 'all' mode requires explicit ALLOW_MONOLITHIC_LOCAL=1 opt-in." >&2
        exit 1
    fi

    # Start local PostgreSQL only if DATABASE_URL points to localhost or 127.0.0.1
    if [[ -z "$DATABASE_URL" ]] || [[ "$DATABASE_URL" == *"localhost"* ]] || [[ "$DATABASE_URL" == *"127.0.0.1"* ]]; then
        echo "Starting local PostgreSQL daemon..."
        su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data -l /var/lib/postgresql/logfile start" || true
        su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='peerlearn'\" | grep -q 1 || psql -c \"CREATE USER peerlearn WITH PASSWORD 'strongpassword';\"" || true
        su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='peer_learn'\" | grep -q 1 || psql -c \"CREATE DATABASE peer_learn OWNER peerlearn;\"" || true
    else
        echo "External PostgreSQL configured, skipping local PostgreSQL."
    fi

    # Start local Redis only if REDIS_URL points to localhost or 127.0.0.1
    if [[ -z "$REDIS_URL" ]] || [[ "$REDIS_URL" == *"localhost"* ]] || [[ "$REDIS_URL" == *"127.0.0.1"* ]]; then
        echo "Starting local Redis daemon..."
        redis-server --daemonize yes || true
    else
        echo "External Redis configured, skipping local Redis daemon."
    fi
fi

# ── Controlled Database Migrations ───────────────────────────────────────────
# Ordinary service startups (api, bot, worker, beat) NEVER execute database migrations.
# RUN_MIGRATIONS_ON_STARTUP is intentionally rejected as a bypass mechanism.
if [[ "$TARGET" == "migrate" ]]; then
    echo "Running controlled Alembic database migration..."
    if [[ -d "/app" ]]; then
        cd /app
    fi
    # Exec alembic directly so any migration error code is strictly propagated to Render
    exec alembic upgrade head
fi

# ── Process Dispatcher (exec forwards SIGTERM directly to child for graceful shutdown)
if [[ -d "/app" ]]; then
    cd /app
fi

case "$TARGET" in
    api|web)
        echo "Starting FastAPI API server on port $PORT..."
        exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
        ;;
    bot)
        echo "Starting Telegram Bot worker with fail-closed distributed lock..."
        exec python -m bot.main
        ;;
    worker)
        echo "Starting dedicated Celery worker..."
        exec celery -A app.tasks.celery_app.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}"
        ;;
    beat)
        echo "Starting dedicated Celery Beat scheduler..."
        exec celery -A app.tasks.celery_app.celery_app beat --loglevel=info
        ;;
    all)
        echo "Starting full supervisor stack (local monolithic mode)..."
        exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
        ;;
    *)
        echo "FATAL: Unhandled service role '$TARGET'." >&2
        exit 1
        ;;
esac
