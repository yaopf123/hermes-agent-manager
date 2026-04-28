#!/usr/bin/env bash
set -euo pipefail

# Remote one-line installer for GitHub-hosted deployments.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/yaopf123/hermes-agent-manager/main/scripts/install-remote.sh | bash
# Or override:
#   GITHUB_REPO=yaopf123/hermes-agent-manager GITHUB_REF=main bash install-remote.sh

GITHUB_REPO="${GITHUB_REPO:-yaopf123/hermes-agent-manager}"
GITHUB_REF="${GITHUB_REF:-main}"
INSTALL_TMP="${INSTALL_TMP:-$(mktemp -d)}"

if [ "$GITHUB_REPO" = "yaopf123/hermes-agent-manager" ]; then
  echo "Set GITHUB_REPO=yaopf123/hermes-agent-manager before running this installer." >&2
  echo "Example: curl -fsSL https://raw.githubusercontent.com/yaopf123/hermes-agent-manager/main/scripts/install-remote.sh | GITHUB_REPO=yaopf123/hermes-agent-manager bash" >&2
  exit 2
fi

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}
need curl
need tar
need python3

ARCHIVE_URL="https://github.com/${GITHUB_REPO}/archive/refs/heads/${GITHUB_REF}.tar.gz"
echo "Downloading ${ARCHIVE_URL}"
curl -fsSL "$ARCHIVE_URL" -o "$INSTALL_TMP/source.tar.gz"
tar -xzf "$INSTALL_TMP/source.tar.gz" -C "$INSTALL_TMP"
SRC_DIR="$(find "$INSTALL_TMP" -mindepth 1 -maxdepth 1 -type d | head -1)"
cd "$SRC_DIR"
./scripts/install.sh
