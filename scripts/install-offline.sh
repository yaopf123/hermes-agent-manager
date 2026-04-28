#!/usr/bin/env bash
set -euo pipefail

# Offline-ish install helper: assumes Docker Engine is already installed.
# It loads the bundled Hermes Docker image first, then runs the normal manager installer.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
./scripts/load-images.sh
./scripts/install.sh
