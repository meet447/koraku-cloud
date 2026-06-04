# VPS deploy (API + host Caddy)

Host the Koraku **Python API** at `https://api.koraku.chipling.xyz` with Docker Compose (API + Redis) and **system Caddy** for HTTPS. The API listens on **`127.0.0.1:8000`**.

## Prerequisites

1. **DNS:** `A` record `api.koraku.chipling.xyz` → your VPS public IP (e.g. `144.24.98.146`).
2. **Firewall:** allow inbound **80** and **443** (Oracle Cloud security list + `ufw` if enabled).
3. **Docker** on the VPS: [Install Docker Engine](https://docs.docker.com/engine/install/ubuntu/) + Compose plugin.

## One-time server setup

SSH in (replace key path if needed):

```bash
ssh -i /path/to/ssh-key.key ubuntu@YOUR_VPS_IP
```

Install Docker (Ubuntu):

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${VERSION_CODENAME:-$VERSION_ID}") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker "$USER"
# log out and back in so group membership applies
```

Clone the repo:

```bash
sudo mkdir -p /opt/koraku
sudo chown "$USER:$USER" /opt/koraku
git clone https://github.com/meet447/koraku-cloud.git /opt/koraku/koraku-cloud
cd /opt/koraku/koraku-cloud
```

Create production `.env` from the example and fill secrets (Supabase, LLM keys, etc.):

```bash
cp .env.example .env
nano .env
```

**Important for a public API:**

| Variable | Example / note |
|----------|----------------|
| `CORS_ALLOWED_ORIGINS` | Your web app origin(s), e.g. `https://koraku.chipling.xyz` |
| `REQUIRE_AUTH_FOR_CHAT` | `true` |
| `SUPABASE_*` | JWT secret, URL, service role key |
| `REDIS_URL` | Leave unset in `.env` — Compose sets `redis://redis:6379/0` |
| `HEALTH_DETAIL_TOKEN` | Long random string for ops |

## Caddy (system service)

Replace the site block in `/etc/caddy/Caddyfile` with [`caddy-site.snippet`](./caddy-site.snippet) (or append if empty):

```bash
sudo tee /etc/caddy/Caddyfile > /dev/null <<'EOF'
api.koraku.chipling.xyz {
	encode gzip zstd
	reverse_proxy 127.0.0.1:8000
}
EOF
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## Deploy / update

```bash
cd /opt/koraku/koraku-cloud
git pull
docker compose -f deploy/vps/docker-compose.yml --env-file .env up -d --build
```

Check logs:

```bash
docker compose -f deploy/vps/docker-compose.yml logs -f api
```

Verify (after DNS propagates):

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS https://api.koraku.chipling.xyz/health
```

## Docker-only Caddy

If this host does **not** already run Caddy on 80/443, use [`Caddyfile`](./Caddyfile) with a separate compose overlay (not included by default on the shared OCI VM).

## Resource notes (1 GB OCI shape)

- Keep `WEB_CONCURRENCY=1` (set in Compose).
- Optional swap: `sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`

## Point your web app at this API

If the Next.js app runs elsewhere, set:

```bash
KORAKU_BACKEND_URL=https://api.koraku.chipling.xyz
```

Browsers should still prefer the BFF (`/koraku-api/*`); direct API access needs matching `CORS_ALLOWED_ORIGINS`.
