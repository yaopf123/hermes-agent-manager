#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE_TAR="$ROOT/docker-images/hermes-agent_latest.tar.gz"

if [ ! -f "$IMAGE_TAR" ]; then
  echo "Missing image archive: $IMAGE_TAR" >&2
  exit 1
fi

gzip -dc "$IMAGE_TAR" | docker load
docker image ls nousresearch/hermes-agent:latest
