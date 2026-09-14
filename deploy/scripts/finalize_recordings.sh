#!/usr/bin/env bash
# =============================================================================
# finalize_recordings.sh — cron wrapper around finalize_recordings.py
# =============================================================================
# Intended to run every 2 minutes via cron (per the brief's "finalize worker
# scans every 2 min" pipeline description), e.g.:
#
#   */2 * * * * /path/to/deploy/scripts/finalize_recordings.sh
#
# It:
#   1. Sources deploy/.env.live for JITSI_RECORDINGS_DIR / INTERNAL_TOKEN
#      (NEVER reads secrets from command-line arguments).
#   2. Finds the ACTIVE colour's backend on the loopback interface by probing
#      GET /health on 8010 (blue) then 8011 (green) — see BACKEND_URL below.
#   3. Invokes finalize_recordings.py with python3 (stdlib-only — no venv
#      dependency, matching the worker's own no-external-deps design).
#   4. Appends stdout/stderr to logs/finalize_recordings.log (created if
#      missing) rather than letting cron mail every run's output.
#
# Deliberately self-contained rather than sourcing deploy/scripts/lib.sh,
# mirroring health_jitsi.sh's own reasoning: this worker is not part of the
# blue-green APP tier switch machinery.
#
# Exit codes: passthrough of finalize_recordings.py's exit code
#   (0 = ran, possibly with per-file failures logged; 2 = usage/config error)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$DEPLOY_DIR/.." && pwd)"

ENV_FILE="${JITSI_ENV_FILE:-$DEPLOY_DIR/.env.live}"
LOG_DIR="${FINALIZE_LOG_DIR:-$REPO_DIR/logs}"
LOG_FILE="$LOG_DIR/finalize_recordings.log"

# Loopback ports the app tier publishes per colour (127.0.0.1 only — see
# deploy/docker-compose.app.yml "WORKER LOOPBACK PORT" and
# deploy/scripts/lib.sh:backend_loopback_port). blue -> 8010, green -> 8011.
# Kept as a literal list rather than sourcing lib.sh, matching this script's
# deliberate self-containment (it is not part of the blue-green switch
# machinery); lib.sh is the source of truth for the mapping and the two must
# stay in step.
BACKEND_LOOPBACK_PORTS=(8010 8011)

usage() {
    cat <<'EOF'
Usage: finalize_recordings.sh [options]

Options:
  --env-file <path>  Path to the Jitsi env file (default: deploy/.env.live)
  --log-file <path>  Path to append run output to (default: logs/finalize_recordings.log)
  -h, --help         Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        --log-file) LOG_FILE="${2:-}"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "unknown argument: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ ! -f "$ENV_FILE" ]]; then
    echo "finalize_recordings: env file not found: $ENV_FILE" >&2
    exit 2
fi

# shellcheck source=/dev/null
set -a
source "$ENV_FILE"
set +a

if [[ -z "${JITSI_RECORDINGS_DIR:-}" ]]; then
    echo "finalize_recordings: JITSI_RECORDINGS_DIR not set in $ENV_FILE" >&2
    exit 2
fi
if [[ -z "${INTERNAL_TOKEN:-}" ]]; then
    echo "finalize_recordings: INTERNAL_TOKEN not set in $ENV_FILE" >&2
    exit 2
fi

# JITSI_RECORDINGS_DIR in .env.live is relative to deploy/ (compose
# bind-mount source, e.g. "./recordings") — resolve it against DEPLOY_DIR so
# this script works regardless of the caller's own working directory (cron
# invokes scripts with an unpredictable cwd).
RECORDINGS_DIR="$JITSI_RECORDINGS_DIR"
if [[ "$RECORDINGS_DIR" != /* ]]; then
    RECORDINGS_DIR="$DEPLOY_DIR/$RECORDINGS_DIR"
fi

# Restrict the log dir/file to owner-only before creating them — the log
# ends up containing internal recording file paths and truncated backend
# error bodies (never the secret token itself), but there's no reason for
# other local users to be able to read it. umask affects only files/dirs
# created AFTER this point in the script.
umask 077
mkdir -p "$LOG_DIR"

PYTHON_BIN="$(command -v python3 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
    echo "finalize_recordings: python3 not found on PATH" >&2
    exit 2
fi

# -----------------------------------------------------------------------------
# Locate the ACTIVE colour's backend.
# -----------------------------------------------------------------------------
# Both colours can be up at once during a blue-green switch, each on its own
# loopback port, so a hardcoded port would silently POST into whichever
# container happened to own it — including a just-superseded one. Probe
# /health and take the first that answers. Both colours share one database, so
# either answering instance ingests correctly; the probe only has to find a
# LIVE one, not the "right" one.
#
# FINALIZE_BACKEND_URL still wins when set, so an operator can pin a colour
# (or point at a non-default host) without editing this script.
resolve_backend_url() {
    if [[ -n "${FINALIZE_BACKEND_URL:-}" ]]; then
        printf '%s' "$FINALIZE_BACKEND_URL"
        return 0
    fi
    local port
    for port in "${BACKEND_LOOPBACK_PORTS[@]}"; do
        if curl -fsS --max-time 5 -o /dev/null "http://127.0.0.1:${port}/health" 2>/dev/null; then
            printf 'http://127.0.0.1:%s' "$port"
            return 0
        fi
    done
    return 1
}

if ! command -v curl >/dev/null 2>&1; then
    echo "finalize_recordings: curl not found on PATH (needed to probe the backend)" >&2
    exit 2
fi

if ! BACKEND_URL="$(resolve_backend_url)"; then
    # Not an error worth alerting on from cron: during a deploy there can be a
    # short window with no colour answering. The next run (2 min later) picks
    # the files up — nothing is lost, because a file is only marked .ingested
    # after a 200.
    {
        echo "=== finalize_recordings run at $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="
        echo "no backend answered /health on ports ${BACKEND_LOOPBACK_PORTS[*]}; skipping this run"
    } >>"$LOG_FILE" 2>&1
    exit 0
fi

{
    echo "=== finalize_recordings run at $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="
    echo "backend: $BACKEND_URL"
    JITSI_RECORDINGS_DIR="$RECORDINGS_DIR" \
    INTERNAL_TOKEN="$INTERNAL_TOKEN" \
        "$PYTHON_BIN" "$SCRIPT_DIR/finalize_recordings.py" --backend-url "$BACKEND_URL"
} >>"$LOG_FILE" 2>&1
