#!/usr/bin/env bash
# =============================================================================
# switch.sh — point the edge at a colour, without dropping a connection
# =============================================================================
#   deploy/scripts/switch.sh green
#   deploy/scripts/switch.sh blue --force      # skip the "is it running" check
#
# The switch is three steps: rewrite deploy/nginx/active/active.conf, validate it
# with `nginx -t`, then `nginx -s reload`.
#
# Why reload is safe: on reload nginx starts a new generation of worker processes
# with the new config and tells the old ones to shut down gracefully. The old
# workers stop accepting new connections but finish the requests they are already
# serving — including in-flight video range requests and slow uploads. No socket
# is closed, and the listening socket is never released, so nothing is refused.
# A `restart` would do none of that, which is why this script never restarts the
# edge.
#
# Why active.conf is written to a temp file and renamed: rename is atomic, so
# nginx can never read a half-written config. The directory (not the file) is
# what is bind-mounted into the container, precisely so the container sees the
# replacement — a file-level bind mount is bound to an inode and would keep
# showing the old contents forever after a rename.
#
# Exit codes: 0 switched (or already active) · 1 failure · 2 usage error
# =============================================================================

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() {
    cat <<'EOF'
Usage: switch.sh <blue|green> [--force] [--no-verify]

  --force       Switch even if the target colour's containers are not all up.
                Only for recovery; the normal path must never need it.
  --no-verify   Skip the post-reload read-back check.
EOF
}

TARGET=""
FORCE=0
VERIFY=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        blue|green) TARGET="$1"; shift ;;
        --force)    FORCE=1; shift ;;
        --no-verify) VERIFY=0; shift ;;
        -h|--help)  usage; exit 0 ;;
        *)          log_error "unknown argument: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$TARGET" ]] || { log_error "target colour is required"; usage; exit 2; }
validate_color "$TARGET"

CURRENT="$(nginx_active_color)"

if [[ "$CURRENT" == "$TARGET" ]]; then
    log_info "edge is already pointing at '$TARGET' — nothing to do (idempotent)"
    state_set active_color "$TARGET"
    exit 0
fi

# -----------------------------------------------------------------------------
# Refuse to switch to something that is not there. Without this check a typo
# would take the whole site down, which is the one outcome this system exists to
# prevent.
# -----------------------------------------------------------------------------
if [[ "$FORCE" != "1" ]]; then
    if ! color_is_up "$TARGET"; then
        log_error "colour '$TARGET' is not fully running — refusing to switch traffic to it"
        log_error "run: deploy/scripts/status.sh   (or pass --force if you accept the risk)"
        exit 1
    fi
fi

container_running "$EDGE_CONTAINER" \
    || die "edge container '$EDGE_CONTAINER' is not running; start it with docker compose -f deploy/docker-compose.edge.yml up -d"

log_step "Switching traffic: $CURRENT -> $TARGET"

# -----------------------------------------------------------------------------
# 1. Write the new pointer atomically, keeping a backup for rollback.
# -----------------------------------------------------------------------------
BACKUP="$STATE_DIR/active.conf.previous"
TMP="$(dirname "$ACTIVE_CONF")/.active.conf.$$"

if [[ -f "$ACTIVE_CONF" ]]; then
    cp "$ACTIVE_CONF" "$BACKUP"
fi

cat >"$TMP" <<EOF
# =============================================================================
# ACTIVE COLOUR — GENERATED FILE, DO NOT EDIT
# =============================================================================
# Written by deploy/scripts/switch.sh at $(date -u +'%Y-%m-%dT%H:%M:%SZ')
# Previous colour: ${CURRENT}
# Release:         $(state_get "${TARGET}.tag" unknown)
#
# Included inside the edge server block. To change the live colour, run
# switch.sh — editing this file by hand will be detected and corrected by the
# next deploy.
# =============================================================================

set \$active_color "${TARGET}";

set \$up_frontend  "frontend-${TARGET}:3000";
set \$up_backend   "backend-${TARGET}:8000";
set \$up_streaming "streaming-${TARGET}:8001";
EOF

mv -f "$TMP" "$ACTIVE_CONF"
log_info "wrote $ACTIVE_CONF -> $TARGET"

restore_and_fail() {
    log_error "$1"
    if [[ -f "$BACKUP" ]]; then
        cp "$BACKUP" "$ACTIVE_CONF"
        log_warn "restored previous active.conf ($CURRENT); traffic unchanged"
        # Best-effort reload so nginx's running config matches the file again.
        docker exec "$EDGE_CONTAINER" nginx -s reload >/dev/null 2>&1 || true
    fi
    exit 1
}

# -----------------------------------------------------------------------------
# 2. Validate before reloading. `nginx -t` parses the full config in a throwaway
#    process; if it fails, the running config is untouched and users never notice.
# -----------------------------------------------------------------------------
if ! docker exec "$EDGE_CONTAINER" nginx -t >>"$DEPLOY_LOG" 2>&1; then
    restore_and_fail "generated nginx config is invalid (see $DEPLOY_LOG) — traffic NOT switched"
fi
log_info "nginx config validated"

# -----------------------------------------------------------------------------
# 3. Graceful reload.
# -----------------------------------------------------------------------------
if ! docker exec "$EDGE_CONTAINER" nginx -s reload >>"$DEPLOY_LOG" 2>&1; then
    restore_and_fail "nginx reload failed (see $DEPLOY_LOG)"
fi
log_info "nginx reloaded gracefully (old workers finish in-flight requests)"

# -----------------------------------------------------------------------------
# 4. Read the switch back from the edge itself rather than trusting the file we
#    just wrote. This is what catches "the reload silently kept the old config".
# -----------------------------------------------------------------------------
if [[ "$VERIFY" == "1" ]]; then
    reported=""
    for _ in 1 2 3 4 5; do
        if reported="$(probe_in_container "$EDGE_CONTAINER" 'http://127.0.0.1/__edge/active')"; then
            [[ "$reported" == *"\"active_color\":\"$TARGET\""* ]] && break
        fi
        sleep 1
    done

    if [[ "$reported" != *"\"active_color\":\"$TARGET\""* ]]; then
        restore_and_fail "edge still does not report '$TARGET' after reload (got: ${reported:-no response})"
    fi
    log_info "edge confirms active colour: $TARGET"
fi

# -----------------------------------------------------------------------------
# 5. Record the move. previous_color is what rollback.sh switches back to.
# -----------------------------------------------------------------------------
state_set previous_color "$CURRENT"
state_set active_color "$TARGET"
record_history "switch" "$TARGET" "$(state_get "${TARGET}.tag" unknown)" "from=$CURRENT"

log_info "traffic is now served by '$TARGET'"
