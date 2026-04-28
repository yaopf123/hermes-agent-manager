#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/ypf/hermes-manager}"
HERMES_DIR="${HERMES_DIR:-/home/ypf/hermes-docker}"
TOKEN="${HERMES_MANAGER_TOKEN:-$(openssl rand -hex 16)}"
SECRET="${HERMES_MANAGER_SECRET:-$(openssl rand -hex 16)}"
PUBLIC_HOST="${HERMES_MANAGER_PUBLIC_HOST:-$(hostname -I | awk '{print $1}')}"
HERMES_AGENT_IMAGE="${HERMES_AGENT_IMAGE:-nousresearch/hermes-agent:latest}"

# Real one-command deployment defaults. Override with false if desired.
INSTALL_DOCKER="${INSTALL_DOCKER:-auto}"          # auto|true|false
PULL_HERMES_IMAGE="${PULL_HERMES_IMAGE:-true}"    # true|false
CREATE_DEFAULT_AGENT="${CREATE_DEFAULT_AGENT:-true}" # true|false
START_DEFAULT_AGENT="${START_DEFAULT_AGENT:-true}"   # true|false

DEFAULT_AGENT_NAME="${DEFAULT_AGENT_NAME:-coder}"
DEFAULT_AGENT_PORT="${DEFAULT_AGENT_PORT:-8642}"
DEFAULT_AGENT_API_KEY="${DEFAULT_AGENT_API_KEY:-hermes-${DEFAULT_AGENT_NAME}-local-key}"
DEFAULT_AGENT_API_MODEL="${DEFAULT_AGENT_API_MODEL:-hermes-${DEFAULT_AGENT_NAME}}"
DEFAULT_AGENT_SOUL="${DEFAULT_AGENT_SOUL:-You are a helpful Hermes agent. Keep work inside /opt/data/workspace unless instructed otherwise.}"

UPSTREAM_BASE_URL="${UPSTREAM_BASE_URL:-${DEFAULT_UPSTREAM_BASE_URL:-https://coding.dashscope.aliyuncs.com/v1}}"
UPSTREAM_MODEL="${UPSTREAM_MODEL:-${DEFAULT_UPSTREAM_MODEL:-qwen3.6-plus}}"
UPSTREAM_API_KEY="${UPSTREAM_API_KEY:-${DEFAULT_UPSTREAM_KEY:-sk-no-key-required}}"
UPSTREAM_PROVIDER="${UPSTREAM_PROVIDER:-custom}"
UPSTREAM_CONTEXT_LENGTH="${UPSTREAM_CONTEXT_LENGTH:-262144}"
UPSTREAM_MAX_TOKENS="${UPSTREAM_MAX_TOKENS:-8192}"

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "$@"
  fi
  echo "This installer needs root privileges. Re-run as root." >&2
  exit 1
fi

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_docker_if_needed() {
  if need_cmd docker && docker compose version >/dev/null 2>&1; then
    systemctl enable --now docker >/dev/null 2>&1 || true
    return
  fi
  if [ "$INSTALL_DOCKER" = "false" ]; then
    echo "Docker is not installed. Install Docker or rerun with INSTALL_DOCKER=true." >&2
    exit 1
  fi
  if [ -x docker/install-docker-ubuntu.sh ]; then
    echo "Installing Docker Engine..."
    bash docker/install-docker-ubuntu.sh
  else
    echo "Docker installer not found. Install Docker manually." >&2
    exit 1
  fi
}

install_docker_if_needed

mkdir -p "$APP_DIR" "$HERMES_DIR/patches"
cp app/app.py "$APP_DIR/app.py"
cp app/wechat_bind.py "$APP_DIR/wechat_bind.py"
cp requirements.txt "$APP_DIR/requirements.txt"
cp patches/weixin.py "$HERMES_DIR/patches/weixin.py"
rm -rf "$HERMES_DIR/custom-skills"
cp -a custom-skills "$HERMES_DIR/custom-skills"
chown -R 10000:10000 "$HERMES_DIR/custom-skills" "$HERMES_DIR/patches" 2>/dev/null || true

if [ ! -f "$APP_DIR/models.yaml" ]; then
  cp examples/models.example.yaml "$APP_DIR/models.yaml"
fi
if [ ! -f "$HERMES_DIR/docker-compose.yml" ]; then
  cp examples/docker-compose.yml "$HERMES_DIR/docker-compose.yml"
fi

if [ "$PULL_HERMES_IMAGE" = "true" ]; then
  echo "Pulling Hermes Agent image: $HERMES_AGENT_IMAGE"
  docker pull "$HERMES_AGENT_IMAGE"
fi

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -U pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

sed \
  -e "s#CHANGE_ME_TOKEN#$TOKEN#g" \
  -e "s#CHANGE_ME_SECRET#$SECRET#g" \
  -e "s#CHANGE_ME_APP_DIR#$APP_DIR#g" \
  -e "s#CHANGE_ME_HERMES_DIR#$HERMES_DIR#g" \
  -e "s#CHANGE_ME_PUBLIC_HOST#$PUBLIC_HOST#g" \
  systemd/hermes-manager.service > /tmp/hermes-manager.service
mv /tmp/hermes-manager.service /etc/systemd/system/hermes-manager.service
systemctl daemon-reload
systemctl enable --now hermes-manager

if [ "$CREATE_DEFAULT_AGENT" = "true" ]; then
  echo "Creating default Hermes agent: $DEFAULT_AGENT_NAME"
  APP_DIR="$APP_DIR" HERMES_DIR="$HERMES_DIR" HERMES_AGENT_IMAGE="$HERMES_AGENT_IMAGE" \
  DEFAULT_AGENT_NAME="$DEFAULT_AGENT_NAME" DEFAULT_AGENT_PORT="$DEFAULT_AGENT_PORT" \
  DEFAULT_AGENT_API_KEY="$DEFAULT_AGENT_API_KEY" DEFAULT_AGENT_API_MODEL="$DEFAULT_AGENT_API_MODEL" \
  DEFAULT_AGENT_SOUL="$DEFAULT_AGENT_SOUL" UPSTREAM_BASE_URL="$UPSTREAM_BASE_URL" \
  UPSTREAM_MODEL="$UPSTREAM_MODEL" UPSTREAM_API_KEY="$UPSTREAM_API_KEY" \
  UPSTREAM_PROVIDER="$UPSTREAM_PROVIDER" UPSTREAM_CONTEXT_LENGTH="$UPSTREAM_CONTEXT_LENGTH" \
  UPSTREAM_MAX_TOKENS="$UPSTREAM_MAX_TOKENS" START_DEFAULT_AGENT="$START_DEFAULT_AGENT" \
  "$APP_DIR/.venv/bin/python" scripts/create-default-agent.py
fi

echo "Hermes Manager installed."
echo "URL: http://$PUBLIC_HOST:8787/?token=$TOKEN"
echo "Default agent API: http://$PUBLIC_HOST:$DEFAULT_AGENT_PORT/v1"
echo "Default agent key: $DEFAULT_AGENT_API_KEY"
echo "Edit model presets: $APP_DIR/models.yaml"
echo "Edit compose: $HERMES_DIR/docker-compose.yml"
