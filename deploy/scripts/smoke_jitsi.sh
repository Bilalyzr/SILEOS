#!/usr/bin/env bash
# =============================================================================
# smoke_jitsi.sh — VPS-only smoke test for the Jitsi stack + edge vhost
# =============================================================================
# Run this ON THE VPS, after `docker compose -f deploy/compose.live.yml
# --env-file deploy/.env.live up -d` and after health_jitsi.sh passes:
#
#   deploy/scripts/smoke_jitsi.sh
#
# It:
#   1. Sources deploy/.env.live for JITSI_PUBLIC_URL / JITSI_JWT_APP_ID /
#      JITSI_JWT_SECRET (NEVER reads secrets from command-line arguments —
#      those end up in shell history and `ps`).
#   2. Mints a throwaway HS256 JWT for a disposable test room using python3
#      (no extra dependency: PyJWT is not assumed to be installed on the
#      host, so the token is built by hand from stdlib `hmac`/`hashlib`/
#      `base64`/`json`).
#   3. Prints a join URL a human can open in a browser to eyeball the room.
#   4. Curls the public vhost and its websocket upgrade endpoints, expecting
#      101/200-class responses.
#
# This script cannot run from the build machine — the plan documents that
# limitation (deviations file item 13). It is meant to be executed by the
# owner during the post-implementation VPS checklist.
#
# Exit codes: 0 all probes passed | 1 a probe failed | 2 usage/config error
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${JITSI_ENV_FILE:-$DEPLOY_DIR/.env.live}"

usage() {
    cat <<'EOF'
Usage: smoke_jitsi.sh [options]

Options:
  --env-file <path>  Path to the Jitsi env file (default: deploy/.env.live)
  --room <name>      Test room name (default: smoketest-<random>)
  -h, --help         Show this help

Secrets are never accepted as arguments — this script only reads them from
the env file. Run it on the VPS after the Jitsi stack is up.

Exit codes: 0 all probes passed | 1 a probe failed | 2 usage/config error
EOF
}

ROOM=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        --room)     ROOM="${2:-}"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "unknown argument: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -f "$ENV_FILE" ]] || { echo "smoke_jitsi: env file not found: $ENV_FILE" >&2; exit 2; }

# -----------------------------------------------------------------------------
# Load the env file line by line (never `source` it — see lib.sh's
# load_deploy_env for the same reasoning: a stray line must not be able to
# execute arbitrary commands, and CRLF line endings must not leak into
# values).
# -----------------------------------------------------------------------------
load_env_file() {
    local file="$1" line key val
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"
        [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
        [[ "$line" == *=* ]] || continue
        key="${line%%=*}"
        key="${key//[[:space:]]/}"
        val="${line#*=}"
        [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
        [[ -n "${!key+set}" ]] && continue
        export "$key=$val"
    done <"$file"
}

load_env_file "$ENV_FILE"

: "${JITSI_PUBLIC_URL:?JITSI_PUBLIC_URL must be set in $ENV_FILE}"
: "${JITSI_JWT_APP_ID:?JITSI_JWT_APP_ID must be set in $ENV_FILE}"
: "${JITSI_JWT_SECRET:?JITSI_JWT_SECRET must be set in $ENV_FILE}"

if [[ "$JITSI_JWT_SECRET" == changeme-* ]]; then
    echo "smoke_jitsi: JITSI_JWT_SECRET in $ENV_FILE is still a changeme-* placeholder" >&2
    exit 2
fi

command -v python3 >/dev/null 2>&1 || { echo "smoke_jitsi: python3 is required" >&2; exit 2; }

if [[ -z "$ROOM" ]]; then
    ROOM="smoketest-$(date +%s)-$$"
fi

# -----------------------------------------------------------------------------
# Mint a throwaway HS256 JWT with stdlib only (no PyJWT dependency assumed on
# the host). Claims mirror app/services/jitsi_token_service.py's shape closely
# enough for a manual join test; this is a disposable smoke-test token, not
# what the backend issues in production.
# -----------------------------------------------------------------------------
JWT="$(
    JITSI_JWT_APP_ID="$JITSI_JWT_APP_ID" \
    JITSI_JWT_SECRET="$JITSI_JWT_SECRET" \
    ROOM="$ROOM" \
    python3 - <<'PYEOF'
import base64
import hashlib
import hmac
import json
import os
import time


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


app_id = os.environ["JITSI_JWT_APP_ID"]
secret = os.environ["JITSI_JWT_SECRET"]
room = os.environ["ROOM"]
now = int(time.time())

header = {"alg": "HS256", "typ": "JWT"}
payload = {
    "iss": app_id,
    "aud": app_id,
    "sub": app_id,
    "room": room,
    "iat": now,
    "nbf": now,
    "exp": now + 900,
    "context": {
        "user": {
            "id": "smoketest",
            "name": "Smoke Test",
            "email": "smoketest@sashainfinity.com",
            "avatar": "",
            "moderator": "true",
        },
        "features": {
            "screen-sharing": "true",
            "recording": "true",
            "livestreaming": "false",
            "transcription": "false",
        },
    },
}

signing_input = (
    b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    + "."
    + b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
)
signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
print(signing_input + "." + b64url(signature))
PYEOF
)"

JOIN_URL="${JITSI_PUBLIC_URL%/}/${ROOM}?jwt=${JWT}"

echo "smoke_jitsi: test room  = $ROOM"
echo "smoke_jitsi: join URL   = $JOIN_URL"
echo

FAILURES=()

# -----------------------------------------------------------------------------
# curl helper: prints "<code>" for the final HTTP status, or "000" on
# connection failure. Used for both plain-HTTP and websocket-upgrade probes.
# -----------------------------------------------------------------------------
probe_status() {
    local url="$1"; shift
    curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$@" "$url" 2>/dev/null || echo 000
}

check_expect() {
    local label="$1" code="$2" expected="$3"
    if [[ ",$expected," == *",$code,"* ]]; then
        echo "OK    $label — $code"
    else
        FAILURES+=("$label returned '$code', expected one of: $expected")
        echo "FAIL  $label — got '$code', expected one of: $expected"
    fi
}

command -v curl >/dev/null 2>&1 || { echo "smoke_jitsi: curl is required" >&2; exit 2; }

# Vhost root — the Jitsi Meet web app shell.
code="$(probe_status "$JITSI_PUBLIC_URL/")"
check_expect "GET $JITSI_PUBLIC_URL/" "$code" "200,204"

# external_api.js — what JitsiStage / the Flutter SDK load.
code="$(probe_status "${JITSI_PUBLIC_URL%/}/external_api.js")"
check_expect "GET external_api.js" "$code" "200"

# XMPP websocket upgrade probe. A plain curl without a real websocket
# handshake will not get 101 through every proxy chain, so 101 (upgraded) or
# 400/404 (endpoint present but rejects a non-websocket GET) both count as
# "reachable"; 000/502/504 mean the vhost cannot reach jitsi-web at all.
code="$(probe_status "${JITSI_PUBLIC_URL%/}/xmpp-websocket" \
    -H "Connection: Upgrade" -H "Upgrade: websocket" \
    -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: c21va2V0ZXN0Y2xpZW50" )"
check_expect "GET /xmpp-websocket (upgrade)" "$code" "101,200,400,404"

# Colibri websocket bridge — same reasoning as above.
code="$(probe_status "${JITSI_PUBLIC_URL%/}/colibri-ws/" \
    -H "Connection: Upgrade" -H "Upgrade: websocket" \
    -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: c21va2V0ZXN0Y2xpZW50" )"
check_expect "GET /colibri-ws/ (upgrade)" "$code" "101,200,400,404"

echo

if [[ ${#FAILURES[@]} -eq 0 ]]; then
    echo "smoke_jitsi: OK — all probes passed"
    exit 0
fi

echo "smoke_jitsi: FAIL — ${#FAILURES[@]} probe(s) failed:"
for f in "${FAILURES[@]}"; do
    printf '  - %s\n' "$f"
done
exit 1
