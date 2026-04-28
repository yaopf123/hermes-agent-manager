# Hermes Agent Manager

A lightweight web manager for running multiple isolated [Hermes Agent](https://github.com/NousResearch/Hermes-Agent) containers.

It supports:

- Create, start, stop, restart, and delete Hermes agents.
- Per-agent Docker workspace isolation.
- Model preset library with edit/test/apply actions.
- One-click model switching for agents.
- Web QR flow for WeChat binding.
- Weixin media-send patch for PPT/Word/file delivery.
- Custom Office skills for better PPT and Word output.
- Optional offline Docker image loading.

## Quick Install From GitHub

After publishing this repo to GitHub, users can install with:

```bash
curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/scripts/install-remote.sh | GITHUB_REPO=OWNER/REPO bash
```

Recommended with explicit token:

```bash
curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/scripts/install-remote.sh | \
  GITHUB_REPO=OWNER/REPO \
  HERMES_MANAGER_TOKEN="change-me-long-random-token" \
  bash
```

Replace `OWNER/REPO` with your real GitHub repository, for example `yaopf/hermes-agent-manager`.

## Manual Install

```bash
git clone https://github.com/OWNER/REPO.git
cd REPO
HERMES_MANAGER_TOKEN="your-token" ./scripts/install.sh
```

Default install paths:

```text
/home/ypf/hermes-manager
/home/ypf/hermes-docker
```

Override paths:

```bash
APP_DIR=/opt/hermes-manager \
HERMES_DIR=/data/hermes-docker \
HERMES_MANAGER_PUBLIC_HOST=192.168.1.21 \
./scripts/install.sh
```

## Docker

Install Docker Engine on Ubuntu/Debian:

```bash
./docker/install-docker-ubuntu.sh
```

For non-Ubuntu systems, install Docker Engine and Docker Compose plugin using official Docker instructions.

## Offline Image Bundle

Large Docker images should not be committed to git. If you have the optional image archive:

```text
docker-images/hermes-agent_latest.tar.gz
```

Load it with:

```bash
./scripts/load-images.sh
```

Then install:

```bash
./scripts/install.sh
```

Or:

```bash
./scripts/install-offline.sh
```

For GitHub publishing, upload `hermes-agent_latest.tar.gz` to GitHub Releases instead of committing it.

## Configuration

Model presets live here on the server:

```text
/home/ypf/hermes-manager/models.yaml
```

Example presets are in:

```text
examples/models.example.yaml
```

The web UI URL after install is printed by the installer, usually:

```text
http://SERVER_IP:8787/?token=YOUR_TOKEN
```

## Service Management

```bash
sudo systemctl status hermes-manager
sudo systemctl restart hermes-manager
journalctl -u hermes-manager -f
```

Hermes containers:

```bash
cd /home/ypf/hermes-docker
docker compose ps
docker compose up -d
docker compose restart
```

## Security

Hermes Manager controls Docker containers and agent workspaces. Keep it behind a trusted LAN/VPN/reverse proxy and use a strong token.

Do not commit real API keys, `models.yaml`, agent data directories, or Docker image tarballs.
