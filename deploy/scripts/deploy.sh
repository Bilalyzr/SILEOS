#!/usr/bin/env bash
# =============================================================================
# deploy.sh — blue-green release with automatic rollback
# =============================================================================
#   deploy/scripts/deploy.sh                          # build locally, deploy
#   deploy/scripts/deploy.sh --tag v1.4.2 --pull      # deploy a registry image
#   deploy/scripts/deploy.sh --dry-run                # show the plan only
#
# ORDER OF OPERATIONS — and why it is this order
#
#   1. Preflight        Fail on missing config BEFORE touching anything.
#   2. Infra            Ensure network / data / edge exist. Never recreated.
#   3. Build or pull    Produce the images. The live colour is still serving.
#   4. Migrate          Schema first, because the new code may require it.
#   5. Start idle colour  Both colours now running; traffic still on the old one.
#   6. HEALTH GATE      The decision point. Nothing has affected users yet.
#   7. Switch           nginx reload. This is the only user-visible moment, and
#                       it drops no connections.
#   8. Verify           Confirm through the edge that the new release is serving.
#   9. Retire           Drain, then stop the old colour (kept for fast rollback).
#  10. Cleanup          Prune images beyond the retention window.
#
# Everything up to step 6 is invisible to users: a failure there tears down the
# idle colour and the live one never notices. From step 7 on, a failure switches
# traffic back to the colour that was serving a moment ago — which is still
# running, so recovery is one nginx reload, not a rebuild.
#
# Exit codes: 0 deployed · 1 failed (rolled back) · 2 usage error
# =============================================================================

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

SCRIPT_DIR="$LIB_DIR"
START_TS=$SECONDS

# --- rollback bookkeeping, read by the EXIT trap -----------------------------
DEPLOY_OK=0
SWITCHED=0
TARGET_STARTED=0
TARGET=""
CURRENT=""

usage() {
    cat <<'EOF'
Usage: deploy.sh [options]

  --tag <tag>          Release tag to deploy (default: git short SHA, else timestamp)
  --color <blue|green> Force the target slot (default: whichever is idle)
  --pull               Pull images from the registry instead of building locally
  --no-migrate         Skip the migration step
  --keep-previous      Leave the old colour's containers running after the switch
  --stop-previous      Stop AND remove the old colour after the switch
  --dry-run            Print the plan and exit without changing anything
  --verbose            Extra logging
  -h, --help           This help

Environment (see deploy/.env.deploy.example for the full list):
  REGISTRY, IMAGE_PREFIX, HEALTH_TIMEOUT, HEALTH_INTERVAL, HEALTH_RETRIES,
  DRAIN_SECONDS, KEEP_PREVIOUS, IMAGE_RETENTION, EDGE_HTTP_PORT
EOF
}

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------
PULL=0
DO_MIGRATE=1
DRY_RUN=0
FORCE_COLOR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tag)            RELEASE_TAG="${2:-}"; shift 2 ;;
        --color)          FORCE_COLOR="${2:-}"; shift 2 ;;
        --pull)           PULL=1; shift ;;
        --no-migrate)     DO_MIGRATE=0; shift ;;
        --keep-previous)  KEEP_PREVIOUS=true; shift ;;
        --stop-previous)  KEEP_PREVIOUS=false; shift ;;
        --dry-run)        DRY_RUN=1; shift ;;
        --verbose)        VERBOSE=1; shift ;;
        -h|--help)        usage; exit 0 ;;
        *) log_error "unknown argument: $1"; usage; exit 2 ;;
    esac
done

# -----------------------------------------------------------------------------
# Release tag. Defaults to the git short SHA so a deployed container can always
# be traced back to a commit; falls back to a timestamp outside a git checkout.
# -----------------------------------------------------------------------------
if [[ -z "${RELEASE_TAG:-}" ]]; then
    if git -C "$REPO_ROOT" rev-parse --short HEAD >/dev/null 2>&1; then
        RELEASE_TAG="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
    else
        RELEASE_TAG="$(date -u +%Y%m%d%H%M%S)"
    fi
fi
export RELEASE_TAG

# =============================================================================
# Steps
# =============================================================================

preflight() {
    log_step "Preflight"

    detect_compose

    docker info >/dev/null 2>&1 || die "cannot talk to the docker daemon (is it running? are you in the docker group?)"

    [[ -f "$APP_ENV_FILE" ]] \
        || die "application env file not found: $APP_ENV_FILE (copy env.example and fill it in)"

    # Compose interpolates these; an empty value would silently produce a broken
    # container rather than an error, so check up front.
    local missing=() key
    for key in POSTGRES_PASSWORD REDIS_PASSWORD SECRET_KEY JWT_SECRET ADMIN_PASSWORD; do
        if ! grep -Eq "^[[:space:]]*${key}=.+" "$APP_ENV_FILE"; then
            missing+=("$key")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        die "required values missing or empty in $APP_ENV_FILE: ${missing[*]}"
    fi

    for f in "$DEPLOY_DIR/docker-compose.app.yml" \
             "$DEPLOY_DIR/docker-compose.data.yml" \
             "$DEPLOY_DIR/docker-compose.edge.yml" \
             "$ACTIVE_CONF"; do
        [[ -f "$f" ]] || die "missing deployment file: $f"
    done

    # These are bind-mount sources. Docker would create them as root-owned
    # directories on demand, which then breaks writes from inside the container.
    mkdir -p "$REPO_ROOT/uploads" "$REPO_ROOT/certificates" \
             "$REPO_ROOT/logs" "$REPO_ROOT/logs/edge-nginx" \
             "$REPO_ROOT/streaming-service/yt_dlp_cache"

    assert_state_consistent

    log_info "release tag: $RELEASE_TAG"
    log_info "registry:    $REGISTRY/$IMAGE_PREFIX-*"
    log_info "deploy log:  $DEPLOY_LOG"
}

ensure_infra() {
    log_step "Ensuring shared infrastructure"

    if ! docker network inspect "$DOCKER_NETWORK" >/dev/null 2>&1; then
        log_info "creating docker network '$DOCKER_NETWORK'"
        docker network create "$DOCKER_NETWORK" >/dev/null
    else
        log_debug "network '$DOCKER_NETWORK' already exists"
    fi

    # `up -d` on an unchanged compose file is a no-op, so this is safe to run on
    # every deploy — it converges rather than restarts.
    if ! container_running "$POSTGRES_CONTAINER"; then
        log_info "starting data tier (postgres, redis)"
        dc_data up -d >>"$DEPLOY_LOG" 2>&1 || die "failed to start the data tier (see $DEPLOY_LOG)"
    else
        log_info "data tier already running"
    fi

    # Wait for Postgres to accept connections; migrations and the readiness gate
    # both depend on it and a cold start can take a while.
    local waited=0
    until docker exec "$POSTGRES_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
        (( waited >= 90 )) && die "postgres did not become ready within 90s"
        sleep 3; waited=$(( waited + 3 ))
    done
    log_info "postgres is accepting connections"

    if ! container_running "$EDGE_CONTAINER"; then
        log_info "starting edge proxy on port $EDGE_HTTP_PORT"
        dc_edge up -d >>"$DEPLOY_LOG" 2>&1 || die "failed to start the edge (see $DEPLOY_LOG)"
        local ewait=0
        until probe_in_container "$EDGE_CONTAINER" 'http://127.0.0.1/__edge/health' >/dev/null 2>&1; do
            (( ewait >= 60 )) && die "edge did not become healthy within 60s"
            sleep 2; ewait=$(( ewait + 2 ))
        done
    else
        log_info "edge proxy already running"
    fi

    # Validate the edge config on disk NOW, before spending minutes on images.
    # The running nginx is unaffected by a broken file until something reloads it,
    # so a config error introduced by this release's source sync would otherwise
    # only surface at the traffic switch — after the build, the migrations and the
    # health gate. Failing here costs seconds instead.
    if ! docker exec "$EDGE_CONTAINER" nginx -t >>"$DEPLOY_LOG" 2>&1; then
        log_error "the edge nginx config in this checkout is invalid:"
        docker exec "$EDGE_CONTAINER" nginx -t 2>&1 | while IFS= read -r l; do log_error "  $l"; done
        die "fix deploy/nginx/ before deploying (the running edge is still serving the previous, valid config)"
    fi
    log_info "edge nginx config validated"
}

choose_target() {
    CURRENT="$(active_color)"

    if [[ -n "$FORCE_COLOR" ]]; then
        validate_color "$FORCE_COLOR"
        TARGET="$FORCE_COLOR"
        if [[ "$TARGET" == "$CURRENT" ]]; then
            # Redeploying onto the live colour cannot be zero-downtime: its
            # containers must be recreated to pick up the new image, and there is
            # nowhere for traffic to go while that happens.
            die "--color $TARGET is the colour currently serving traffic. Deploying onto it would cause downtime. Omit --color to use the idle slot."
        fi
    else
        TARGET="$(other_color "$CURRENT")"
    fi

    log_step "Plan: $CURRENT (live) -> $TARGET (target), release $RELEASE_TAG"
}

build_images() {
    if [[ "$PULL" == "1" ]]; then
        log_step "Pulling images ($RELEASE_TAG)"
        local svc
        for svc in "${SERVICES[@]}"; do
            local ref; ref="$(image_ref "$svc" "$RELEASE_TAG")"
            log_info "pulling $ref"
            docker pull "$ref" >>"$DEPLOY_LOG" 2>&1 \
                || die "failed to pull $ref — was it pushed by CI? (see $DEPLOY_LOG)"
        done
    else
        log_step "Building images ($RELEASE_TAG)"
        # Built through the app compose file so build args (the VITE_* values Vite
        # inlines at build time) come from the same env files the runtime uses.
        COLOR="$TARGET" dc_app "$TARGET" build >>"$DEPLOY_LOG" 2>&1 \
            || die "image build failed (see $DEPLOY_LOG)"
        log_info "images built"
    fi
    record_history "images" "$TARGET" "$RELEASE_TAG" "$([[ "$PULL" == 1 ]] && echo pulled || echo built)"
}

run_migrations() {
    if [[ "$DO_MIGRATE" != "1" ]]; then
        log_warn "skipping migrations (--no-migrate)"
        return 0
    fi

    log_step "Applying database migrations"

    # Migrations run BEFORE the new colour starts, and before any traffic switch.
    # Consequence worth being explicit about: while both colours can be up, the
    # OLD code is briefly running against the NEW schema. Additive migrations
    # (new tables, new nullable columns) are safe under that condition;
    # destructive ones (dropping or renaming a column the old code still selects)
    # are NOT, and need maintenance mode — see deploy/README.md.
    if ! DEPLOY_LOG="$DEPLOY_LOG" RELEASE_TAG="$RELEASE_TAG" "$SCRIPT_DIR/migrate.sh"; then
        die "migrations failed — aborting before any traffic change"
    fi
    # The SQL ledger covers historical migrations; newer releases also use
    # Alembic. Run the NEW image once, without starting another API/scheduler.
    if ! dc_app "$TARGET" run --rm --no-deps backend python -m alembic upgrade head >>"$DEPLOY_LOG" 2>&1; then
        die "Alembic migrations failed — aborting before starting the target"
    fi
}

start_target() {
    log_step "Starting '$TARGET' ($RELEASE_TAG)"

    # --remove-orphans keeps a renamed/removed service from lingering in the slot.
    if ! dc_app "$TARGET" up -d --remove-orphans >>"$DEPLOY_LOG" 2>&1; then
        die "failed to start colour '$TARGET' (see $DEPLOY_LOG)"
    fi
    TARGET_STARTED=1
    state_set "${TARGET}.tag" "$RELEASE_TAG"

    local svc
    for svc in "${SERVICES[@]}"; do
        log_info "started $(container_name "$svc" "$TARGET")"
    done
    log_info "'$TARGET' is up but receives NO traffic yet — '$CURRENT' is still live"
}

health_gate() {
    log_step "Health gate on '$TARGET'"

    if ! DEPLOY_LOG="$DEPLOY_LOG" "$SCRIPT_DIR/health-check.sh" \
            --color "$TARGET" \
            --timeout "$HEALTH_TIMEOUT" \
            --interval "$HEALTH_INTERVAL" \
            --retries "$HEALTH_RETRIES" \
            --expect-tag "$RELEASE_TAG"; then
        die "'$TARGET' failed the health gate — traffic was never switched, '$CURRENT' is unaffected"
    fi
}

switch_traffic() {
    log_step "Switching traffic to '$TARGET'"

    if ! DEPLOY_LOG="$DEPLOY_LOG" "$SCRIPT_DIR/switch.sh" "$TARGET"; then
        die "traffic switch failed — switch.sh restored the previous config"
    fi
    SWITCHED=1
}

verify_live() {
    log_step "Verifying the live site"

    # End-to-end through the edge's published port: the only check that proves
    # the whole chain (host -> edge -> new colour -> postgres) works.
    if ! DEPLOY_LOG="$DEPLOY_LOG" "$SCRIPT_DIR/health-check.sh" \
            --url "http://127.0.0.1:${EDGE_HTTP_PORT}/health/version" \
            --timeout "$EDGE_VERIFY_TIMEOUT" \
            --interval 3 \
            --retries 2 \
            --expect-tag "$RELEASE_TAG"; then
        die "the live site is not serving release $RELEASE_TAG through the edge"
    fi

    if ! DEPLOY_LOG="$DEPLOY_LOG" "$SCRIPT_DIR/health-check.sh" \
            --url "http://127.0.0.1:${EDGE_HTTP_PORT}/health/ready" \
            --timeout 30 --interval 3 --retries 2 --quiet; then
        die "readiness through the edge failed after the switch"
    fi

    log_info "live site verified on release $RELEASE_TAG"
}

retire_previous() {
    log_step "Retiring '$CURRENT'"

    # Drain window: the reload already handed new connections to the new colour,
    # but old workers may still be finishing long requests (video ranges, large
    # uploads) against the old containers. Stopping them immediately would cut
    # those off — the one way a "zero-downtime" deploy still shows users an error.
    if (( DRAIN_SECONDS > 0 )); then
        log_info "draining for ${DRAIN_SECONDS}s so in-flight requests to '$CURRENT' can finish"
        sleep "$DRAIN_SECONDS"
    fi

    if [[ "$KEEP_PREVIOUS" == "true" ]]; then
        # Stopped, not removed. A stopped container can be restarted in about a
        # second, which makes rollback essentially instant; a removed one has to
        # be recreated from its image.
        log_info "stopping (but keeping) '$CURRENT' containers for fast rollback"
        dc_app "$CURRENT" stop >>"$DEPLOY_LOG" 2>&1 || log_warn "could not stop '$CURRENT' cleanly"
    else
        log_info "stopping and removing '$CURRENT' containers"
        dc_app "$CURRENT" down --remove-orphans >>"$DEPLOY_LOG" 2>&1 || log_warn "could not remove '$CURRENT' cleanly"
    fi
}

cleanup_images() {
    log_step "Cleaning up old images"
    if ! IMAGE_RETENTION="$IMAGE_RETENTION" DEPLOY_LOG="$DEPLOY_LOG" "$SCRIPT_DIR/cleanup.sh"; then
        # Never fail a successful deploy over housekeeping.
        log_warn "image cleanup reported a problem — the deployment itself is fine"
    fi
}

# =============================================================================
# Failure handling
# =============================================================================
# A single EXIT trap covers every exit path: `die`, an unexpected non-zero from
# `set -e`, and Ctrl-C. Guarding on DEPLOY_OK rather than on $? means a rollback
# also happens if something exits non-zero without going through `die`.
# =============================================================================
on_exit() {
    local rc=$?
    local elapsed=$(( SECONDS - START_TS ))

    if [[ "$DRY_RUN" == "1" && "$DEPLOY_OK" == "1" ]]; then
        release_lock
        return
    fi

    if [[ "$DEPLOY_OK" == "1" ]]; then
        log_step "Deployment SUCCEEDED in $(human_duration "$elapsed")"
        log_info "live colour: $TARGET   release: $RELEASE_TAG"
        log_info "previous colour '$CURRENT' is $([[ "$KEEP_PREVIOUS" == "true" ]] && echo 'stopped and available for instant rollback' || echo 'removed')"
        log_info "log: $DEPLOY_LOG"
        record_history "deploy-ok" "$TARGET" "$RELEASE_TAG" "duration=${elapsed}s"
        release_lock
        return
    fi

    log_error "Deployment FAILED after $(human_duration "$elapsed") (exit $rc)"
    record_history "deploy-failed" "${TARGET:-?}" "$RELEASE_TAG" "duration=${elapsed}s"

    if [[ "$SWITCHED" == "1" ]]; then
        # Traffic had already moved. Put it back on the colour that was serving
        # before this run; it is stopped-but-present at worst, so this is fast.
        log_warn "traffic had already been switched to '$TARGET' — rolling back to '$CURRENT'"
        if DEPLOY_LOG="$DEPLOY_LOG" "$SCRIPT_DIR/rollback.sh" --to "$CURRENT" --reason "failed deploy of $RELEASE_TAG"; then
            log_info "rollback complete — '$CURRENT' is serving again"
        else
            log_error "AUTOMATIC ROLLBACK FAILED. Manual intervention required."
            log_error "  deploy/scripts/status.sh"
            log_error "  deploy/scripts/rollback.sh --to $CURRENT --force"
        fi
    elif [[ "$TARGET_STARTED" == "1" ]]; then
        # Never switched, so users were never affected. Just clear the slot.
        log_warn "traffic was never switched — '$CURRENT' still serving, no user impact"
        log_info "tearing down the failed '$TARGET' slot"
        dc_app "$TARGET" down --remove-orphans >>"$DEPLOY_LOG" 2>&1 \
            || log_warn "could not fully tear down '$TARGET'; inspect with: docker ps -a"
    else
        log_warn "failed before starting any container — nothing to roll back"
    fi

    log_error "log kept for debugging: $DEPLOY_LOG"
    release_lock
}

trap on_exit EXIT

# =============================================================================
# Main
# =============================================================================
main() {
    log_step "SashaInfinity LMS deployment — run $RUN_ID"

    preflight
    choose_target

    if [[ "$DRY_RUN" == "1" ]]; then
        log_step "Dry run — no changes made"
        cat <<EOF

  release tag        : $RELEASE_TAG
  live colour        : $CURRENT
  target colour      : $TARGET
  images             : $(image_ref backend "$RELEASE_TAG")
                       $(image_ref frontend "$RELEASE_TAG")
                       $(image_ref streaming "$RELEASE_TAG")
  source             : $([[ "$PULL" == "1" ]] && echo "pull from registry" || echo "build locally")
  migrations         : $([[ "$DO_MIGRATE" == "1" ]] && echo enabled || echo skipped)
  health gate        : ${HEALTH_RETRIES} consecutive passes, ${HEALTH_TIMEOUT}s budget
  drain window       : ${DRAIN_SECONDS}s
  keep previous      : $KEEP_PREVIOUS
  edge port          : $EDGE_HTTP_PORT

EOF
        DEPLOY_OK=1
        exit 0
    fi

    # The lock is taken only once we are about to mutate something, so that
    # --dry-run and preflight never block a real deploy.
    acquire_lock

    ensure_infra
    build_images
    run_migrations
    start_target
    health_gate
    switch_traffic
    verify_live
    retire_previous
    cleanup_images

    DEPLOY_OK=1
}

main
