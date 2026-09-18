#!/usr/bin/env bash
# One-shot VM setup for the systemd + Caddy deploy path (Debian/Ubuntu).
# Run this FROM INSIDE the cloned repo, as a user with sudo, on the Azure VM:
#
#   git clone <your-fork-url> /opt/matatu
#   cd /opt/matatu
#   sudo bash backend/deploy/setup.sh
#
# Idempotent — safe to re-run after a `git pull` to pick up code changes.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"

if [ "$EUID" -ne 0 ]; then
  echo "Run with sudo." >&2
  exit 1
fi

echo "== packages =="
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip debian-keyring debian-archive-keyring apt-transport-https curl >/dev/null

if ! command -v caddy >/dev/null 2>&1; then
  echo "== installing caddy =="
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq
  apt-get install -y -qq caddy >/dev/null
else
  echo "== caddy already installed =="
fi

echo "== service user =="
id -u matatu >/dev/null 2>&1 || useradd --system --home "$BACKEND_DIR" --shell /usr/sbin/nologin matatu

echo "== venv + deps =="
if [ ! -d "$BACKEND_DIR/.venv" ]; then
  python3 -m venv "$BACKEND_DIR/.venv"
fi
"$BACKEND_DIR/.venv/bin/pip" install -q --upgrade pip
"$BACKEND_DIR/.venv/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"
chown -R matatu:matatu "$BACKEND_DIR"

echo "== systemd unit =="
cp "$BACKEND_DIR/deploy/matatu-backend.service" /etc/systemd/system/matatu-backend.service
systemctl daemon-reload
systemctl enable --now matatu-backend

echo "== caddy config =="
cp "$BACKEND_DIR/deploy/Caddyfile" /etc/caddy/Caddyfile
systemctl reload caddy || systemctl restart caddy

echo
echo "== status =="
systemctl --no-pager status matatu-backend | head -5
echo
echo "Open TCP 80 and 443 in the Azure NSG for this VM if you haven't."
echo "Then check: curl -s https://20-164-2-5.nip.io/health"
