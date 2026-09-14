#!/usr/bin/env bash
# =============================================================================
# status.sh — what is deployed, right now
# =============================================================================
#   deploy/scripts/status.sh
#   deploy/scripts/status.sh --history 20
#
# Read-only: it never changes anything, so it is safe to run at any point,
# including in the middle of a deploy. This is the first command to run when
# something looks wrong.
# =============================================================================

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

HISTORY_LINES=10
while [[ $# -gt 0 ]]; do
    case "$1" in
        --history) HISTORY_LINES="${2:-10}"; shift 2 ;;
        -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) log_error "unknown argument: $1"; exit 2 ;;
    esac
done

# status.sh is a diagnostic, so it must not litter logs/deploy with a file per
# invocation.
DEPLOY_LOG=/dev/null

hr() { printf '%s\n' "------------------------------------------------------------"; }

badge() {
    case "$1" in
        up)   printf '%sUP     %s' "$C_GRN" "$C_RST" ;;
        down) printf '%sDOWN   %s' "$C_DIM" "$C_RST" ;;
        bad)  printf '%sBROKEN %s' "$C_RED" "$C_RST" ;;
    esac
}

printf '\n%s SashaInfinity LMS — deployment status %s\n' "$C_BLU" "$C_RST"
hr

# -----------------------------------------------------------------------------
# Traffic
# -----------------------------------------------------------------------------
NGINX_COLOR="$(nginx_active_color)"
STATE_COLOR="$(active_color)"

printf 'Live colour (nginx) : %s%s%s\n' "$C_GRN" "$NGINX_COLOR" "$C_RST"
printf 'Recorded state      : %s\n' "$STATE_COLOR"
if [[ "$NGINX_COLOR" != "$STATE_COLOR" ]]; then
    printf '%s  ! nginx and state/active_color disagree — the next deploy will repair this%s\n' "$C_YLW" "$C_RST"
fi
printf 'Previous colour     : %s\n' "$(previous_color)"
printf 'Edge port           : %s\n' "$EDGE_HTTP_PORT"

if [[ -f "$MAINTENANCE_FLAG" ]]; then
    printf 'Maintenance mode    : %sON%s (since %s)\n' "$C_YLW" "$C_RST" "$(head -n1 "$MAINTENANCE_FLAG" 2>/dev/null)"
    printf '                      reason: %s\n' "$(grep -m1 '^reason=' "$MAINTENANCE_FLAG" 2>/dev/null | cut -d= -f2-)"
else
    printf 'Maintenance mode    : off\n'
fi

if [[ -d "$LOCK_DIR" ]]; then
    printf 'Deploy lock         : %sHELD%s by PID %s\n' "$C_YLW" "$C_RST" "$(cat "$LOCK_DIR/pid" 2>/dev/null || echo '?')"
fi

# -----------------------------------------------------------------------------
# Infrastructure
# -----------------------------------------------------------------------------
hr
printf 'Infrastructure\n'
for c in "$EDGE_CONTAINER" "$POSTGRES_CONTAINER" sasha-redis; do
    if container_running "$c"; then
        health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' "$c" 2>/dev/null)"
        printf '  %s %-18s health=%s\n' "$(badge up)" "$c" "$health"
    elif container_exists "$c"; then
        printf '  %s %-18s (exists, stopped)\n' "$(badge down)" "$c"
    else
        printf '  %s %-18s (missing)\n' "$(badge bad)" "$c"
    fi
done

if docker network inspect "$DOCKER_NETWORK" >/dev/null 2>&1; then
    printf '  %s %-18s\n' "$(badge up)" "network:$DOCKER_NETWORK"
else
    printf '  %s %-18s (missing)\n' "$(badge bad)" "network:$DOCKER_NETWORK"
fi

# -----------------------------------------------------------------------------
# Colours
# -----------------------------------------------------------------------------
for colour in blue green; do
    hr
    marker=""
    [[ "$colour" == "$NGINX_COLOR" ]] && marker=" ${C_GRN}<= LIVE${C_RST}"
    printf 'Colour: %s%s   release: %s\n' "$colour" "$marker" "$(state_get "${colour}.tag" '(none)')"

    for svc in "${SERVICES[@]}"; do
        c="$(container_name "$svc" "$colour")"
        if container_running "$c"; then
            health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' "$c" 2>/dev/null)"
            restarts="$(docker inspect -f '{{.RestartCount}}' "$c" 2>/dev/null)"
            image="$(docker inspect -f '{{.Config.Image}}' "$c" 2>/dev/null)"
            printf '  %s %-24s health=%-10s restarts=%-3s %s\n' \
                "$(badge up)" "$svc" "$health" "$restarts" "$image"
        elif container_exists "$c"; then
            printf '  %s %-24s (stopped — available for rollback)\n' "$(badge down)" "$svc"
        else
            printf '  %s %-24s (not created)\n' "$(badge down)" "$svc"
        fi
    done
done

# -----------------------------------------------------------------------------
# Live endpoint check through the edge
# -----------------------------------------------------------------------------
hr
printf 'Live endpoints (via edge on port %s)\n' "$EDGE_HTTP_PORT"

check_endpoint() {
    local path="$1" label="$2" body
    if body="$(http_get "http://127.0.0.1:${EDGE_HTTP_PORT}${path}" 8 2>/dev/null)"; then
        printf '  %sOK%s   %-18s %s\n' "$C_GRN" "$C_RST" "$label" "$(printf '%s' "$body" | head -c 160)"
    else
        printf '  %sFAIL%s %-18s no 2xx response\n' "$C_RED" "$C_RST" "$label"
    fi
}

check_endpoint /__edge/health  "edge"
check_endpoint /__edge/active  "active colour"
check_endpoint /health         "backend live"
check_endpoint /health/ready   "backend ready"
check_endpoint /health/version "release"

# -----------------------------------------------------------------------------
# History
# -----------------------------------------------------------------------------
if [[ -f "$STATE_DIR/history.log" ]]; then
    hr
    printf 'Last %s events\n' "$HISTORY_LINES"
    printf '  %-21s %-18s %-7s %s\n' "WHEN" "EVENT" "COLOUR" "RELEASE / DETAIL"
    tail -n "$HISTORY_LINES" "$STATE_DIR/history.log" | while IFS=$'\t' read -r ts event colour tag detail; do
        printf '  %-21s %-18s %-7s %s %s\n' "$ts" "$event" "$colour" "$tag" "$detail"
    done
fi

hr
printf 'Deploy logs: %s\n\n' "$LOG_DIR"
