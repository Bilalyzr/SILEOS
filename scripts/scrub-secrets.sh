#!/usr/bin/bash
# Secret scrub script — removes leaked credentials from git history
# RUN THIS AFTER credential rotation (PAT/keys/smtp/google sessions)

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== SECRET SCRUB START ==="
echo "Repo: $REPO_ROOT"
echo ""

# 1. Safety backup
BACKUP_DIR="$REPO_DIR/../sasha-lms-backup-$(date +%Y%m%d-%H%M%S)"
echo "[1/5] Creating backup at $BACKUP_DIR ..."
git clone --bare . "$BACKUP_DIR"
echo "✓ Backup created"
echo ""

# 2. Install BFG or git-filter-repo if missing
if ! command -v git-filter-repo &> /dev/null; then
    echo "[2/5] Installing git-filter-repo..."
    pip install git-filter-repo
fi
echo "✓ git-filter-repo ready"
echo ""

# 3. Remove files from history
echo "[3/5] Removing secrets from history..."
git filter-repo \
    --invert-paths \
    --path gitTok.md \
    --path .env \
    --path backend/youtube_cookies.txt \
    --force
echo "✓ Secrets removed from all commits"
echo ""

# 4. Clean refs
echo "[4/5] Cleaning refs..."
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
git reflog expire --expire=now --all
echo "✓ Refs cleaned"
echo ""

# 5. Force push (requires --force flag)
if [ "$1" == "--force" ]; then
    echo "[5/5] Force pushing to origin..."
    git push origin --force --all
    git push origin --force --tags
    echo "✓ Force pushed to origin"
else
    echo "[5/5] Dry run complete. Add --force to push."
    echo ""
    echo "To push: $0 --force"
fi

echo ""
echo "=== SECRET SCRUB COMPLETE ==="
echo "Backup at: $BACKUP_DIR"
echo ""
echo "NEXT STEPS:"
echo "1. All collaborators: git fetch --prune --force"
echo "2. All collaborators: git rebase origin/main (or re-clone)"
echo "3. Delete backup after verification: rm -rf $BACKUP_DIR"
