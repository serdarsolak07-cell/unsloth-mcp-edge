# unsloth-mcp-edge

Evdeki [Unsloth Studio](https://unsloth.ai) modeline, Tailscale üzerinden Linux laptopun ev dizinini MCP araçlarıyla bağlar.

Home Unsloth Studio talks to a Linux laptop worker over Tailscale (FastMCP Streamable HTTP).

## Ne işe yarar

- Ev PC: Unsloth Studio `http://127.0.0.1:8888/v1`
- Laptop: FastMCP worker `http://100.x:8788/mcp`
- Araçlar: listele, oku, yaz, sil, taşı, kopyala, dar komut listesi (`rm`, `mv`, `cp`, …)

Korunan: `~/.ssh`, `~/.gnupg`, bearer token. Yasak: `sudo`, `dd`, `mkfs`, `shutdown`.

Bu bir resmi Unsloth ürünü değil. Kişisel kullanım.

## Gereksinim

- İki Linux makine (Ubuntu/Debian)
- Evde Unsloth Studio + yüklü model + API anahtarı (`sk-unsloth-...`)
- İkisinde Tailscale aynı kuyruk
- Python 3.11+

## Kurulum

### 1. Ev

```bash
git clone https://github.com/serdarsolak07-cell/unsloth-mcp-edge.git
cd unsloth-mcp-edge/mcp-host
chmod +x install_host.sh && ./install_host.sh
```

`config.json` içine laptop Tailscale IP:

```json
"worker_url": "http://100.x.x.x:8788/mcp",
"worker_health_url": "http://100.x.x.x:8788/health"
```

```bash
export UNSLOTH_STUDIO_AUTH_TOKEN='sk-unsloth-...'
```

`~/.config/mcp-bearer.token` dosyasını laptopa kopyala.

### 2. Laptop

```bash
git clone https://github.com/serdarsolak07-cell/unsloth-mcp-edge.git
cd unsloth-mcp-edge/mcp-worker
# token: ~/.config/mcp-bearer.token
chmod +x install_worker.sh && ./install_worker.sh
curl http://127.0.0.1:8788/health
```

### 3. Dene (ev)

```bash
~/.local/share/mcp-host/venv/bin/python main_host.py --once "ev dizinini listele"
```

Sohbet: `python main_host.py`  / çıkış: `/q`

## Uyarı

Worker ev dizininde silme/taşıma yapabilir. Sadece kendi makinelerinde çalıştır. Token ve Unsloth anahtarını GitHub'a koyma.

## Lisans

MIT
