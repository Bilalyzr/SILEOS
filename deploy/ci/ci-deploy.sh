#!/usr/bin/env bash
# =============================================================================
# ci-deploy.sh — pipeline deploy via the blue-green deploy/ system
# =============================================================================
# Called by .github/workflows/deploy.yml from the self-hosted runner on this
# VPS. Traffic path (since the edge cutover):
#
#     Cloudflare -> host nginx (:3200) -> sasha-edge -> green/blue app tier
#
# This wraps deploy/scripts/deploy.sh (build -> idle colour -> health gate ->
# switch -> verify -> retire) with the pipeline's own safety net:
#
#   0. refuses to run if TWO postgres containers could share the live volume
#   1. fresh pg_dump safety backup
#   2. SQL migrations via the deploy/ ledger (additive-only) against the
#      running sasha-postgres
#   3. deploy/scripts/deploy.sh --tag <sha>   (zero-downtime blue-green)
#
# Flags:
#   --tag SHA        release identifier
#   --skip-migrate   skip step 2
#   --rollback       deploy/scripts/rollback.sh (previous release)
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

LIVE_PG="sasha-postgres"
LEGACY_PG="sasha_lms-postgres-1"
HEALTH_URL="http://localhost:3200/health"

TAG="$(git rev-parse --short HEAD 2>/dev/null || echo manual)"
SKIP_MIGRATE=0
MODE="deploy"

while [ $# -gt 0 ]; do
    case "$1" in
        --tag)          TAG="$2"; shift 2 ;;
        --skip-migrate) SKIP_MIGRATE=1; shift ;;
        --rollback)     MODE="rollback"; shift ;;
        *) echo "unknown flag: $1" >&2; exit 2 ;;
    esac
done

log()  { echo "[ci-deploy $(date -u +%H:%M:%S)] $*"; }
die()  { echo "[ci-deploy ERROR] $*" >&2; exit 1; }

# --- 0. safety gate ----------------------------------------------------------
# The live volume (sasha_lms_postgres_data) must be owned by exactly ONE
# postgres container. Two postgres processes on one data directory is the
# 2026-08-15 incident class — corrupts the cluster.
if docker ps --format '{{.Names}}' | grep -qx "$LEGACY_PG"; then
    die "legacy postgres '$LEGACY_PG' is RUNNING alongside '$LIVE_PG' —
two postgres containers cannot share the live volume. Stop the legacy one:
    docker stop $LEGACY_PG && docker rm $LEGACY_PG"
fi
docker ps --format '{{.Names}}' | grep -qx "$LIVE_PG" \
    || die "live postgres '$LIVE_PG' is not running"

# ============================= rollback mode =================================
if [ "$MODE" = "rollback" ]; then
    log "rollback via deploy/scripts/rollback.sh"
    bash deploy/scripts/rollback.sh --reason "ci rollback"
    bash deploy/scripts/status.sh || true
    exit 0
fi

# ============================= deploy mode ===================================
log "release tag: $TAG"

# --- 1. safety backup --------------------------------------------------------
BK="database/backups/pre-deploy/tutor_lms_${TAG}_$(date -u +%Y%m%d_%H%M%S).sql.gz"
mkdir -p database/backups/pre-deploy
if docker exec "$LIVE_PG" pg_dump -U tutor tutor_lms | gzip > "$BK" && gzip -t "$BK" && [ -s "$BK" ]; then
    log "safety backup: $BK ($(du -h "$BK" | cut -f1))"
else
    die "safety pg_dump failed — aborting before any change"
fi

# --- 2. migrations (ledger, additive-only) -----------------------------------
if [ "$SKIP_MIGRATE" = "1" ]; then
    log "migrations SKIPPED by flag"
else
    log "applying migrations against $LIVE_PG"
    POSTGRES_CONTAINER="$LIVE_PG" \
    POSTGRES_USER=tutor \
    POSTGRES_DB=tutor_lms \
        bash deploy/scripts/migrate.sh
fi

# --- 3. blue-green deploy ----------------------------------------------------
log "running deploy/scripts/deploy.sh --tag $TAG (zero-downtime switch)"
bash deploy/scripts/deploy.sh --tag "$TAG"

# --- 4. final local check through the edge -----------------------------------
sleep 3
if curl -fsS --max-time 10 "$HEALTH_URL" >/dev/null 2>&1; then
    log "DEPLOYED $TAG — edge health OK"
else
    log "WARNING: edge health probe failed after deploy.sh reported success — check status.sh"
    bash deploy/scripts/status.sh || true
    exit 1
fi
