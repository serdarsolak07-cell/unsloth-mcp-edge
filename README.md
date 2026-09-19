# unsloth-mcp-edge

Unsloth Studio on a home PC can use a Linux laptop over Tailscale through an
authenticated FastMCP worker. The worker exposes bounded filesystem tools and
an allowlisted command tool.

## Requirements

- Linux on both machines, Python 3.11+, and Tailscale
- Unsloth Studio with an OpenAI-compatible local endpoint
- A shared random token stored at `~/.config/mcp-bearer.token`

The worker protects SSH/GnuPG credentials by default. It never invokes a
shell, rejects shell operators, and validates paths against configured roots.

## Install

On the home PC:

```bash
git clone https://github.com/serdarsolak07-cell/unsloth-mcp-edge.git
cd unsloth-mcp-edge/mcp-host
chmod +x install_host.sh
./install_host.sh
```

Set `worker_url`, `worker_health_url`, and `unsloth_model` in `config.json`,
then export `UNSLOTH_STUDIO_AUTH_TOKEN`.

On the laptop:

```bash
cd unsloth-mcp-edge/mcp-worker
# Copy the host token to ~/.config/mcp-bearer.token first.
chmod +x install_worker.sh
./install_worker.sh
```

The health endpoint requires the token in the standard HTTP authorization
header. For a local check, construct the header without putting the token in
the shell history:

```bash
TOKEN="$(cat ~/.config/mcp-bearer.token)"
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8788/health
unset TOKEN
```

Run a one-shot request from the home PC:

```bash
~/.local/share/mcp-host/venv/bin/python main_host.py \
  --config config.json --once "ev dizinini listele"
```

## Configuration

`mcp-worker/config.json` controls `allowed_paths`, `protected_paths`, the
command allowlist, command working directory, timeout, output, and read/write
limits. If `allowlist_commands` is omitted, a conservative development set
covering Git, Python/pytest, Node/npm/npx, Make, and Cargo/Rust is used. Keep
the worker reachable only over Tailscale. Do not commit tokens or API keys.

Commands run without a shell, from the configured allowed working directory,
with a finite timeout and bounded captured output. This bounds individual
operations without imposing a tool-call-round limit on the host agent.
`remove` accepts files and non-root directories recursively; copy and move
preserve directory semantics. Protected paths and paths outside allowed roots
remain rejected.

The host does not impose an agent tool-call limit by default:
`max_tool_rounds: null` means the agent can continue planning and using tools
until it returns a final answer. Set a positive integer only when you
deliberately want an orchestration limit; this does not weaken worker security.

### Agent özgürlüğü ve güvenlik

Agent, görev tamamlanana kadar sınırsız planlama ve tool-call döngüsü
kullanabilir. Bu özgürlük, worker güvenlik politikasını devre dışı bırakmaz:

- bearer token doğrulaması zorunludur;
- `allowed_paths` ve `protected_paths` kontrolleri uygulanır;
- shell operatörleri ve tehlikeli komutlar reddedilir;
- allowlist dışındaki komutlar çalıştırılmaz.

Sınırsız agent döngüsü yalnızca orchestration ayarıdır; dosya ve komut
güvenliği worker tarafında kalır.

## Mevcut durum ve doğrulama

Bu sürüm, ana bilgisayardaki agent'in Tailscale üzerinden uzak Linux
worker'i gerçek bir çalışma bilgisayarı gibi kullanması için hazırlanmıştır.
Uzak worker şu işlemleri destekler:

- proje klasörleri ve dosyaları oluşturma, düzenleme, kopyalama, taşıma ve silme;
- recursive klasör silme (izinli kökler içinde);
- Git, Python, pytest, Node/npm/npx, Make ve Cargo/Rust komutları;
- izinli çalışma dizininde test/build/proje komutları çalıştırma;
- sınırsız host tool-call döngüsü (`max_tool_rounds: null`).

Güvenlik kontrolleri korunur: bearer token, izinli/korunan yollar, shell
enjeksiyonu ve tehlikeli komut kontrolleri devrededir.
Komutlar shell olmadan çalıştırılır; timeout ve çıktı boyutu sınırları
tekil işlemleri kontrol eder, agent'in planlama özgürlüğünü kısıtlamaz.

Yerel doğrulama sonuçları:

- 9 test geçti;
- Python ve shell syntax kontrolleri geçti;
- runtime smoke testleri başarılı;
- `git diff --check` başarılı.

Gerçek Tailscale bağlantısı, Unsloth endpoint'i ve iki bilgisayar arasındaki
uçtan uca çalışma henüz kullanıcı makinelerinde test edilmelidir.

## License

MIT
