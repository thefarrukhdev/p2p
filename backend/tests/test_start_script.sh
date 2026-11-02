#!/usr/bin/env bash
set -eo pipefail

START_SH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/start.sh"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

FAILED=0

run_test() {
    local num="$1"
    local desc="$2"
    local expected_code="$3"
    shift 3

    set +e
    "$@" > "$TEMP_DIR/out.log" 2> "$TEMP_DIR/err.log"
    local actual_code=$?
    set -e

    if [[ "$actual_code" -eq "$expected_code" ]]; then
        echo "PASS [Test $num]: $desc (exit code $actual_code)"
    else
        echo "FAIL [Test $num]: $desc"
        echo "  Expected code: $expected_code, Got: $actual_code"
        echo "  stdout:"
        cat "$TEMP_DIR/out.log"
        echo "  stderr:"
        cat "$TEMP_DIR/err.log"
        FAILED=$((FAILED + 1))
    fi
}

echo "=== Running start.sh 10-Scenario Test Suite ==="

# Scenario 1: no arguments -> exit 1
run_test 1 "No arguments provided" 1 \
    bash -c "unset SERVICE_TYPE; '$START_SH'"

# Scenario 2: empty SERVICE_TYPE -> exit 1
run_test 2 "Empty SERVICE_TYPE without arguments" 1 \
    bash -c "SERVICE_TYPE='' '$START_SH'"

# Scenario 3: unknown role with arguments -> exit 1
run_test 3 "Unknown role passed as argument" 1 \
    bash -c "'$START_SH' totally_invalid_role"

# Scenario 4: unknown SERVICE_TYPE without arguments -> exit 1
run_test 4 "Unknown SERVICE_TYPE without arguments" 1 \
    bash -c "SERVICE_TYPE='invalid_env_role' '$START_SH'"

# Scenario 5: all without opt-in -> exit 1
run_test 5 "Monolithic 'all' without ALLOW_MONOLITHIC_LOCAL" 1 \
    bash -c "unset ALLOW_MONOLITHIC_LOCAL; '$START_SH' all"

# Scenario 6: all with ALLOW_MONOLITHIC_LOCAL=1 locally -> allowed (mock supervisord)
mkdir -p "$TEMP_DIR/bin"
cat << 'EOF' > "$TEMP_DIR/bin/supervisord"
#!/bin/bash
echo "MOCK_SUPERVISORD_INVOKED"
exit 0
EOF
chmod +x "$TEMP_DIR/bin/supervisord"
run_test 6 "Monolithic 'all' with ALLOW_MONOLITHIC_LOCAL=1 locally" 0 \
    bash -c "PATH='$TEMP_DIR/bin:$PATH' ALLOW_MONOLITHIC_LOCAL=1 DATABASE_URL='postgresql://remote:5432/db' REDIS_URL='redis://remote:6379/0' '$START_SH' all"

# Scenario 7: all with RENDER=true -> exit 1
run_test 7 "Monolithic 'all' rejected when RENDER=true" 1 \
    bash -c "PATH='$TEMP_DIR/bin:$PATH' ALLOW_MONOLITHIC_LOCAL=1 RENDER='true' '$START_SH' all"

# Scenario 8: all with ENVIRONMENT=production -> exit 1
run_test 8 "Monolithic 'all' rejected when ENVIRONMENT=production" 1 \
    bash -c "PATH='$TEMP_DIR/bin:$PATH' ALLOW_MONOLITHIC_LOCAL=1 ENVIRONMENT='production' '$START_SH' all"

# Scenario 9: RUN_MIGRATIONS_ON_STARTUP=true + api -> migration not called
cat << 'EOF' > "$TEMP_DIR/bin/uvicorn"
#!/bin/bash
echo "MOCK_UVICORN_INVOKED"
exit 0
EOF
cat << 'EOF' > "$TEMP_DIR/bin/alembic"
#!/bin/bash
echo "MOCK_ALEMBIC_INVOKED"
exit 99
EOF
chmod +x "$TEMP_DIR/bin/uvicorn" "$TEMP_DIR/bin/alembic"

set +e
PATH="$TEMP_DIR/bin:$PATH" RUN_MIGRATIONS_ON_STARTUP="true" "$START_SH" api > "$TEMP_DIR/scen9.out" 2> "$TEMP_DIR/scen9.err"
SCEN9_CODE=$?
set -e
if [[ "$SCEN9_CODE" -eq 0 ]] && grep -q "MOCK_UVICORN_INVOKED" "$TEMP_DIR/scen9.out" && ! grep -q "MOCK_ALEMBIC_INVOKED" "$TEMP_DIR/scen9.out"; then
    echo "PASS [Test 9]: RUN_MIGRATIONS_ON_STARTUP=true ignored for ordinary 'api' startup (migration not called)"
else
    echo "FAIL [Test 9]: RUN_MIGRATIONS_ON_STARTUP=true erroneously triggered migration or failed"
    FAILED=$((FAILED + 1))
fi

# Scenario 10: migrate -> alembic executed exactly once
cat << 'EOF' > "$TEMP_DIR/bin/alembic_counter"
#!/bin/bash
COUNT_FILE="$1"
c=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
echo $((c + 1)) > "$COUNT_FILE"
echo "ALEMBIC_UPGRADE_HEAD_EXECUTED"
exit 0
EOF
chmod +x "$TEMP_DIR/bin/alembic_counter"

cat << EOF > "$TEMP_DIR/bin/alembic"
#!/bin/bash
exec "$TEMP_DIR/bin/alembic_counter" "$TEMP_DIR/alembic_count.txt" "\$@"
EOF
chmod +x "$TEMP_DIR/bin/alembic"

set +e
PATH="$TEMP_DIR/bin:$PATH" "$START_SH" migrate > "$TEMP_DIR/scen10.out" 2> "$TEMP_DIR/scen10.err"
SCEN10_CODE=$?
set -e
INVOCATION_COUNT=$(cat "$TEMP_DIR/alembic_count.txt" 2>/dev/null || echo 0)
if [[ "$SCEN10_CODE" -eq 0 ]] && [[ "$INVOCATION_COUNT" -eq 1 ]]; then
    echo "PASS [Test 10]: 'migrate' executes alembic upgrade head exactly once (exit code 0, count 1)"
else
    echo "FAIL [Test 10]: 'migrate' did not execute alembic exactly once (code: $SCEN10_CODE, count: $INVOCATION_COUNT)"
    FAILED=$((FAILED + 1))
fi

echo "============================================="
if [[ "$FAILED" -eq 0 ]]; then
    echo "ALL 10 START.SH SCENARIOS PASSED!"
    exit 0
else
    echo "$FAILED SCENARIOS FAILED!"
    exit 1
fi
