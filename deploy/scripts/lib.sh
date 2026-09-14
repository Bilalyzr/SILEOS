#!/usr/bin/env bash
# =============================================================================
# lib.sh — shared plumbing for every deploy script
# =============================================================================
# Sourced, never executed. Provides paths, logging, locking, colour/state
# bookkeeping and the docker compose wrappers.
#
# Every script that sources this gets `set -euo pipefail`, so a typo or an
# unchecked failure aborts rather than half-deploying.
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Paths. Resolved from this file's location so the scripts work no matter what
# directory they are invoked from — cron and CI rarely cd where you expect.
# -----------------------------------------------------------------------------
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$LIB_DIR/.." && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"
STATE_DIR="$DEPLOY_DIR/state"
LOG_DIR="$REPO_ROOT/logs/deploy"
ACTIVE_CONF="$DEPLOY_DIR/nginx/active/active.conf"
MAINTENANCE_FLAG="$DEPLOY_DIR/nginx/maintenance/ON"
LOCK_DIR="$STATE_DIR/.lock"

mkdir -p "$STATE_DIR" "$LOG_DIR" "$DEPLOY_DIR/secrets"

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
# Two env files, both optional, layered:
#
#   1. <repo>/.env         — the application's existing runtime config. NOT
#                            sourced into the shell: it legitimately contains
#                            values like CORS_ORIGINS=["a", "b"] that are valid
#                            for docker compose's own parser but are a syntax
#                            error for bash. It is handed to compose via
#                            --env-file instead.
#   2. deploy/.env.deploy  — deployment knobs only (registry, timeouts, ports).
#                            Simple KEY=value, read by the scripts themselves.
#                            Keep it that way: no spaces, no brackets, no command
#                            substitution.
#
# Real environment variables outrank both, which is what lets CI pass RELEASE_TAG
# and REGISTRY without editing any file on the server.
# -----------------------------------------------------------------------------
APP_ENV_FILE="${APP_ENV_FILE:-$REPO_ROOT/.env}"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-$DEPLOY_DIR/.env.deploy}"

# Parsed line by line rather than `set -a; source ...` on purpose. Sourcing would
# let the file OVERWRITE variables already present in the environment, inverting
# the precedence documented above — and CI passes REGISTRY and RELEASE_TAG as
# environment variables while .env.deploy on the server still carries its own
# values for them. Parsing also means a stray line cannot execute arbitrary
# commands, and CRLF endings (likely, since this repo is edited on Windows) do not
# end up inside the values.
load_deploy_env() {
    local file="$1" line key val
    [[ -f "$file" ]] || return 0

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"
        [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
        [[ "$line" == *=* ]] || continue

        key="${line%%=*}"
        key="${key//[[:space:]]/}"
        val="${line#*=}"

        [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue

        # Already set in the environment? Leave it alone.
        [[ -n "${!key+set}" ]] && continue

        export "$key=$val"
    done <"$file"
}

load_deploy_env "$DEPLOY_ENV_FILE"

# --- deployment defaults (every one overridable via env or .env.deploy) -------
DOCKER_NETWORK="${DOCKER_NETWORK:-sasha-net}"
REGISTRY="${REGISTRY:-local}"
IMAGE_PREFIX="${IMAGE_PREFIX:-sasha-lms}"
EDGE_HTTP_PORT="${EDGE_HTTP_PORT:-3200}"

# Health gating
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-180}"        # seconds to wait for a colour
HEALTH_INTERVAL="${HEALTH_INTERVAL:-5}"        # seconds between attempts
HEALTH_RETRIES="${HEALTH_RETRIES:-3}"          # consecutive passes required
EDGE_VERIFY_TIMEOUT="${EDGE_VERIFY_TIMEOUT:-60}"

# Post-switch behaviour
DRAIN_SECONDS="${DRAIN_SECONDS:-15}"           # grace before stopping old colour
KEEP_PREVIOUS="${KEEP_PREVIOUS:-true}"         # keep old containers for fast rollback
IMAGE_RETENTION="${IMAGE_RETENTION:-3}"        # releases of images to keep

# Postgres (for the migration runner)
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-sasha-postgres}"
POSTGRES_USER="${POSTGRES_USER:-tutor}"
POSTGRES_DB="${POSTGRES_DB:-tutor_lms}"

EDGE_CONTAINER="${EDGE_CONTAINER:-sasha-edge}"

readonly SERVICES=(backend frontend streaming)

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
# Everything goes to stdout AND to a per-run file under logs/deploy/, because
# the single most useful artefact after a failed deploy is the log of the deploy
# that failed. DEPLOY_LOG is set by the caller (deploy.sh) or defaults here.
# -----------------------------------------------------------------------------
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
DEPLOY_LOG="${DEPLOY_LOG:-$LOG_DIR/$(basename "${0%.sh}")-$RUN_ID.log}"

if [[ -t 1 && "${NO_COLOR:-}" != "1" ]]; then
    C_RED=$'\033[0;31m'; C_GRN=$'\033[0;32m'; C_YLW=$'\033[1;33m'
    C_BLU=$'\033[0;34m'; C_DIM=$'\033[2m';    C_RST=$'\033[0m'
else
    C_RED=''; C_GRN=''; C_YLW=''; C_BLU=''; C_DIM=''; C_RST=''
fi

_log() {
    local level="$1" colour="$2"; shift 2
    local ts; ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    printf '%s%s%s [%s] %s\n' "$colour" "$ts" "$C_RST" "$level" "$*"
    printf '%s [%s] %s\n' "$ts" "$level" "$*" >>"$DEPLOY_LOG"
}

log_info()  { _log "INFO " "$C_GRN" "$@"; }
log_warn()  { _log "WARN " "$C_YLW" "$@"; }
log_error() { _log "ERROR" "$C_RED" "$@" >&2; }
log_debug() { [[ "${VERBOSE:-0}" == "1" ]] && _log "DEBUG" "$C_DIM" "$@" || true; }

log_step() {
    local ts; ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    printf '\n%s==> %s%s\n' "$C_BLU" "$*" "$C_RST"
    printf '%s [STEP ] === %s ===\n' "$ts" "$*" >>"$DEPLOY_LOG"
}

die() { log_error "$@"; exit 1; }

# -----------------------------------------------------------------------------
# docker compose wrappers
# -----------------------------------------------------------------------------
# Supports both the v2 plugin (`docker compose`) and the legacy standalone
# binary (`docker-compose`), because production servers run whichever they were
# set up with and this must not be the thing that breaks a release.
# -----------------------------------------------------------------------------
_compose_cmd=()

detect_compose() {
    if [[ ${#_compose_cmd[@]} -gt 0 ]]; then return 0; fi
    command -v docker >/dev/null 2>&1 || die "docker is not installed or not on PATH"
    if docker compose version >/dev/null 2>&1; then
        _compose_cmd=(docker compose)
    elif command -v docker-compose >/dev/null 2>&1; then
        _compose_cmd=(docker-compose)
    else
        die "neither 'docker compose' nor 'docker-compose' is available"
    fi
    log_debug "using compose: ${_compose_cmd[*]}"
}

# Assembles the --env-file flags into the caller's array (bash nameref). Missing
# files are skipped rather than fatal, so a fresh checkout can still run
# `status.sh` and `--help` before .env exists.
_env_file_array() {
    local -n out="$1"
    out=()
    [[ -f "$APP_ENV_FILE" ]]    && out+=(--env-file "$APP_ENV_FILE")
    [[ -f "$DEPLOY_ENV_FILE" ]] && out+=(--env-file "$DEPLOY_ENV_FILE")
    return 0
}

# Loopback-only host port the backend of a given colour is published on, for
# the recordings finalize worker (which runs on the HOST, outside docker, and
# therefore cannot reach backend-blue/backend-green over the docker network).
# blue -> 8010, green -> 8011. Bound to 127.0.0.1 in docker-compose.app.yml, so
# these are reachable only from the host itself, never from the internet.
backend_loopback_port() {
    case "$1" in
        blue)  printf '8010' ;;
        green) printf '8011' ;;
        *)     printf '8010' ;;
    esac
}

# dc_app <colour> <compose args...>
dc_app() {
    detect_compose
    local colour="$1"; shift
    local envargs; _env_file_array envargs
    COLOR="$colour" \
    BACKEND_LOOPBACK_PORT="$(backend_loopback_port "$colour")" \
    "${_compose_cmd[@]}" \
        "${envargs[@]}" \
        -p "sasha-$colour" \
        -f "$DEPLOY_DIR/docker-compose.app.yml" \
        "$@"
}

dc_data() {
    detect_compose
    local envargs; _env_file_array envargs
    "${_compose_cmd[@]}" "${envargs[@]}" -f "$DEPLOY_DIR/docker-compose.data.yml" "$@"
}

dc_edge() {
    detect_compose
    local envargs; _env_file_array envargs
    "${_compose_cmd[@]}" "${envargs[@]}" -f "$DEPLOY_DIR/docker-compose.edge.yml" "$@"
}

# -----------------------------------------------------------------------------
# Colour + state bookkeeping
# -----------------------------------------------------------------------------
# state/active_color is the authoritative record of which colour the scripts
# believe is live. nginx's active.conf is the record of which colour actually
# receives traffic. They can only disagree if someone edited one by hand, and
# assert_state_consistent() exists to catch precisely that before a deploy makes
# it worse.
# -----------------------------------------------------------------------------
state_get() {
    local key="$1" default="${2:-}"
    if [[ -f "$STATE_DIR/$key" ]]; then
        tr -d '[:space:]' <"$STATE_DIR/$key"
    else
        printf '%s' "$default"
    fi
}

state_set() {
    local key="$1" value="$2"
    printf '%s\n' "$value" >"$STATE_DIR/$key"
}

active_color()   { state_get active_color blue; }
previous_color() { state_get previous_color ""; }

other_color() {
    case "$1" in
        blue)  printf 'green' ;;
        green) printf 'blue'  ;;
        *)     die "invalid colour '$1' (expected blue or green)" ;;
    esac
}

validate_color() {
    [[ "$1" == "blue" || "$1" == "green" ]] || die "invalid colour '$1' (expected blue or green)"
}

# The colour nginx is actually serving, read back out of the generated config.
nginx_active_color() {
    [[ -f "$ACTIVE_CONF" ]] || { printf 'unknown'; return; }
    sed -n 's/^[[:space:]]*set[[:space:]]\+\$active_color[[:space:]]\+"\([a-z]*\)".*/\1/p' "$ACTIVE_CONF" | head -n1
}

assert_state_consistent() {
    local recorded nginx_col
    recorded="$(active_color)"
    nginx_col="$(nginx_active_color)"
    if [[ "$recorded" != "$nginx_col" ]]; then
        log_warn "state/active_color says '$recorded' but nginx active.conf says '$nginx_col'"
        log_warn "trusting nginx (it is what actually serves traffic) and repairing state"
        validate_color "$nginx_col"
        state_set active_color "$nginx_col"
    fi
}

container_name() {
    local service="$1" colour="$2"
    printf 'sasha-%s-%s' "$service" "$colour"
}

container_exists()  { docker inspect "$1" >/dev/null 2>&1; }
container_running() { [[ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null || echo false)" == "true" ]]; }

color_is_up() {
    local colour="$1" service
    for service in "${SERVICES[@]}"; do
        container_running "$(container_name "$service" "$colour")" || return 1
    done
    return 0
}

# -----------------------------------------------------------------------------
# Locking
# -----------------------------------------------------------------------------
# mkdir is used rather than flock: it is atomic on every filesystem that matters
# and does not depend on util-linux being installed. The PID inside lets us
# distinguish a genuinely concurrent deploy from a lock left behind by a killed
# one.
# -----------------------------------------------------------------------------
acquire_lock() {
    local waited=0 max_wait="${LOCK_WAIT:-0}"
    while ! mkdir "$LOCK_DIR" 2>/dev/null; do
        local holder; holder="$(cat "$LOCK_DIR/pid" 2>/dev/null || echo '?')"
        if [[ "$holder" != '?' ]] && ! kill -0 "$holder" 2>/dev/null; then
            log_warn "removing stale lock from dead PID $holder"
            rm -rf "$LOCK_DIR"
            continue
        fi
        if (( waited >= max_wait )); then
            die "another deploy is in progress (PID $holder). Wait for it, or remove $LOCK_DIR if you are certain it is stale."
        fi
        sleep 2; waited=$(( waited + 2 ))
    done
    printf '%s\n' "$$" >"$LOCK_DIR/pid"
    LOCK_HELD=1
}

release_lock() {
    if [[ "${LOCK_HELD:-0}" == "1" ]]; then
        rm -rf "$LOCK_DIR"
        LOCK_HELD=0
    fi
}

# -----------------------------------------------------------------------------
# HTTP probing
# -----------------------------------------------------------------------------
# curl is preferred; busybox wget is the fallback so this works on hosts without
# curl and inside alpine containers. Returns the body on stdout, non-zero on any
# response that is not 2xx.
# -----------------------------------------------------------------------------
http_get() {
    local url="$1" timeout="${2:-10}"
    if command -v curl >/dev/null 2>&1; then
        curl -fsS --max-time "$timeout" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O - -T "$timeout" "$url"
    else
        die "neither curl nor wget is available on this host"
    fi
}

# Runs an HTTP probe from INSIDE a container, so no host port needs publishing
# and we test the app exactly as the edge will reach it. Tries curl then wget
# because the backend image has curl and the node-alpine frontend has wget.
probe_in_container() {
    local container="$1" url="$2"
    docker exec "$container" sh -c \
        "command -v curl >/dev/null 2>&1 && curl -fsS --max-time 10 '$url' \
         || wget -q -O - -T 10 '$url'" 2>/dev/null
}

# -----------------------------------------------------------------------------
# History
# -----------------------------------------------------------------------------
record_history() {
    local event="$1" colour="$2" tag="$3" detail="${4:-}"
    printf '%s\t%s\t%s\t%s\t%s\n' \
        "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$event" "$colour" "$tag" "$detail" \
        >>"$STATE_DIR/history.log"
}

human_duration() {
    local s="$1"
    printf '%dm %ds' $(( s / 60 )) $(( s % 60 ))
}

image_ref() {
    local service="$1" tag="$2"
    printf '%s/%s-%s:%s' "$REGISTRY" "$IMAGE_PREFIX" "$service" "$tag"
}
