#!/usr/bin/env bash
# =============================================================================
# maintenance-on.sh — show the maintenance page to everyone
# =============================================================================
#   deploy/scripts/maintenance-on.sh
#   deploy/scripts/maintenance-on.sh --reason "coupon table migration"
#
# Normal deploys must NEVER call this: blue-green means users keep being served
# throughout, and a maintenance page during a routine release would be a
# regression, not a feature. This exists for the cases blue-green genuinely
# cannot cover — a destructive migration where old and new code cannot both run
# against the same schema (dropping or renaming a column, splitting a table).
#
# HOW IT WORKS
# It creates deploy/nginx/maintenance/ON. The edge config tests for that file's
# existence on every request (`if (-f /etc/nginx/maintenance/ON)`), so the effect
# is immediate: no reload, no config rewrite, nothing to get wrong under pressure.
# The directory is bind-mounted, so a file created here is visible inside the
# container at once.
#
# Users get HTTP 503 plus a Retry-After, which is the correct signal for crawlers
# and CDNs — they will come back rather than caching the page or de-indexing the
# site. /health and /__edge/* stay reachable so monitoring does not go dark and
# the deploy scripts keep working.
#
# Idempotent: running it twice is fine and refreshes the recorded reason.
# =============================================================================

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

REASON="${1:-}"
if [[ "$REASON" == "--reason" ]]; then
    REASON="${2:-unspecified}"
elif [[ -z "$REASON" ]]; then
    REASON="unspecified"
fi

if [[ -f "$MAINTENANCE_FLAG" ]]; then
    log_warn "maintenance mode is ALREADY on (since $(head -n1 "$MAINTENANCE_FLAG" 2>/dev/null || echo 'unknown'))"
fi

mkdir -p "$(dirname "$MAINTENANCE_FLAG")"

# The flag's contents are purely for humans reading it later; nginx only tests
# that the file exists.
cat >"$MAINTENANCE_FLAG" <<EOF
$(date -u +'%Y-%m-%dT%H:%M:%SZ')
enabled_by=${USER:-unknown}@$(hostname 2>/dev/null || echo unknown)
reason=$REASON
EOF

log_step "Maintenance mode: ON"
log_info "reason: $REASON"

# Prove it rather than assume it. A wrong answer here means users are seeing the
# app when you believe they are not, which is the dangerous direction for a
# destructive migration.
if container_running "$EDGE_CONTAINER"; then
    code="$(docker exec "$EDGE_CONTAINER" sh -c \
        "wget -q -S -O /dev/null http://127.0.0.1/ 2>&1 | awk '/HTTP\\//{print \$2; exit}'" 2>/dev/null || echo "")"
    if [[ "$code" == "503" ]]; then
        log_info "verified: the edge is returning 503 with the maintenance page"
    else
        log_warn "expected HTTP 503 from the edge but got '${code:-no response}'"
        log_warn "check that deploy/nginx/maintenance is mounted at /etc/nginx/maintenance"
    fi

    if probe_in_container "$EDGE_CONTAINER" 'http://127.0.0.1/__edge/health' >/dev/null 2>&1; then
        log_info "verified: probes (/health, /__edge/*) are still reachable"
    else
        log_warn "edge probe endpoint is not answering — investigate before proceeding"
    fi
else
    log_warn "edge container '$EDGE_CONTAINER' is not running; the flag is set and will apply once it starts"
fi

record_history "maintenance-on" "$(active_color)" "-" "$REASON"

log_info "disable with: deploy/scripts/maintenance-off.sh"
