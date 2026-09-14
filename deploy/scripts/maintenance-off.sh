#!/usr/bin/env bash
# =============================================================================
# maintenance-off.sh — return users to the application
# =============================================================================
#   deploy/scripts/maintenance-off.sh
#
# Removes deploy/nginx/maintenance/ON. Since the edge tests for that file per
# request, traffic resumes immediately — no reload needed.
#
# Idempotent: running it when maintenance is already off is a no-op that still
# exits 0, so it is safe to call unconditionally at the end of a script or from a
# cleanup trap. That matters: the worst failure mode of maintenance mode is
# forgetting to turn it off, so calling this defensively should always be safe.
# =============================================================================

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [[ ! -f "$MAINTENANCE_FLAG" ]]; then
    log_info "maintenance mode is already off — nothing to do"
    exit 0
fi

log_step "Maintenance mode: OFF"
log_info "was enabled: $(head -n1 "$MAINTENANCE_FLAG" 2>/dev/null || echo unknown)"

rm -f "$MAINTENANCE_FLAG"

# Confirm real traffic is flowing again before declaring success.
if container_running "$EDGE_CONTAINER"; then
    ok=0
    for _ in 1 2 3 4 5; do
        if probe_in_container "$EDGE_CONTAINER" 'http://127.0.0.1/health' >/dev/null 2>&1; then
            ok=1; break
        fi
        sleep 1
    done

    if [[ "$ok" == "1" ]]; then
        log_info "verified: the edge is serving the application again (colour: $(nginx_active_color))"
    else
        log_warn "the maintenance flag is removed, but /health is not answering through the edge."
        log_warn "That points at the app tier, not at maintenance mode. Check:"
        log_warn "  deploy/scripts/status.sh"
    fi
else
    log_warn "edge container '$EDGE_CONTAINER' is not running — start it with:"
    log_warn "  docker compose -f deploy/docker-compose.edge.yml up -d"
fi

record_history "maintenance-off" "$(active_color)" "-" ""
