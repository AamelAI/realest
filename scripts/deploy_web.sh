#!/usr/bin/env bash
# Build + restart the Next.js UI on the Arbutus VM (admin at /admin).
# Called from CI after rsync; safe to run manually on the app host.
set -euo pipefail
export PATH="/usr/bin:/bin:$HOME/.local/bin:$PATH"
ROOT=/home/ubuntu/base
UNIT_SRC="$ROOT/scripts/systemd/realest-web.service"

if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
  echo "node/npm missing — install Node 22 before deploy_web" >&2
  exit 1
fi

if [[ -f "$UNIT_SRC" ]]; then
  sudo cp "$UNIT_SRC" /etc/systemd/system/realest-web.service
  sudo systemctl daemon-reload
  sudo systemctl enable realest-web.service
fi

cd "$ROOT/web"
npm ci
npm run build

sudo systemctl restart realest-web.service
sleep 2
curl -sf http://127.0.0.1:3000/admin >/dev/null
echo "web ok $(hostname) $(date -u +%Y-%m-%dT%H:%MZ)"
