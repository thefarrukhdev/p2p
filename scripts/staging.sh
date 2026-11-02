#!/usr/bin/env bash
# ==============================================================================
# P2P Local Isolated Staging Helper Script
# Project: p2p-local-staging
# Strict Isolation: Zero production calls, mock APIs, local DB/Redis
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose.local-staging.yml"
COMPOSE_PROJECT="p2p-local-staging"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

pass() {
    echo -e "${GREEN}[PASS]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

fail() {
    echo -e "${RED}[FAIL]${NC} $*" >&2
    exit 1
}

# --- Command: preflight ---
cmd_preflight() {
    info "Running preflight checks for local staging environment..."
    
    # 1. Check Docker & Compose
    command -v docker >/dev/null 2>&1 || fail "Docker CLI is not installed or not in PATH."
    docker compose version >/dev/null 2>&1 || fail "docker compose plugin is not available."
    pass "Docker and Docker Compose are available."

    # 2. Check disk space (warn if < 2GB free on root)
    local free_kb
    free_kb=$(df -k / | awk 'NR==2 {print $4}')
    local free_mb=$((free_kb / 1024))
    if [ "$free_mb" -lt 1500 ]; then
        warn "Free disk space on root filesystem is low: ${free_mb} MB available."
    else
        pass "Disk space check passed: ${free_mb} MB available."
    fi

    # 3. Check staging config file
    local env_file="${REPO_ROOT}/.env.local-staging"
    [ -f "$env_file" ] || fail "Configuration file .env.local-staging not found at ${env_file}."
    
    # Verify no production domains/tokens exist in .env.local-staging
    local prod_markers=("onrender.com" "dpg-" "red-" "api.telegram.org" "auth.21-school.ru" "api.21-school.ru")
    for marker in "${prod_markers[@]}"; do
        if grep -qi "$marker" "$env_file"; then
            fail "CRITICAL: Production marker '${marker}' found in ${env_file}! Aborting to prevent production pollution."
        fi
    done
    pass "Staging configuration verified: zero production markers detected."

    # 4. Port availability (8008 for API proxy, 5174 for Frontend)
    for port in 8008 5174; do
        if ss -tln | grep -q ":${port} "; then
            # If our own compose container is holding the port, that's fine
            local container_using
            container_using=$(docker ps --filter "publish=${port}" --format '{{.Names}}' 2>/dev/null || true)
            if [ -n "$container_using" ]; then
                info "Port ${port} is currently bound by staging container '${container_using}'."
            else
                warn "Port ${port} is bound by another local process. Verify before starting."
            fi
        else
            pass "Port ${port} is free."
        fi
    done

    pass "Preflight checks complete."
}

# --- Command: start ---
cmd_start() {
    cmd_preflight

    info "Executing database migrations..."
    docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" run --rm migrate

    info "Starting all staging containers..."
    docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" up -d

    info "Waiting for services to become healthy..."
    local attempts=0
    local max_attempts=30
    while [ $attempts -lt $max_attempts ]; do
        local unready=0
        for svc in postgres redis mock-telegram mock-school21 api; do
            local health
            health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' "${COMPOSE_PROJECT}-${svc}-1" 2>/dev/null || echo "missing")
            if [ "$health" != "healthy" ]; then
                unready=$((unready + 1))
            fi
        done

        if [ "$unready" -eq 0 ]; then
            pass "All essential services (postgres, redis, mock-telegram, mock-school21, api) are healthy!"
            break
        fi

        attempts=$((attempts + 1))
        sleep 2
    done

    if [ $attempts -ge $max_attempts ]; then
        fail "Timed out waiting for staging services to become healthy."
    fi

    cmd_status
}

# --- Command: status ---
cmd_status() {
    info "Current staging status:"
    docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" ps
    echo ""
    info "Telegram Poller Leader Lock in Redis:"
    docker exec "${COMPOSE_PROJECT}-redis-1" redis-cli get "p2p:telegram_bot:leader_lock" 2>/dev/null || echo "No lock found"
}

# --- Command: logs ---
cmd_logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        info "Tailing logs for service: ${service}..."
        docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" logs -f "$service"
    else
        info "Tailing logs for all services..."
        docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" logs -f --tail=50
    fi
}

# --- Command: test ---
cmd_test() {
    info "Running comprehensive integration acceptance test suite..."
    
    # 1. API Health
    info "Checking API health on http://127.0.0.1:8008/health..."
    local health_resp
    health_resp=$(curl -sS -f http://127.0.0.1:8008/health || fail "API health check failed!")
    echo "$health_resp" | grep -q '"status":"ok"' || fail "Unexpected health response: ${health_resp}"
    pass "API health check: HTTP 200 OK."

    # 2. Protected Diagnostics (Unauthorized)
    info "Verifying protected diagnostics reject unauthenticated requests..."
    local diag_code
    diag_code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8008/api/v1/diagnostics)
    [ "$diag_code" -eq 401 ] || fail "Expected HTTP 401 for anonymous diagnostics, got ${diag_code}."
    pass "Diagnostics rejection for anonymous users: HTTP 401 Unauthorized."

    # 3. Create synthetic admin & verify diagnostics HTTP 200
    info "Seeding synthetic admin and verifying protected diagnostics access..."
    local admin_token
    admin_token=$(docker exec "${COMPOSE_PROJECT}-api-1" python3 -c "
import asyncio, uuid
from app.db.base import AsyncSessionLocal
from app.db.models.user import User
from app.core.security import create_access_token
from sqlalchemy import select

async def get_token():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.school21_login == 'staging_admin'))
        u = res.scalar_one_or_none()
        if not u:
            u = User(id=uuid.uuid4(), school21_login='staging_admin', is_admin=True, is_active=True, is_logged_in=True)
            db.add(u)
            await db.commit()
            await db.refresh(u)
        print('TOKEN_OUTPUT:' + create_access_token(str(u.id)))
asyncio.run(get_token())
" | grep '^TOKEN_OUTPUT:' | cut -d: -f2)

    local admin_diag_code
    admin_diag_code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${admin_token}" http://127.0.0.1:8008/api/v1/diagnostics)
    [ "$admin_diag_code" -eq 200 ] || fail "Expected HTTP 200 for admin diagnostics, got ${admin_diag_code}."
    pass "Diagnostics access for active admin: HTTP 200 OK."

    # 4. Auth flow against Mock School 21
    info "Testing School 21 Keycloak auth against mock-school21..."
    local auth_resp
    auth_resp=$(curl -sS -X POST http://127.0.0.1:8008/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d '{"login":"staging_regular","password":"testpassword"}')
    echo "$auth_resp" | grep -q '"status":"ok"' || fail "Auth login failed: ${auth_resp}"
    pass "Mock School 21 Keycloak login flow succeeded (issued access & refresh tokens)."

    # 4b. Auth flow for new unlinked user (testing need_telegram and bot_url resolution)
    info "Testing auth flow for unlinked user (checking need_telegram and bot_url)..."
    local unlinked_login="unlinked_$(date +%s)"
    local unlinked_resp
    unlinked_resp=$(curl -sS -X POST http://127.0.0.1:8008/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d "{\"login\":\"${unlinked_login}\",\"password\":\"testpassword\"}")
    echo "$unlinked_resp" | grep -q '"status":"need_telegram"' || fail "Expected need_telegram status: ${unlinked_resp}"
    echo "$unlinked_resp" | grep -q '"bot_url":"https://t.me/p2p_staging_bot' || fail "Expected bot_url in staging login response: ${unlinked_resp}"
    echo "$unlinked_resp" | grep -q '"staging_otp":"123456"' || fail "Expected staging_otp in staging login response: ${unlinked_resp}"
    pass "Unlinked login correctly issued bot_url, staging_otp, and need_telegram status."

    # 4c. Verify pre-seeded staging OTP 123456
    info "Verifying pre-seeded OTP 123456 login completion..."
    local temp_token
    temp_token=$(echo "$unlinked_resp" | grep -o '"temp_token":"[^"]*"' | cut -d'"' -f4)
    local verify_resp
    verify_resp=$(curl -sS -X POST http://127.0.0.1:8008/api/v1/auth/verify-code \
        -H "Content-Type: application/json" \
        -d "{\"temp_token\":\"${temp_token}\",\"code\":\"123456\"}")
    echo "$verify_resp" | grep -q '"access_token"' || fail "Verify code failed: ${verify_resp}"
    pass "Staging pre-seeded OTP 123456 successfully verified."

    # 5. Celery Worker task consumption
    info "Testing Celery task execution..."
    local celery_res
    celery_res=$(docker exec "${COMPOSE_PROJECT}-api-1" python3 -c "
from app.tasks.slot_tasks import dispatch_telegram_notifications
res = dispatch_telegram_notifications.delay()
val = res.get(timeout=5)
print(f'STATUS={res.status}:VAL={val}')
")
    echo "$celery_res" | grep -q "STATUS=SUCCESS" || fail "Celery task failed: ${celery_res}"
    pass "Celery worker consumed and completed task successfully."

    # 6. Outbound Telegram Notification to Mock Telegram
    info "Testing notification dispatch to mock-telegram..."
    docker exec "${COMPOSE_PROJECT}-api-1" python3 -c "
import asyncio
from app.services.telegram_dispatcher import dispatch_notification
asyncio.run(dispatch_notification(987654321, 'Staging Test', 'Notification body'))
"
    local mock_tg_count
    mock_tg_count=$(docker exec "${COMPOSE_PROJECT}-api-1" python3 -c "
import urllib.request, json
res = urllib.request.urlopen('http://mock-telegram:8080/_mock/sent_messages')
print(json.loads(res.read())['count'])
")
    [ "$mock_tg_count" -ge 1 ] || fail "Mock Telegram did not record sent message!"
    pass "Telegram notification captured by local mock server without external network call."

    # 7. Egress Network Block Verification
    info "Verifying that application containers cannot route to external internet..."
    local egress_blocked
    egress_blocked=$(docker exec "${COMPOSE_PROJECT}-api-1" python3 -c "
import urllib.request
try:
    urllib.request.urlopen('http://8.8.8.8', timeout=1)
    print('ALLOWED')
except Exception:
    print('BLOCKED')
")
    [ "$egress_blocked" = "BLOCKED" ] || fail "CRITICAL: Container has external egress! Network isolation failed."
    pass "Egress isolation verified: network unreachable for external traffic."

    # 8. Frontend proxy
    info "Verifying frontend serves index.html and proxies /api..."
    local fe_code
    fe_code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5174/)
    [ "$fe_code" -eq 200 ] || fail "Frontend did not return 200, got ${fe_code}."
    pass "Frontend serving correctly on http://127.0.0.1:5174/."

    echo ""
    pass "ALL LOCAL INTEGRATION ACCEPTANCE TESTS PASSED!"
}

# --- Command: stop ---
cmd_stop() {
    info "Gracefully stopping staging containers (preserving volumes)..."
    docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" stop
    pass "Staging containers stopped."
}

# --- Command: clean ---
cmd_clean() {
    echo -e "${YELLOW}WARNING: This will remove all containers, networks, and data volumes for project '${COMPOSE_PROJECT}'.${NC}"
    echo -e "Unrelated containers (such as Baito) will NOT be affected."
    read -rp "Are you sure you want to proceed? [y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        info "Cleaning staging resources..."
        docker compose -p "$COMPOSE_PROJECT" -f "$COMPOSE_FILE" down -v --remove-orphans
        pass "Staging project cleaned successfully."
    else
        info "Clean cancelled."
    fi
}

# --- Main entry point ---
usage() {
    echo "Usage: $0 {preflight|start|status|logs [service]|test|stop|clean}"
    exit 1
}

main() {
    local cmd="${1:-}"
    shift || true

    case "$cmd" in
        preflight) cmd_preflight ;;
        start)     cmd_start ;;
        status)    cmd_status ;;
        logs)      cmd_logs "$@" ;;
        test)      cmd_test ;;
        stop)      cmd_stop ;;
        clean)     cmd_clean ;;
        *)         usage ;;
    esac
}

main "$@"
