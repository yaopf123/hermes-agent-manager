#!/usr/bin/env bash
set -euo pipefail

# Ubuntu/Debian Docker Engine install helper.
# Run on the target server if Docker is not installed yet.

sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
. /etc/os-release
case "${ID:-}" in
  ubuntu)
    DOCKER_DISTRO="ubuntu"
    DOCKER_CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
    ;;
  debian)
    DOCKER_DISTRO="debian"
    DOCKER_CODENAME="${VERSION_CODENAME:-}"
    ;;
  *)
    echo "Unsupported distro: ${PRETTY_NAME:-unknown}. Install Docker manually." >&2
    exit 1
    ;;
esac
if [ -z "$DOCKER_CODENAME" ]; then
  echo "Could not detect OS codename. Install Docker manually." >&2
  exit 1
fi
curl -fsSL "https://download.docker.com/linux/${DOCKER_DISTRO}/gpg" | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${DOCKER_DISTRO} ${DOCKER_CODENAME} stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
