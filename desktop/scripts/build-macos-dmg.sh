#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Hermes Agent Manager"
APP_PATH="$ROOT_DIR/src-tauri/target/release/bundle/macos/${APP_NAME}.app"
OUT_DIR="$ROOT_DIR/src-tauri/target/release/bundle/dmg"
OUT_DMG="$OUT_DIR/${APP_NAME}_0.1.0_aarch64.dmg"
STAGE="$(mktemp -d)"

cleanup() {
  rm -rf "$STAGE"
}
trap cleanup EXIT

if [ ! -d "$APP_PATH" ]; then
  echo "Missing app bundle: $APP_PATH" >&2
  echo "Run npm run desktop:build:app first." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
cp -R "$APP_PATH" "$STAGE/${APP_NAME}.app"
ln -s /Applications "$STAGE/Applications"
rm -f "$OUT_DMG"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$OUT_DMG"

echo "Created $OUT_DMG"
