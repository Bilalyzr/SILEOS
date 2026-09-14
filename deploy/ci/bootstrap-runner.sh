#!/usr/bin/env bash
# =============================================================================
# bootstrap-runner.sh — install the GitHub Actions self-hosted runner
# =============================================================================
# Sets up the CI/CD runner on THIS VPS for github.com/SashaInfinity/Sasha_lms.
# The runner is what makes the pipeline free: unlimited minutes (no 2,000/mo
# private-repo quota), no GHCR storage (images are built locally), and no SSH
# secrets (it is already on the production host).
#
# ONE-TIME SETUP
#   sudo bash deploy/ci/bootstrap-runner.sh <RUNNER_REGISTRATION_TOKEN>
#
#   Get the token (valid 1 hour) from either:
#     https://github.com/SashaInfinity/Sasha_lms/settings/actions/runners/new
#   or, with the gh CLI authenticated:
#     gh api repos/SashaInfinity/Sasha_lms/actions/runners/registration-token \
#       --jq .token
#
# WHAT IT INSTALLS
#   /opt/sasha-ci/actions-runner   runner software (systemd service
#                                  sasha-ci-runner, enabled on boot)
#   /opt/sasha-ci/venv             python venv for backend pytest (healed
#                                  automatically by the quality job)
#   /opt/sasha-ci/buildcache/      docker layer caches for the build job
#
# RUNS AS ROOT — deliberate on this single-admin box: the runner must run
# docker, read the repo's .env files and write the deploy checkout. The repo
# is private (only collaborators can trigger workflows). Revisit if outside
# contributors ever get write access.
#
# MAINTENANCE
#   systemctl status sasha-ci-runner        # is it up?
#   sudo systemctl restart sasha-ci-runner  # after host reboots gone wrong
#   cd /opt/sasha-ci/actions-runner && ./config.sh --remove --token <TOKEN>
#                                           # decommission cleanly
# =============================================================================
set -euo pipefail

REPO_URL="https://github.com/SashaInfinity/Sasha_lms"
RUNNER_DIR="/opt/sasha-ci/actions-runner"
SERVICE_NAME="sasha-ci-runner"

[ $# -ge 1 ] && TOKEN="$1" || { echo "usage: $0 <RUNNER_REGISTRATION_TOKEN>" >&2; exit 2; }
[ "$(id -u)" = 0 ] || { echo "run as root (sudo)" >&2; exit 2; }

command -v systemctl >/dev/null || { echo "systemd required" >&2; exit 2; }

# --- runner software ---------------------------------------------------------
if [ ! -x "$RUNNER_DIR/config.sh" ]; then
    mkdir -p /opt/sasha-ci
    echo ">>> downloading latest runner (linux-x64)"
    VER="$(curl -fsS https://api.github.com/repos/actions/runner/releases/latest | grep -oP '"tag_name":\s*"v\K[0-9.]+' | head -1)"
    [ -n "$VER" ] || { echo "could not resolve runner version" >&2; exit 1; }
    curl -fsSL "https://github.com/actions/runner/releases/download/v${VER}/actions-runner-linux-x64-${VER}.tar.gz" -o /tmp/runner.tgz
    mkdir -p "$RUNNER_DIR"
    tar -xzf /tmp/runner.tgz -C "$RUNNER_DIR"
    rm -f /tmp/runner.tgz
else
    echo ">>> runner software already present at $RUNNER_DIR"
fi

# --- register + install service ------------------------------------------------
if [ ! -f "$RUNNER_DIR/.runner" ]; then
    echo ">>> registering runner"
    cd "$RUNNER_DIR"
    # Root runner is deliberate on this box (see header); this is GitHub's
    # official opt-out for the config.sh sudo refusal.
    RUNNER_ALLOW_RUNASROOT="1" ./config.sh --url "$REPO_URL" --token "$TOKEN" \
        --name sasha-vps-runner --labels sasha-vps --unattended --replace
else
    echo ">>> runner already registered"
fi

echo ">>> installing + starting systemd service"
cd "$RUNNER_DIR"
./svc.sh stop 2>/dev/null || true
./svc.sh install root
./svc.sh start

# --- pipeline scratch dirs ----------------------------------------------------
mkdir -p /opt/sasha-ci/buildcache /opt/sasha-ci/venv

sleep 2
# svc.sh installs the unit under the runner's full name, not $SERVICE_NAME.
UNIT="$(systemctl list-units --type=service --all | awk '/actions\.runner\..*\.service/{print $1; exit}')"
systemctl is-active --quiet "${UNIT:-$SERVICE_NAME}" \
    && echo "OK: runner service running — it should appear as Idle at" \
       "https://github.com/SashaInfinity/Sasha_lms/settings/actions/runners" \
    || { echo "service did not start — check: journalctl -u '${UNIT:-$SERVICE_NAME}' -n 50" >&2; exit 1; }
