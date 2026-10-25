#!/usr/bin/env bash
set -e

# ═══════════════════════════════════════════════════════════════════
# P2P Platform — Full Local Startup Script
# Ishga tushiradi: PostgreSQL, Redis, Backend API, Celery Worker,
#                  Celery Beat, Frontend Dev Server
# ═══════════════════════════════════════════════════════════════════

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV="$BACKEND_DIR/.venv"
PID_DIR="$ROOT_DIR/.pids"
LOG_DIR="$ROOT_DIR/.logs"

# Local environment

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$PID_DIR" "$LOG_DIR"

# ── Helpers ───────────────────────────────────────────────────────
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

cleanup() {
    echo ""
    warn "Barcha servislarni to'xtatish..."
    for pidfile in "$PID_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            info "PID $pid to'xtatildi ($(basename "$pidfile" .pid))"
        fi
        rm -f "$pidfile"
    done
    log "Barcha servislar to'xtatildi."
    exit 0
}

trap cleanup SIGINT SIGTERM

check_port() {
    if ss -tlnp 2>/dev/null | grep -q ":$1 "; then
        return 0
    fi
    return 1
}

wait_for_port() {
    local port=$1 name=$2 timeout=${3:-15}
    for i in $(seq 1 "$timeout"); do
        if check_port "$port"; then
            log "$name ishga tushdi (port $port)"
            return 0
        fi
        sleep 1
    done
    err "$name $timeout sekund ichida ishga tushmadi (port $port)"
}

# ── 1. Prerequisite tekshirish ────────────────────────────────────
echo -e "\n${BLUE}══════════════════════════════════════${NC}"
echo -e "${BLUE}   P2P Platform — Startup Script${NC}"
echo -e "${BLUE}══════════════════════════════════════${NC}\n"

info "Tizim tekshiruvi..."

command -v python3 >/dev/null || err "python3 topilmadi"
command -v node >/dev/null    || err "node topilmadi"
command -v npm >/dev/null     || err "npm topilmadi"

# ── 2. PostgreSQL ─────────────────────────────────────────────────
info "PostgreSQL tekshiruvi..."
if ! check_port 5432; then
    sudo systemctl start postgresql 2>/dev/null || true
    if ! check_port 5432; then
        warn "PostgreSQL (port 5432) ishlamayapti. (Local DB ni ishga tushirish talab etiladi)"
    else
        log "PostgreSQL ishga tushdi (port 5432)"
    fi
else
    log "PostgreSQL allaqachon ishlamoqda"
fi

# ── 3. Redis ──────────────────────────────────────────────────────
info "Redis tekshiruvi..."
if ! check_port 6379; then
    sudo systemctl start redis valkey 2>/dev/null || true
    if ! check_port 6379; then
        warn "Redis (port 6379) ishlamayapti. (Local Redis ni ishga tushirish talab etiladi)"
    else
        log "Redis ishga tushdi (port 6379)"
    fi
else
    log "Redis allaqachon ishlamoqda"
fi

# ── 4. Python venv ────────────────────────────────────────────────
info "Python virtual environment tekshiruvi..."
if [ ! -d "$VENV" ]; then
    info "Venv yaratilmoqda..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --upgrade pip -q
    "$VENV/bin/pip" install -r "$BACKEND_DIR/requirements.txt" -q
    "$VENV/bin/pip" install itsdangerous -q
    log "Dependencies o'rnatildi"
else
    log "Venv mavjud"
fi

# ── 5. Backend .env ───────────────────────────────────────────────
if [ ! -f "$BACKEND_DIR/.env" ]; then
    warn ".env fayli topilmadi, .env.example dan nusxa olinmoqda..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    log ".env yaratildi (kerak bo'lsa tahrirlang: $BACKEND_DIR/.env)"
fi

# ── 6. Frontend node_modules ─────────────────────────────────────
info "Frontend dependencies tekshiruvi..."
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    info "npm install..."
    (cd "$FRONTEND_DIR" && npm install --silent)
    log "Frontend dependencies o'rnatildi"
else
    log "node_modules mavjud"
fi

# ── 7. Alembic migratsiyalar ─────────────────────────────────────
info "Database migratsiyalar..."
(cd "$BACKEND_DIR" && "$VENV/bin/alembic" upgrade head 2>&1 | grep -v "^$")
log "Migratsiyalar bajarildi"

# ── 8. Backend API ────────────────────────────────────────────────
echo ""
info "Backend API ishga tushirilmoqda (port 18000)..."
(cd "$BACKEND_DIR" && "$VENV/bin/uvicorn" app.main:app --host 0.0.0.0 --port 18000 --reload \
    > "$LOG_DIR/api.log" 2>&1) &
echo $! > "$PID_DIR/api.pid"
wait_for_port 18000 "Backend API"

# ── 9. Celery Worker ─────────────────────────────────────────────
info "Celery Worker ishga tushirilmoqda..."
(cd "$BACKEND_DIR" && "$VENV/bin/celery" -A app.tasks.celery_app.celery_app worker --loglevel=info \
    > "$LOG_DIR/celery_worker.log" 2>&1) &
echo $! > "$PID_DIR/celery_worker.pid"
log "Celery Worker ishga tushdi"

# ── 10. Celery Beat ──────────────────────────────────────────────
info "Celery Beat ishga tushirilmoqda..."
(cd "$BACKEND_DIR" && "$VENV/bin/celery" -A app.tasks.celery_app.celery_app beat --loglevel=info \
    > "$LOG_DIR/celery_beat.log" 2>&1) &
echo $! > "$PID_DIR/celery_beat.pid"
log "Celery Beat ishga tushdi"

# ── 11. Frontend Dev Server ──────────────────────────────────────
info "Frontend dev server ishga tushirilmoqda (port 5173)..."
(cd "$FRONTEND_DIR" && npx vite --host 0.0.0.0 --port 5173 \
    > "$LOG_DIR/frontend.log" 2>&1) &
echo $! > "$PID_DIR/frontend.pid"
wait_for_port 5173 "Frontend"

# ── 12. Telegram Bot ──────────────────────────────────────────────
info "Telegram Bot ishga tushirilmoqda..."
(cd "$BACKEND_DIR" && "$VENV/bin/python" -m bot.main \
    > "$LOG_DIR/bot.log" 2>&1) &
echo $! > "$PID_DIR/bot.pid"
log "Telegram Bot ishga tushdi"

# ── Done ──────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   Barcha servislar muvaffaqiyatli ishga tushdi!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BLUE}Frontend:${NC}    http://localhost:5173"
echo -e "  ${BLUE}Backend API:${NC} http://localhost:18000"
echo -e "  ${BLUE}Swagger:${NC}     http://localhost:18000/docs"
echo -e "  ${BLUE}Admin:${NC}       http://localhost:18000/admin"
echo ""
echo -e "  ${YELLOW}Loglar:${NC}      $LOG_DIR/"
echo -e "  ${YELLOW}To'xtatish:${NC}  Ctrl+C"
echo ""

# Servislar ishlayotganini kuzatish
wait
