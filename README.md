# Hermes Agent Manager

A lightweight web manager for running multiple isolated [Hermes Agent](https://github.com/NousResearch/Hermes-Agent) containers.

It supports:

- Real one-command install: Docker check/install, image pull, manager setup, default agent creation, and agent start.
- Create, start, stop, restart, and delete Hermes agents.
- Per-agent Docker workspace isolation.
- Model preset library with edit/test/apply actions.
- One-click model switching for agents.
- Web QR flow for WeChat binding.
- Weixin media-send patch for PPT/Word/file delivery.
- Custom Office skills for better PPT and Word output.
- Optional offline Docker image loading.
- Desktop installer preview for Windows/macOS/Linux packaging.

## Desktop App

The first desktop version lives in `desktop/`. It is a Tauri app that can:

- deploy Hermes Manager to a remote Linux server over SSH;
- run local install on Linux/macOS;
- create and start the default Hermes agent during install;
- test the Manager URL;
- open the web Manager after deployment;
- show installer logs in the desktop window.

Development:

```bash
cd desktop
npm install
npm run build
npm run desktop:dev
```

Build a native package on the current OS:

```bash
cd desktop
npm run desktop:build
```

On macOS this builds a `.app` and creates a simple `.dmg`. You can run those steps manually too:

```bash
cd desktop
npm run desktop:build:app
npm run desktop:build:macos-dmg
```

Configured bundle targets:

```text
Windows: NSIS .exe
macOS: .dmg
Linux: .deb / .rpm / AppImage
```

Remote deployment from the desktop app requires `ssh`. Password mode also requires `sshpass` on the desktop machine. Key-based SSH works without `sshpass`.

## Quick Install From GitHub

This installs Docker when needed, pulls `nousresearch/hermes-agent:latest`, installs Hermes Manager, creates one default isolated Hermes agent, and starts it.

```bash
curl -fsSL https://raw.githubusercontent.com/yaopf123/hermes-agent-manager/main/scripts/install-remote.sh | GITHUB_REPO=yaopf123/hermes-agent-manager bash
```

Recommended cloud-model install:

```bash
curl -fsSL https://raw.githubusercontent.com/yaopf123/hermes-agent-manager/main/scripts/install-remote.sh | \
  GITHUB_REPO=yaopf123/hermes-agent-manager \
  HERMES_MANAGER_TOKEN="change-me-long-random-token" \
  HERMES_MANAGER_PUBLIC_HOST="SERVER_IP" \
  DEFAULT_AGENT_NAME="coder" \
  DEFAULT_AGENT_PORT="8642" \
  UPSTREAM_BASE_URL="https://coding.dashscope.aliyuncs.com/v1" \
  UPSTREAM_MODEL="qwen3.6-plus" \
  UPSTREAM_API_KEY="sk-your-key" \
  bash
```

Local llama.cpp install example:

```bash
curl -fsSL https://raw.githubusercontent.com/yaopf123/hermes-agent-manager/main/scripts/install-remote.sh | \
  GITHUB_REPO=yaopf123/hermes-agent-manager \
  HERMES_MANAGER_TOKEN="change-me-long-random-token" \
  HERMES_MANAGER_PUBLIC_HOST="SERVER_IP" \
  DEFAULT_AGENT_NAME="coder" \
  DEFAULT_AGENT_PORT="8642" \
  UPSTREAM_BASE_URL="http://SERVER_IP:8080/v1" \
  UPSTREAM_MODEL="Qwen3.6-35B-A3B-Q4_K_M.gguf" \
  UPSTREAM_API_KEY="sk-no-key-required" \
  UPSTREAM_CONTEXT_LENGTH="131072" \
  bash
```

## Manual Install

```bash
git clone https://github.com/yaopf123/hermes-agent-manager.git
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

## Install Options

Common environment variables:

```bash
HERMES_MANAGER_TOKEN=change-me
HERMES_MANAGER_PUBLIC_HOST=SERVER_IP
APP_DIR=/home/ypf/hermes-manager
HERMES_DIR=/home/ypf/hermes-docker
HERMES_AGENT_IMAGE=nousresearch/hermes-agent:latest
INSTALL_DOCKER=auto        # auto|true|false
PULL_HERMES_IMAGE=true
CREATE_DEFAULT_AGENT=true
START_DEFAULT_AGENT=true
DEFAULT_AGENT_NAME=coder
DEFAULT_AGENT_PORT=8642
DEFAULT_AGENT_API_KEY=hermes-coder-local-key
DEFAULT_AGENT_API_MODEL=hermes-coder
UPSTREAM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
UPSTREAM_MODEL=qwen3.6-plus
UPSTREAM_API_KEY=sk-...
UPSTREAM_CONTEXT_LENGTH=262144
UPSTREAM_MAX_TOKENS=8192
```

Set `CREATE_DEFAULT_AGENT=false` if you only want the web manager and prefer to create agents later from the UI.

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

Default agent after install:

```bash
curl http://SERVER_IP:8642/v1/models \
  -H "Authorization: Bearer hermes-coder-local-key"
```

## Security

Hermes Manager controls Docker containers and agent workspaces. Keep it behind a trusted LAN/VPN/reverse proxy and use a strong token.

Do not commit real API keys, `models.yaml`, agent data directories, or Docker image tarballs.
