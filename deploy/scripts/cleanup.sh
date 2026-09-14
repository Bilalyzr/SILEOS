#!/usr/bin/env bash
# =============================================================================
# cleanup.sh — reclaim disk without destroying your rollback path
# =============================================================================
#   deploy/scripts/cleanup.sh                # prune per IMAGE_RETENTION
#   deploy/scripts/cleanup.sh --dry-run      # show what would be removed
#   deploy/scripts/cleanup.sh --keep 5
#
# Called at the end of a successful deploy. It is deliberately conservative,
# because the naive alternative — `docker system prune -af`, as the existing
# build-production.sh does — deletes the previous release's images and with them
# the ability to roll back. Disk is cheap; a rollback you cannot perform during an
# incident is not.
#
# What it will never remove:
#   * an image any container references (running OR stopped)
#   * the images for the currently live release
#   * the images for the most recent IMAGE_RETENTION releases
#
# Also trims deploy logs older than LOG_RETENTION_DAYS.
#
# Exit codes: 0 always, unless arguments are wrong. Housekeeping must not fail a
# deployment, so problems are logged as warnings.
# =============================================================================

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

KEEP="${IMAGE_RETENTION:-3}"
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-30}"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep)    KEEP="${2:-3}"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help) sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) log_error "unknown argument: $1"; exit 2 ;;
    esac
done

log_step "Cleanup (keeping the $KEEP most recent releases)"

# -----------------------------------------------------------------------------
# Tags that must survive, whatever their age.
# -----------------------------------------------------------------------------
protected=()
for colour in blue green; do
    t="$(state_get "${colour}.tag" "")"
    [[ -n "$t" ]] && protected+=("$t")
done

# Images referenced by any container, running or not. `docker ps -a` includes the
# stopped previous colour, which is exactly what rollback depends on.
in_use=()
while IFS= read -r img; do
    [[ -n "$img" ]] && in_use+=("$img")
done < <(docker ps -a --format '{{.Image}}' 2>/dev/null | sort -u)

log_debug "protected tags: ${protected[*]:-none}"
log_debug "images in use:  ${in_use[*]:-none}"

is_protected() {
    local ref="$1" tag="${1##*:}" p u
    for p in "${protected[@]:-}"; do
        [[ -n "$p" && "$tag" == "$p" ]] && return 0
    done
    for u in "${in_use[@]:-}"; do
        [[ "$ref" == "$u" ]] && return 0
    done
    return 1
}

removed=0
kept=0

for svc in "${SERVICES[@]}"; do
    repo="${REGISTRY}/${IMAGE_PREFIX}-${svc}"

    # Newest first, so anything past index KEEP is outside the retention window.
    # A '|' delimiter is used rather than a tab so the pipeline does not depend on
    # a literal tab surviving edits to this file.
    mapfile -t refs < <(
        docker images --filter "reference=${repo}:*" \
                      --format '{{.CreatedAt}}|{{.Repository}}:{{.Tag}}' 2>/dev/null \
            | grep -v '|.*:<none>$' \
            | sort -r \
            | cut -d'|' -f2
    )

    if [[ ${#refs[@]} -eq 0 ]]; then
        log_debug "no images for $repo"
        continue
    fi

    idx=0
    for ref in "${refs[@]}"; do
        idx=$(( idx + 1 ))

        if (( idx <= KEEP )); then
            log_debug "keep (within retention window): $ref"
            kept=$(( kept + 1 ))
            continue
        fi

        if is_protected "$ref"; then
            log_info "keep (in use or live): $ref"
            kept=$(( kept + 1 ))
            continue
        fi

        if [[ "$DRY_RUN" == "1" ]]; then
            log_info "would remove: $ref"
        else
            if docker rmi "$ref" >>"$DEPLOY_LOG" 2>&1; then
                log_info "removed: $ref"
                removed=$(( removed + 1 ))
            else
                # Usually means another tag still points at the same image ID.
                log_debug "could not remove $ref (still referenced) — left alone"
            fi
        fi
    done
done

# -----------------------------------------------------------------------------
# Dangling layers from rebuilds. `--filter dangling=true` only touches untagged
# images with no container referencing them, so this cannot eat a release.
# -----------------------------------------------------------------------------
if [[ "$DRY_RUN" == "1" ]]; then
    dangling_count="$(docker images -f dangling=true -q 2>/dev/null | wc -l | tr -d ' ')"
    log_info "would prune $dangling_count dangling image layer(s)"
else
    if reclaimed="$(docker image prune -f --filter dangling=true 2>>"$DEPLOY_LOG" | tail -n1)"; then
        [[ -n "$reclaimed" ]] && log_info "dangling layers: $reclaimed"
    fi
fi

# Build cache grows without bound on a server that builds every release.
if [[ "$DRY_RUN" != "1" && "${PRUNE_BUILD_CACHE:-true}" == "true" ]]; then
    if bc_out="$(docker builder prune -f --keep-storage "${BUILD_CACHE_KEEP:-5GB}" 2>>"$DEPLOY_LOG" | tail -n1)"; then
        [[ -n "$bc_out" ]] && log_info "build cache: $bc_out"
    else
        log_debug "builder prune unavailable on this docker version — skipped"
    fi
fi

# -----------------------------------------------------------------------------
# Old deploy logs.
# -----------------------------------------------------------------------------
if [[ -d "$LOG_DIR" ]]; then
    old_logs=$(find "$LOG_DIR" -maxdepth 1 -name '*.log' -type f -mtime "+$LOG_RETENTION_DAYS" 2>/dev/null | wc -l | tr -d ' ')
    if (( old_logs > 0 )); then
        if [[ "$DRY_RUN" == "1" ]]; then
            log_info "would delete $old_logs deploy log(s) older than ${LOG_RETENTION_DAYS} days"
        else
            find "$LOG_DIR" -maxdepth 1 -name '*.log' -type f -mtime "+$LOG_RETENTION_DAYS" -delete 2>/dev/null || true
            log_info "deleted $old_logs deploy log(s) older than ${LOG_RETENTION_DAYS} days"
        fi
    fi
fi

log_info "cleanup done: $removed image(s) removed, $kept kept"
exit 0
