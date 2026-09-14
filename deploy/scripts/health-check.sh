#!/usr/bin/env bash
# =============================================================================
# health-check.sh — decide whether a deployment slot may receive live traffic
# =============================================================================
# This is the gate the whole zero-downtime property rests on: traffic is only
# ever switched after this script exits 0.
#
# Two modes:
#
#   --color blue          Probe a colour's containers from the inside. Used
#                         BEFORE the switch, while the colour has no traffic and
#                         no published ports.
#
#   --url http://host/... Probe a URL from this host. Used AFTER the switch to
#                         confirm the edge really is serving the new colour.
#
# Design notes:
#
#  * The backend is gated on /health/ready, not /health. /health only proves the
#    process is answering HTTP; /health/ready proves it can reach Postgres. A
#    container that boots fine but cannot see the database would otherwise sail
#    through the gate and take the site down on switch.
#
#  * HEALTH_RETRIES consecutive passes are required, not one. A single success
#    can come from a worker that is about to die (a boot that succeeded before
#    lazily opening its DB pool, an OOM about to land). Requiring N in a row
#    with a gap between them filters that out cheaply.
#
#  * The container is re-checked for liveness on every attempt, so a crash-loop
#    fails fast instead of burning the whole timeout.
#
# Exit codes: 0 healthy · 1 unhealthy or timed out · 2 usage error
# =============================================================================

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() {
    cat <<'EOF'
Usage:
  health-check.sh --color <blue|green> [options]
  health-check.sh --url <url> [options]

Options:
  --color <blue|green>   Probe a colour's containers from inside them.
  --url <url>            Probe an HTTP endpoint from this host.
  --timeout <seconds>    Total time budget       (default: $HEALTH_TIMEOUT, 180)
  --interval <seconds>   Delay between attempts  (default: $HEALTH_INTERVAL, 5)
  --retries <n>          Consecutive passes required (default: $HEALTH_RETRIES, 3)
  --expect-tag <tag>     Also require /health/version to report this release
  --quiet                Only log failures
  -h, --help             Show this help

Exit codes: 0 healthy | 1 unhealthy/timeout | 2 usage error
EOF
}

MODE=""
TARGET_COLOR=""
TARGET_URL=""
EXPECT_TAG=""
QUIET=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --color)      MODE="color"; TARGET_COLOR="${2:-}"; shift 2 ;;
        --url)        MODE="url";   TARGET_URL="${2:-}";   shift 2 ;;
        --timeout)    HEALTH_TIMEOUT="${2:-}";  shift 2 ;;
        --interval)   HEALTH_INTERVAL="${2:-}"; shift 2 ;;
        --retries)    HEALTH_RETRIES="${2:-}";  shift 2 ;;
        --expect-tag) EXPECT_TAG="${2:-}";      shift 2 ;;
        --quiet)      QUIET=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)            log_error "unknown argument: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$MODE" ]] || { log_error "one of --color or --url is required"; usage; exit 2; }

say() { [[ "$QUIET" == "1" ]] || log_info "$@"; }

# -----------------------------------------------------------------------------
# A single full pass over one colour. Returns 0 only if every component answers.
# -----------------------------------------------------------------------------
check_color_once() {
    local colour="$1" service container body

    for service in "${SERVICES[@]}"; do
        container="$(container_name "$service" "$colour")"

        if ! container_exists "$container"; then
            FAIL_REASON="container $container does not exist"
            return 1
        fi

        if ! container_running "$container"; then
            local status
            status="$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo unknown)"
            FAIL_REASON="container $container is not running (status: $status)"
            return 1
        fi

        # A container that keeps restarting can be "running" for the instant we
        # look at it. Catch it via the restart counter instead.
        local restarts
        restarts="$(docker inspect -f '{{.RestartCount}}' "$container" 2>/dev/null || echo 0)"
        if (( restarts > 3 )); then
            FAIL_REASON="container $container has restarted $restarts times (crash loop)"
            return 1
        fi
    done

    # --- backend readiness: the one check that gates on Postgres --------------
    # Standby workers also report health, so both blue/green colours can pass
    # without both becoming scheduler leaders.
    if ! docker exec "sasha-runtime-${colour}" python -m app.workers.runtime --health >/dev/null 2>&1; then
        FAIL_REASON="maintenance worker is missing, stale or unavailable"
        return 1
    fi

    container="$(container_name backend "$colour")"
    if ! body="$(probe_in_container "$container" "http://127.0.0.1:8000/health/ready")"; then
        FAIL_REASON="backend readiness probe failed (non-2xx or no response)"
        return 1
    fi
    if [[ "$body" != *'"ready": true'* && "$body" != *'"ready":true'* ]]; then
        FAIL_REASON="backend readiness returned 2xx but not ready: $body"
        return 1
    fi
    if [[ "$body" == *'"degraded"'* ]]; then
        log_warn "backend reports degraded subsystems: $body"
    fi

    # --- release identity ----------------------------------------------------
    if [[ -n "$EXPECT_TAG" ]]; then
        if ! body="$(probe_in_container "$container" "http://127.0.0.1:8000/health/version")"; then
            FAIL_REASON="version probe failed"
            return 1
        fi
        if [[ "$body" != *"$EXPECT_TAG"* ]]; then
            FAIL_REASON="expected release '$EXPECT_TAG' but backend reports: $body"
            return 1
        fi
    fi

    # --- frontend ------------------------------------------------------------
    container="$(container_name frontend "$colour")"
    if ! probe_in_container "$container" "http://127.0.0.1:3000/" >/dev/null; then
        FAIL_REASON="frontend did not serve / with 2xx"
        return 1
    fi

    # --- streaming service ---------------------------------------------------
    container="$(container_name streaming "$colour")"
    if ! body="$(probe_in_container "$container" "http://127.0.0.1:8001/health")"; then
        FAIL_REASON="streaming service health probe failed"
        return 1
    fi

    return 0
}

check_url_once() {
    local url="$1" body
    if ! body="$(http_get "$url" 10 2>/dev/null)"; then
        FAIL_REASON="no 2xx response from $url"
        return 1
    fi
    if [[ -n "$EXPECT_TAG" && "$body" != *"$EXPECT_TAG"* ]]; then
        FAIL_REASON="expected release '$EXPECT_TAG' in response from $url, got: $body"
        return 1
    fi
    return 0
}

# -----------------------------------------------------------------------------
# Retry loop: poll until HEALTH_RETRIES consecutive passes, or the budget runs
# out. A failure resets the streak — three passes separated by a failure is not
# a stable service.
# -----------------------------------------------------------------------------
main() {
    local deadline=$(( SECONDS + HEALTH_TIMEOUT ))
    local streak=0 attempt=0
    FAIL_REASON="not attempted"

    local label
    if [[ "$MODE" == "color" ]]; then
        validate_color "$TARGET_COLOR"
        label="colour '$TARGET_COLOR'"
    else
        label="$TARGET_URL"
    fi

    say "health check on $label (timeout ${HEALTH_TIMEOUT}s, need ${HEALTH_RETRIES} consecutive passes)"

    while (( SECONDS < deadline )); do
        attempt=$(( attempt + 1 ))

        if { [[ "$MODE" == "color" ]] && check_color_once "$TARGET_COLOR"; } \
        || { [[ "$MODE" == "url"   ]] && check_url_once   "$TARGET_URL";   }; then
            streak=$(( streak + 1 ))
            say "attempt $attempt: healthy ($streak/$HEALTH_RETRIES)"
            if (( streak >= HEALTH_RETRIES )); then
                log_info "health check PASSED for $label after ${attempt} attempt(s)"
                return 0
            fi
        else
            if (( streak > 0 )); then
                log_warn "attempt $attempt: FAILED after $streak consecutive pass(es) — resetting streak"
            else
                say "attempt $attempt: not ready yet — $FAIL_REASON"
            fi
            streak=0
        fi

        sleep "$HEALTH_INTERVAL"
    done

    log_error "health check FAILED for $label after ${HEALTH_TIMEOUT}s: $FAIL_REASON"

    # Container logs are the first thing anyone asks for after a failed gate, so
    # capture them into the deploy log while the container still exists.
    if [[ "$MODE" == "color" ]]; then
        local service container
        for service in "${SERVICES[@]}"; do
            container="$(container_name "$service" "$TARGET_COLOR")"
            if container_exists "$container"; then
                {
                    printf '\n----- last 60 log lines: %s -----\n' "$container"
                    docker logs --tail 60 "$container" 2>&1 || true
                } >>"$DEPLOY_LOG"
            fi
        done
        log_error "container logs captured to $DEPLOY_LOG"
    fi

    return 1
}

main
