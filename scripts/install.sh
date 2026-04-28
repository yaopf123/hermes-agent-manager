#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/ypf/hermes-manager}"
HERMES_DIR="${HERMES_DIR:-/home/ypf/hermes-docker}"
TOKEN="${HERMES_MANAGER_TOKEN:-$(openssl rand -hex 16)}"
SECRET="${HERMES_MANAGER_SECRET:-$(openssl rand -hex 16)}"

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "$@"
  fi
  echo "This installer needs root privileges. Re-run as root." >&2
  exit 1
fi

PUBLIC_HOST="${HERMES_MANAGER_PUBLIC_HOST:-$(hostname -I | awk '{print $1}')}"

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

echo "Hermes Manager installed."
echo "URL: http://$PUBLIC_HOST:8787/?token=$TOKEN"
echo "Edit model presets: $APP_DIR/models.yaml"
echo "Edit compose: $HERMES_DIR/docker-compose.yml"
