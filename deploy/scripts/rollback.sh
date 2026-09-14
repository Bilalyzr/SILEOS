#!/usr/bin/env bash
# =============================================================================
# rollback.sh — put the previous release back in front of users
# =============================================================================
#   deploy/scripts/rollback.sh                      # back to the previous colour
#   deploy/scripts/rollback.sh --to blue            # back to a specific colour
#   deploy/scripts/rollback.sh --tag v1.4.1         # rebuild a slot from a tag
#
# Called automatically by deploy.sh when a deploy fails after the traffic switch,
# and manually when a release turns out to be bad after the fact.
#
# THE FAST PATH
# Because deploy.sh stops the old colour rather than removing it (KEEP_PREVIOUS),
# the previous release is normally sitting there ready to go. Rollback is then:
# start the containers, health-gate them, reload nginx. Seconds, no image pull,
# no build.
#
# THE SLOW PATH
# If the previous colour was removed (--stop-previous) or you are rolling back to
# an older tag, the slot is recreated from the recorded image tag first. That
# needs the image to still exist locally or in the registry — which is why
# cleanup.sh keeps IMAGE_RETENTION releases instead of pruning aggressively.
#
# Exit codes: 0 rolled back · 1 failure · 2 usage error
# =============================================================================

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

SCRIPT_DIR="$LIB_DIR"
START_TS=$SECONDS

usage() {
    cat <<'EOF'
Usage: rollback.sh [options]

  --to <blue|green>   Colour to roll back to (default: state/previous_color)
  --tag <tag>         Release tag to restore into that colour. Implies a
                      recreate even if containers are already present.
  --reason <text>     Recorded in state/history.log for the audit trail
  --force             Switch even if the health gate fails. Last resort: use
                      when the current colour is serving errors and a degraded
                      previous release is still better than nothing.
  -h, --help          This help
EOF
}

TO_COLOR=""
TO_TAG=""
REASON="manual rollback"
FORCE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --to)     TO_COLOR="${2:-}"; shift 2 ;;
        --tag)    TO_TAG="${2:-}";   shift 2 ;;
        --reason) REASON="${2:-}";   shift 2 ;;
        --force)  FORCE=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) log_error "unknown argument: $1"; usage; exit 2 ;;
    esac
done

# -----------------------------------------------------------------------------
# Work out the destination.
# -----------------------------------------------------------------------------
LIVE="$(nginx_active_color)"
validate_color "$LIVE"

if [[ -z "$TO_COLOR" ]]; then
    TO_COLOR="$(previous_color)"
    if [[ -z "$TO_COLOR" ]]; then
        # No recorded history (first ever deploy, or state was wiped). The other
        # slot is the only candidate.
        TO_COLOR="$(other_color "$LIVE")"
        log_warn "no previous colour recorded; assuming '$TO_COLOR'"
    fi
fi
validate_color "$TO_COLOR"

if [[ "$TO_COLOR" == "$LIVE" ]]; then
    die "'$TO_COLOR' is already the live colour — nothing to roll back to. Pass --to explicitly if you meant a different slot."
fi

if [[ -z "$TO_TAG" ]]; then
    TO_TAG="$(state_get "${TO_COLOR}.tag" "")"
fi

log_step "Rollback: $LIVE -> $TO_COLOR (release ${TO_TAG:-unknown})"
log_info "reason: $REASON"

# deploy.sh calls this from inside its own EXIT trap while holding the lock, so
# taking it again would deadlock. Only lock when running standalone.
if [[ "${LOCK_HELD:-0}" != "1" && ! -d "$LOCK_DIR" ]]; then
    acquire_lock
fi

# -----------------------------------------------------------------------------
# Make sure the destination slot is running.
# -----------------------------------------------------------------------------
if color_is_up "$TO_COLOR" && [[ -z "${TO_TAG:-}" || "$(state_get "${TO_COLOR}.tag" "")" == "$TO_TAG" ]]; then
    log_info "'$TO_COLOR' containers are already running — fast path"
else
    if [[ -z "$TO_TAG" ]]; then
        die "'$TO_COLOR' is not running and no release tag is recorded for it. Re-deploy explicitly: deploy.sh --tag <tag> --color $TO_COLOR"
    fi

    log_step "Bringing up '$TO_COLOR' at release $TO_TAG"

    # Verify the images exist before touching the slot, so a missing image is a
    # clear error rather than a half-started stack.
    local_missing=()
    for svc in "${SERVICES[@]}"; do
        ref="$(image_ref "$svc" "$TO_TAG")"
        if ! docker image inspect "$ref" >/dev/null 2>&1; then
            log_info "image not present locally, attempting pull: $ref"
            if ! docker pull "$ref" >>"$DEPLOY_LOG" 2>&1; then
                local_missing+=("$ref")
            fi
        fi
    done

    if [[ ${#local_missing[@]} -gt 0 ]]; then
        log_error "cannot roll back: these images are neither local nor pullable:"
        for ref in "${local_missing[@]}"; do log_error "  $ref"; done
        die "rebuild from source instead: deploy.sh --tag $TO_TAG --color $TO_COLOR"
    fi

    RELEASE_TAG="$TO_TAG" dc_app "$TO_COLOR" up -d --remove-orphans >>"$DEPLOY_LOG" 2>&1 \
        || die "failed to start '$TO_COLOR' at release $TO_TAG (see $DEPLOY_LOG)"
    state_set "${TO_COLOR}.tag" "$TO_TAG"
fi

# -----------------------------------------------------------------------------
# Health-gate the destination. A rollback to something that is also broken just
# extends the outage, so the gate applies here too — with a shorter budget,
# because during an incident waiting three minutes is its own cost.
# -----------------------------------------------------------------------------
log_step "Health gate on '$TO_COLOR'"

if DEPLOY_LOG="$DEPLOY_LOG" "$SCRIPT_DIR/health-check.sh" \
        --color "$TO_COLOR" \
        --timeout "${ROLLBACK_HEALTH_TIMEOUT:-90}" \
        --interval 3 \
        --retries 2; then
    GATE_PASSED=1
else
    GATE_PASSED=0
    if [[ "$FORCE" != "1" ]]; then
        log_error "'$TO_COLOR' failed its health gate — NOT switching traffic to it"
        log_error "'$LIVE' remains live. Investigate, then re-run with --force if a degraded"
        log_error "previous release is still preferable to the current one."
        record_history "rollback-aborted" "$TO_COLOR" "${TO_TAG:-unknown}" "$REASON"
        release_lock
        exit 1
    fi
    log_warn "--force given: switching to '$TO_COLOR' despite a failed health gate"
fi

# -----------------------------------------------------------------------------
# Switch. --force is passed through so a partially-healthy slot can still take
# traffic during an incident.
# -----------------------------------------------------------------------------
log_step "Switching traffic back to '$TO_COLOR'"

switch_args=("$TO_COLOR")
[[ "$GATE_PASSED" != "1" ]] && switch_args+=(--force)

if ! DEPLOY_LOG="$DEPLOY_LOG" "$SCRIPT_DIR/switch.sh" "${switch_args[@]}"; then
    log_error "the traffic switch itself failed; '$LIVE' is still live"
    record_history "rollback-failed" "$TO_COLOR" "${TO_TAG:-unknown}" "$REASON"
    release_lock
    exit 1
fi

# -----------------------------------------------------------------------------
# Leave the bad colour stopped but present. Its containers and logs are the
# evidence for why the release failed — `docker logs sasha-backend-<colour>`
# still works on a stopped container, and would not on a removed one.
# -----------------------------------------------------------------------------
log_step "Quarantining '$LIVE'"
log_info "stopping '$LIVE' but keeping the containers so their logs survive"
dc_app "$LIVE" stop >>"$DEPLOY_LOG" 2>&1 || log_warn "could not stop '$LIVE' cleanly"

{
    printf '\n===== post-rollback logs from the failed colour (%s) =====\n' "$LIVE"
    for svc in "${SERVICES[@]}"; do
        c="$(container_name "$svc" "$LIVE")"
        if container_exists "$c"; then
            printf '\n----- %s -----\n' "$c"
            docker logs --tail 200 "$c" 2>&1 || true
        fi
    done
} >>"$DEPLOY_LOG"

elapsed=$(( SECONDS - START_TS ))
record_history "rollback" "$TO_COLOR" "${TO_TAG:-unknown}" "from=$LIVE reason=$REASON duration=${elapsed}s"

log_step "Rollback complete in $(human_duration "$elapsed")"
log_info "live colour: $TO_COLOR (release ${TO_TAG:-unknown})"
log_info "failed colour '$LIVE' is stopped; inspect it with:"
log_info "  docker logs --tail 200 $(container_name backend "$LIVE")"
log_info "full log: $DEPLOY_LOG"

release_lock
