#!/usr/bin/env bash
# Proves the ngrok static domain is reserved to the authtoken in ngrok.yml.
set -uo pipefail
cd "$(dirname "$0")/.."
D=$(grep -E '^NGROK_DOMAIN=' .env 2>/dev/null | cut -d= -f2- | tr -d ' ')
[ -z "$D" ] && { echo "✗ NGROK_DOMAIN not set in .env"; exit 1; }

TMP=$(mktemp -d); echo "tunnel-ok" > "$TMP/index.html"
(cd "$TMP" && python3 -m http.server 8011 >/dev/null 2>&1) & SRV=$!
ngrok http --url="$D" 8011 --log=stdout >"$TMP/ng.log" 2>&1 & NG=$!
sleep 6
BODY=$(curl -s --max-time 20 "https://$D" | head -1)
kill $NG $SRV 2>/dev/null

if [ "$BODY" = "tunnel-ok" ]; then
  echo "✓ https://$D is reserved to this authtoken and serving"
  exit 0
fi
echo "✗ https://$D did not serve your content"
grep -iE "ERR_NGROK_[0-9]+|ERROR:" "$TMP/ng.log" | head -3
echo
echo "  ERR_NGROK_320 → the domain is not reserved to THIS authtoken."
echo "    Sign in as the account that owns the domain, then:"
echo "    ngrok config add-authtoken <token>"
echo "  ERR_NGROK_121 → agent too old: ngrok update"
exit 1
