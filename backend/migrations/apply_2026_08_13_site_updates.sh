#!/usr/bin/env bash
# 2026-08-13: Consolidated migration runner for the Site Updates batch
# (Issues 1-8 from siteupdates.md).
#
# Applies every new schema change introduced by this branch so the live
# site picks up all the mechanisms in one step. Idempotent — every
# statement uses CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS,
# so re-running is safe.
#
# Usage (from the host, against the docker-compose postgres):
#   bash backend/migrations/apply_2026_08_13_site_updates.sh
#
# Or against a remote DB by exporting DATABASE_URL first.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# New tables / columns added by this batch, in dependency order.
SQL_FILES=(
  "course_video_view_count_2026_08_13.sql"   # Issue 1: per-course video view count
  "watch_sessions_2026_08_13.sql"             # Issue 8: WatchSession table
)

echo "Applying Site Updates migrations (2026-08-13)..."

if [[ -n "${DATABASE_URL:-}" ]]; then
  # Remote DB via DATABASE_URL (psql ignores the host part for libpq).
  for f in "${SQL_FILES[@]}"; do
    echo "  -> $f"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$HERE/$f"
  done
else
  # Default: the docker-compose postgres service.
  for f in "${SQL_FILES[@]}"; do
    echo "  -> $f"
    docker-compose exec -T postgres psql -U tutor -d tutor_lms < "$HERE/$f"
  done
fi

echo "Done. All Site Updates migrations applied."
echo ""
echo "NOTE: the backend's init_db() (Base.metadata.create_all + ensure_schema)"
echo "also reconciles these on boot, so simply restarting the backend is enough"
echo "for a fresh deploy. This script is for bringing an EXISTING live DB in"
echo "line without a full restart."
