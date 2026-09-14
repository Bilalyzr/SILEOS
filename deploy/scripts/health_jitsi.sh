#!/usr/bin/env bash
# =============================================================================
# health_jitsi.sh — is the self-hosted Jitsi stack (deploy/compose.live.yml)
# healthy right now?
# =============================================================================
#   deploy/scripts/health_jitsi.sh
#   deploy/scripts/health_jitsi.sh --quiet
#
# Deliberately self-contained rather than sourcing deploy/scripts/lib.sh: that
# file's state/locking/colour bookkeeping belongs to the blue-green APP tier
# switch, and the Jitsi stack is a separate, non-colour-duplicated instance on
# the data-tier side (see deploy/compose.live.yml's header comment). Pulling
# lib.sh in here would create a dependency on machinery this stack has nothing
# to do with.
#
# Checks:
#   1. docker inspect health/running state for each of the five core
#      containers (jitsi-web, prosody, jicofo, jvb, jvb — jibri is checked too
#      when its "recording" profile container exists, but its absence is not
#      a failure since it is profile-gated).
#   2. HTTP 200 from the host-published web port (127.0.0.1:8080).
#
# Exit codes: 0 healthy | 1 unhealthy | 2 usage error
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Core containers that must always be up. jibri is intentionally excluded —
# it only runs under the "recording" compose profile, so its absence is
# expected on a stack that has not enabled recording.
CORE_CONTAINERS=(
    sasha-jitsi-web
    sasha-jitsi-prosody
    sasha-jitsi-jicofo
    sasha-jitsi-jvb
)
OPTIONAL_CONTAINERS=(
    sasha-jitsi-jibri
)

WEB_URL="${JITSI_HEALTH_URL:-http://127.0.0.1:8080}"
QUIET=0

usage() {
    cat <<'EOF'
Usage: health_jitsi.sh [options]

Options:
  --url <url>   Web health-probe URL (default: http://127.0.0.1:8080)
  --quiet       Only print the final one-line summary
  -h, --help    Show this help

Exit codes: 0 healthy | 1 unhealthy | 2 usage error
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --url)      WEB_URL="${2:-}"; shift 2 ;;
        --quiet)    QUIET=1; shift ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "unknown argument: $1" >&2; usage; exit 2 ;;
    esac
done

say() { [[ "$QUIET" == "1" ]] || printf '%s\n' "$*"; }

FAILURES=()

# -----------------------------------------------------------------------------
# Container health/running checks.
# -----------------------------------------------------------------------------
check_container() {
    local name="$1" required="$2"

    if ! docker inspect "$name" >/dev/null 2>&1; then
        if [[ "$required" == "1" ]]; then
            FAILURES+=("$name: container does not exist")
            say "FAIL  $name — does not exist"
        else
            say "SKIP  $name — not running (optional / recording profile)"
        fi
        return
    fi

    local running status health
    running="$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null || echo false)"
    if [[ "$running" != "true" ]]; then
        status="$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo unknown)"
        FAILURES+=("$name: not running (status: $status)")
        say "FAIL  $name — not running (status: $status)"
        return
    fi

    # Not every jitsi image defines a HEALTHCHECK the same way; when Docker has
    # no health status for a container (empty string) that is not itself a
    # failure as long as it is running — fall through and treat it as healthy.
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$name" 2>/dev/null || echo "")"
    if [[ -n "$health" && "$health" != "healthy" ]]; then
        FAILURES+=("$name: health status is '$health'")
        say "FAIL  $name — health status is '$health'"
        return
    fi

    say "OK    $name — running${health:+ (health: $health)}"
}

for c in "${CORE_CONTAINERS[@]}"; do
    check_container "$c" 1
done
for c in "${OPTIONAL_CONTAINERS[@]}"; do
    check_container "$c" 0
done

# -----------------------------------------------------------------------------
# HTTP probe against the host-published web port.
# -----------------------------------------------------------------------------
http_probe() {
    local url="$1" code
    if command -v curl >/dev/null 2>&1; then
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" || echo 000)"
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --spider -T 10 "$url" 2>/dev/null; then
            code=200
        else
            code=000
        fi
    else
        FAILURES+=("no curl or wget available on this host to probe $url")
        say "FAIL  http probe — neither curl nor wget available"
        return
    fi

    if [[ "$code" == "200" ]]; then
        say "OK    http $url — 200"
    else
        FAILURES+=("http $url returned '$code', expected 200")
        say "FAIL  http $url — got '$code', expected 200"
    fi
}

http_probe "$WEB_URL"

# -----------------------------------------------------------------------------
# Summary.
# -----------------------------------------------------------------------------
if [[ ${#FAILURES[@]} -eq 0 ]]; then
    printf 'health_jitsi: OK — all checks passed (%s)\n' "$DEPLOY_DIR"
    exit 0
fi

printf 'health_jitsi: FAIL — %d check(s) failed:\n' "${#FAILURES[@]}"
for f in "${FAILURES[@]}"; do
    printf '  - %s\n' "$f"
done
exit 1
