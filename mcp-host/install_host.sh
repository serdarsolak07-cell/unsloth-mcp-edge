#!/usr/bin/env bash
# Ev Ubuntu: venv + systemd user + linger
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${MCP_HOST_VENV:-$HOME/.local/share/mcp-host/venv}"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT="$UNIT_DIR/distributed-mcp-host.service"

echo "==> venv $VENV"
mkdir -p "$(dirname "$VENV")" "$UNIT_DIR" "$HERE"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -U pip
"$VENV/bin/pip" install -r "$HERE/requirements.txt"

if [[ ! -f "$HERE/config.json" ]]; then
  cp "$HERE/config.example.json" "$HERE/config.json"
  echo "config.json olusturuldu. Laptop Tailscale IP yaz."
fi

TOKEN_FILE="$HOME/.config/mcp-bearer.token"
mkdir -p "$(dirname "$TOKEN_FILE")"
if [[ -z "${MCP_BEARER_TOKEN:-}" ]]; then
  if [[ -f "$TOKEN_FILE" ]]; then
    MCP_BEARER_TOKEN="$(cat "$TOKEN_FILE")"
  else
    MCP_BEARER_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    umask 077
    printf '%s\n' "$MCP_BEARER_TOKEN" > "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
    echo "yeni token: $TOKEN_FILE  (aynisini laptopta kullan)"
  fi
fi

cat > "$UNIT" <<EOF
[Unit]
Description=Unsloth MCP host (Studio :8888 + uzak worker)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$HERE
ExecStart=$VENV/bin/python $HERE/main_host.py --config $HERE/config.json
Restart=on-failure
RestartSec=8
Environment=HOME=%h
Environment=MCP_BEARER_TOKEN=$MCP_BEARER_TOKEN
Environment=UNSLOTH_STUDIO_AUTH_TOKEN=${UNSLOTH_STUDIO_AUTH_TOKEN:-}

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
loginctl enable-linger "$USER" || true

echo
echo "========== HOST KURULDU =========="
echo "config : $HERE/config.json"
echo "token  : $TOKEN_FILE"
echo "1) unsloth studio -H 0.0.0.0 -p 8888"
echo "2) export UNSLOTH_STUDIO_AUTH_TOKEN='sk-unsloth-'"
echo "3) config.json laptop 100.x IP"
echo "4) token dosyasini laptopa kopyala"
echo "5) $VENV/bin/python $HERE/main_host.py --once 'ev dizinini listele'"
echo "=================================="
