#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${MCP_WORKER_VENV:-$HOME/.local/share/mcp-worker/venv}"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$(dirname "$VENV")" "$UNIT_DIR"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -U pip
"$VENV/bin/pip" install -r "$HERE/requirements.txt"
if [[ ! -f "$HERE/config.json" ]]; then cp "$HERE/config.example.json" "$HERE/config.json"; fi
TOKEN_FILE="$HOME/.config/mcp-bearer.token"
if [[ ! -f "$TOKEN_FILE" && -z "${MCP_BEARER_TOKEN:-}" ]]; then
  echo "Missing $TOKEN_FILE (copy the host token there)." >&2
  exit 1
fi
cat > "$UNIT_DIR/distributed-mcp-worker.service" <<EOF
[Unit]
Description=Unsloth MCP worker
After=network-online.target
[Service]
WorkingDirectory=$HERE
ExecStart=$VENV/bin/python $HERE/worker_server.py --config $HERE/config.json
Environment=HOME=%h
Environment=MCP_TOKEN_FILE=$TOKEN_FILE
Restart=on-failure
[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now distributed-mcp-worker.service
echo "Worker installed. Use the token in the HTTP authorization header to check /health."
