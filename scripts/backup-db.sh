#!/bin/sh
# =============================================================================
# backup-db.sh — nightly pg_dump for SashaInfinity LMS
# =============================================================================
# Runs INSIDE the backup-cron container (postgres:15-alpine image: ships both
# pg_dump and busybox crond). Scheduled by docker-compose.backup.yml at 02:30.
#
# Manual run from the host:
#   docker exec sasha-backup-cron /scripts/backup-db.sh
#
# Restore a backup (RUN NOTHING UNTIL YOU HAVE A FRESH SAFETY COPY):
#   gunzip -c tutor_lms_<ts>.sql.gz | \
#     docker exec -i sasha_lms-postgres-1 psql -U tutor -d tutor_lms
# =============================================================================
set -eu

PGHOST="${PGHOST:-postgres}"
PGUSER="${PGUSER:-tutor}"
PGDATABASE="${PGDATABASE:-tutor_lms}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
LOG="${LOG:-/var/log/sasha/backup.log}"
NIGHTLY_KEEP_DAYS="${NIGHTLY_KEEP_DAYS:-14}"
WEEKLY_KEEP_DAYS="${WEEKLY_KEEP_DAYS:-56}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

mkdir -p "$BACKUP_DIR/nightly" "$BACKUP_DIR/weekly"

TS=$(date +%Y%m%d_%H%M%S)
OUT="$BACKUP_DIR/nightly/tutor_lms_${TS}.sql.gz"

# --- dump --------------------------------------------------------------------
if pg_dump -h "$PGHOST" -U "$PGUSER" "$PGDATABASE" | gzip > "$OUT"; then
    if [ ! -s "$OUT" ] || ! gzip -t "$OUT" 2>/dev/null; then
        log "FAIL($TS): dump failed integrity check — removing partial file"
        rm -f "$OUT"
        exit 1
    fi
    SIZE=$(du -h "$OUT" | cut -f1)
    ROWS=$(gzip -dc "$OUT" | grep -c '^COPY ' || true)
    log "OK($TS): $OUT ($SIZE, ${ROWS} table dumps)"
else
    log "FAIL($TS): pg_dump exited non-zero"
    rm -f "$OUT"
    exit 1
fi

# --- weekly promotion (Sunday) ------------------------------------------------
if [ "$(date +%u)" = "7" ]; then
    cp "$OUT" "$BACKUP_DIR/weekly/tutor_lms_weekly_${TS}.sql.gz"
    log "OK($TS): promoted to weekly"
fi

# --- retention -----------------------------------------------------------------
find "$BACKUP_DIR/nightly" -name 'tutor_lms_*.sql.gz' -mtime "+$NIGHTLY_KEEP_DAYS" -delete 2>/dev/null || true
find "$BACKUP_DIR/weekly" -name 'tutor_lms_*.sql.gz' -mtime "+$WEEKLY_KEEP_DAYS" -delete 2>/dev/null || true
