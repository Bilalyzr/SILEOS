#!/bin/sh
# =============================================================================
# backup-db.sh — nightly pg_dump for the DEVELOPMENT SashaInfinity LMS stack
# =============================================================================
# Separate from production: dumps the development postgres (service name
# "postgres" on network development_tutor-network), writes dev-only backups
# under development/database/backups/, logs to development/logs/backup.log.
# Dumps are named dev_tutor_lms_* so they can never be confused with the
# production tutor_lms_* files.
#
# Runs INSIDE the dev-backup-cron container (postgres:15-alpine: ships both
# pg_dump and busybox crond). Scheduled by docker-compose.backup.yml at 03:15.
#
# Manual run from the host:
#   docker exec dev-backup-cron /scripts/backup-db.sh
#
# Restore a dev backup (RUN NOTHING UNTIL YOU HAVE A FRESH SAFETY COPY):
#   gunzip -c dev_tutor_lms_<ts>.sql.gz | \
#     docker exec -i development-postgres-1 psql -U tutor -d tutor_lms
# =============================================================================
set -eu

PGHOST="${PGHOST:-postgres}"
PGUSER="${PGUSER:-tutor}"
PGDATABASE="${PGDATABASE:-tutor_lms}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
LOG="${LOG:-/var/log/sasha/backup.log}"
DUMP_PREFIX="${DUMP_PREFIX:-dev_tutor_lms}"
NIGHTLY_KEEP_DAYS="${NIGHTLY_KEEP_DAYS:-14}"
WEEKLY_KEEP_DAYS="${WEEKLY_KEEP_DAYS:-56}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [dev] $*" | tee -a "$LOG"; }

mkdir -p "$BACKUP_DIR/nightly" "$BACKUP_DIR/weekly"

TS=$(date +%Y%m%d_%H%M%S)
OUT="$BACKUP_DIR/nightly/${DUMP_PREFIX}_${TS}.sql.gz"

# --- dump --------------------------------------------------------------------
# Dump to a temp file first. Piping pg_dump straight into gzip masks a pg_dump
# failure behind gzip's success — production lost 15 nights of real backups to
# that bug. This copy keeps the hardened logic.
TMP_DUMP="$OUT.part"
if pg_dump -h "$PGHOST" -U "$PGUSER" "$PGDATABASE" > "$TMP_DUMP" 2>> "$LOG" \
   && gzip -c "$TMP_DUMP" > "$OUT"; then
    rm -f "$TMP_DUMP"
    if [ ! -s "$OUT" ] || ! gzip -t "$OUT" 2>/dev/null; then
        log "FAIL($TS): dump failed integrity check — removing partial file"
        rm -f "$OUT"
        exit 1
    fi
    SIZE=$(du -h "$OUT" | cut -f1)
    ROWS=$(gzip -dc "$OUT" | grep -c '^COPY ' || true)
    if [ "${ROWS:-0}" -eq 0 ]; then
        log "FAIL($TS): dump contains 0 table dumps — database unreachable or empty, NOT backing up as OK"
        rm -f "$OUT"
        exit 1
    fi
    log "OK($TS): $OUT ($SIZE, ${ROWS} table dumps)"
else
    log "FAIL($TS): pg_dump exited non-zero — see errors above"
    rm -f "$TMP_DUMP" "$OUT"
    exit 1
fi

# --- weekly promotion (Sunday) ------------------------------------------------
if [ "$(date +%u)" = "7" ]; then
    cp "$OUT" "$BACKUP_DIR/weekly/${DUMP_PREFIX}_weekly_${TS}.sql.gz"
    log "OK($TS): promoted to weekly"
fi

# --- retention -----------------------------------------------------------------
find "$BACKUP_DIR/nightly" -name "${DUMP_PREFIX}_*.sql.gz" -mtime "+$NIGHTLY_KEEP_DAYS" -delete 2>/dev/null || true
find "$BACKUP_DIR/weekly" -name "${DUMP_PREFIX}_*.sql.gz" -mtime "+$WEEKLY_KEEP_DAYS" -delete 2>/dev/null || true
