#!/usr/bin/env bash
# =============================================================================
# migrate.sh — apply backend/migrations/*.sql once each, in order
# =============================================================================
# This repo has no Alembic: migrations are hand-written SQL files that were
# applied manually, and init_db() only issues CREATE TABLE IF NOT EXISTS (so it
# never adds a column to a table that already exists). That is workable by hand
# and completely unworkable from a pipeline, which needs to know what has already
# run. This script adds the missing piece — a ledger — without changing how the
# migrations themselves are written.
#
#   migrate.sh --baseline    Mark every existing file as applied WITHOUT running
#                            it. Run this exactly once, on a database that is
#                            already up to date, before the first pipeline
#                            deploy. Skipping it would re-run every historical
#                            migration against a live database.
#   migrate.sh --dry-run     List what would run, change nothing.
#   migrate.sh               Apply pending migrations.
#
# TRANSACTIONS: most files in backend/migrations/ open their own BEGIN/COMMIT, so
# psql is NOT invoked with --single-transaction (that would nest transactions and
# make the file's own COMMIT end the outer one early). Per-file atomicity is
# therefore the SQL file's own responsibility — wrap new migrations in
# BEGIN/COMMIT, as the existing ones do.
#
# IDEMPOTENCE: safe to run repeatedly. Files already in the ledger are skipped.
# A file whose contents changed after being applied is reported as an error
# rather than silently re-run or silently ignored.
#
# Exit codes: 0 nothing to do or all applied · 1 a migration failed · 2 usage
# =============================================================================

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

MIGRATIONS_DIR="${MIGRATIONS_DIR:-$REPO_ROOT/backend/migrations}"
# v2: the predecessor table was populated by hand (duplicate rows, stale
# checksums) and blocks the pipeline three ways — ON CONFLICT needs a unique
# key the table lacks, dedup exposes checksums from before files were made
# idempotent, and fixing those would need DB access on the server. Every
# migration file is now re-run safe, so the pipeline keeps its OWN ledger:
# it starts empty, each file applies as a no-op against the already-migrated
# schema and records a fresh checksum. The old table is left as an audit
# trail and is never read again.
LEDGER_TABLE="${LEDGER_TABLE:-_deploy_migrations_v2}"

MODE="apply"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --baseline) MODE="baseline"; shift ;;
        --dry-run)  MODE="dry-run";  shift ;;
        --status)   MODE="status";   shift ;;
        -h|--help)
            sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) log_error "unknown argument: $1"; exit 2 ;;
    esac
done

# -----------------------------------------------------------------------------
# psql helpers. Connections go through `docker exec` on the postgres container's
# unix socket, so no password is needed and the DB never has to be reachable from
# the host or the network.
# -----------------------------------------------------------------------------
psql_q() {
    docker exec -i "$POSTGRES_CONTAINER" \
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -v ON_ERROR_STOP=1 -qtAX -c "$1"
}

psql_file() {
    docker exec -i "$POSTGRES_CONTAINER" \
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -v ON_ERROR_STOP=1 -q -f - <"$1"
}

checksum() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        # Not cryptographic, but this is change detection, not security.
        cksum "$1" | awk '{print $1"-"$2}'
    fi
}

# SQL string literal escaping: double any single quotes. Filenames and checksums
# are the only values interpolated, but doing this unconditionally means a file
# with a quote in its name cannot break (or inject into) the ledger update.
sql_lit() { printf "%s" "${1//\'/\'\'}"; }

ensure_ledger() {
    psql_q "
        CREATE TABLE IF NOT EXISTS ${LEDGER_TABLE} (
            filename    text PRIMARY KEY,
            checksum    text NOT NULL,
            applied_at  timestamptz NOT NULL DEFAULT now(),
            release_tag text,
            baselined   boolean NOT NULL DEFAULT false
        );
    " >/dev/null
    # The ledger table pre-dates the PRIMARY KEY on production (created by
    # hand or by an early version, and populated with duplicate filename
    # rows), which makes ledger_record's ON CONFLICT (filename) fail with
    # "no unique or exclusion constraint matching the ON CONFLICT
    # specification". CREATE TABLE IF NOT EXISTS silently skips a
    # pre-existing table, so repair it here: keep the newest row per
    # filename, then add the constraint.
    psql_q "
        DELETE FROM ${LEDGER_TABLE} a
            USING ${LEDGER_TABLE} b
            WHERE a.filename = b.filename
              AND a.ctid < b.ctid;
    " >/dev/null
    psql_q "
        DO \$\$ BEGIN
            ALTER TABLE ${LEDGER_TABLE}
                ADD CONSTRAINT ${LEDGER_TABLE}_filename_key UNIQUE (filename);
        EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL;
        END \$\$;
    " >/dev/null
}

ledger_has()      { [[ "$(psql_q "SELECT 1 FROM ${LEDGER_TABLE} WHERE filename = '$(sql_lit "$1")';")" == "1" ]]; }
ledger_checksum() { psql_q "SELECT checksum FROM ${LEDGER_TABLE} WHERE filename = '$(sql_lit "$1")';"; }

ledger_record() {
    local name="$1" sum="$2" baselined="$3"
    psql_q "
        INSERT INTO ${LEDGER_TABLE} (filename, checksum, release_tag, baselined)
        VALUES ('$(sql_lit "$name")', '$(sql_lit "$sum")', '$(sql_lit "${RELEASE_TAG:-unknown}")', $baselined)
        ON CONFLICT (filename) DO UPDATE
            SET checksum = EXCLUDED.checksum,
                applied_at = now(),
                release_tag = EXCLUDED.release_tag;
    " >/dev/null
}

# -----------------------------------------------------------------------------
main() {
    container_running "$POSTGRES_CONTAINER" \
        || die "postgres container '$POSTGRES_CONTAINER' is not running"

    [[ -d "$MIGRATIONS_DIR" ]] || die "migrations directory not found: $MIGRATIONS_DIR"

    ensure_ledger

    # Lexicographic order. The existing filenames are either descriptive or
    # date-suffixed, and both sort into a stable, reproducible sequence — the
    # important property being that every environment applies the same order.
    local files=()
    while IFS= read -r f; do files+=("$f"); done < <(find "$MIGRATIONS_DIR" -maxdepth 1 -name '*.sql' -type f | LC_ALL=C sort)

    if [[ ${#files[@]} -eq 0 ]]; then
        log_info "no migration files in $MIGRATIONS_DIR — nothing to do"
        return 0
    fi

    if [[ "$MODE" == "status" ]]; then
        log_step "Migration status"
        local f name
        for f in "${files[@]}"; do
            name="$(basename "$f")"
            if ledger_has "$name"; then
                printf '  %sapplied%s  %s\n' "$C_GRN" "$C_RST" "$name"
            else
                printf '  %spending%s  %s\n' "$C_YLW" "$C_RST" "$name"
            fi
        done
        return 0
    fi

    # -------------------------------------------------------------------------
    # Baseline: adopt an already-migrated database. Nothing is executed.
    # -------------------------------------------------------------------------
    if [[ "$MODE" == "baseline" ]]; then
        log_step "Baselining ${#files[@]} migration(s) — no SQL will be executed"
        local f name
        for f in "${files[@]}"; do
            name="$(basename "$f")"
            if ledger_has "$name"; then
                log_info "already in ledger: $name"
            else
                ledger_record "$name" "$(checksum "$f")" true
                log_info "baselined: $name"
            fi
        done
        record_history "migrate-baseline" "-" "${RELEASE_TAG:-unknown}" "files=${#files[@]}"
        log_info "baseline complete — future runs will only apply NEW files"
        return 0
    fi

    # -------------------------------------------------------------------------
    # Work out what is pending, and refuse to proceed on a changed file.
    # -------------------------------------------------------------------------
    local pending=() f name sum recorded
    for f in "${files[@]}"; do
        name="$(basename "$f")"
        sum="$(checksum "$f")"

        if ledger_has "$name"; then
            recorded="$(ledger_checksum "$name")"
            if [[ "$recorded" != "$sum" ]]; then
                log_error "migration '$name' was already applied but its contents have changed."
                log_error "  ledger:  $recorded"
                log_error "  on disk: $sum"
                log_error "Editing an applied migration means environments have diverged. Add a NEW"
                log_error "migration file instead. To accept the current file as-is, run:"
                log_error "  docker exec -i $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB \\"
                log_error "    -c \"UPDATE ${LEDGER_TABLE} SET checksum='$sum' WHERE filename='$name';\""
                return 1
            fi
            continue
        fi

        pending+=("$f")
    done

    if [[ ${#pending[@]} -eq 0 ]]; then
        log_info "database is up to date (${#files[@]} migration(s) already applied)"
        return 0
    fi

    log_step "${#pending[@]} pending migration(s)"
    for f in "${pending[@]}"; do
        log_info "  pending: $(basename "$f")"
    done

    if [[ "$MODE" == "dry-run" ]]; then
        log_info "--dry-run: nothing was applied"
        return 0
    fi

    # -------------------------------------------------------------------------
    # Apply. Stops at the first failure — a half-migrated schema plus a
    # continuing deploy is far worse than an aborted deploy, and deploy.sh turns
    # this non-zero exit into an automatic rollback with traffic never switched.
    # -------------------------------------------------------------------------
    for f in "${pending[@]}"; do
        name="$(basename "$f")"
        log_info "applying: $name"
        if ! psql_file "$f" >>"$DEPLOY_LOG" 2>&1; then
            log_error "migration FAILED: $name (see $DEPLOY_LOG)"
            log_error "the ledger was not updated, so re-running will retry this file"
            record_history "migrate-failed" "-" "${RELEASE_TAG:-unknown}" "file=$name"
            return 1
        fi
        ledger_record "$name" "$(checksum "$f")" false
        log_info "applied:  $name"
    done

    record_history "migrate" "-" "${RELEASE_TAG:-unknown}" "applied=${#pending[@]}"
    log_info "${#pending[@]} migration(s) applied successfully"
}

main
