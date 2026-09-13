#!/usr/bin/env bash
# Manual deploy on the Arbutus VM after code has been synced (CI uses rsync).
# Prefer pushing to main — GitHub Actions deploys automatically.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd /home/ubuntu/base
uv sync
sudo systemctl restart realest.service
sleep 2
curl -sf http://127.0.0.1:8000/health
echo
echo "restarted $(hostname) $(date -u +%Y-%m-%dT%H:%MZ)"
