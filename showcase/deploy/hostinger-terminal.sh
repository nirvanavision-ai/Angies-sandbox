#!/bin/bash
# ============================================================
# Deploy "The Sovereign Logic Terminal" to bullshitdecoder.com
# Run this ON the Hostinger VPS (browser terminal or SSH), as root
# or a sudo-capable user:
#
#   sudo bash hostinger-terminal.sh
#
# It is idempotent — safe to re-run for updates.
# ============================================================
set -euo pipefail

DOMAIN="bullshitdecoder.com"
WEBROOT="/var/www/bullshitdecoder"
RAW_URL="https://raw.githubusercontent.com/nirvanavision-ai/Angies-sandbox/claude/exa-mcp-setup-wvhwwc/showcase/terminal/index.html"

echo "==> [1/4] Web root: $WEBROOT"
mkdir -p "$WEBROOT"

# Prefer a local copy (if you cloned the repo next to this script); otherwise
# fetch the single-file site straight from GitHub.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../terminal/index.html" ]; then
  echo "==> [2/4] Using local copy from repo checkout"
  cp "$SCRIPT_DIR/../terminal/index.html" "$WEBROOT/index.html"
else
  echo "==> [2/4] Fetching site from GitHub"
  curl -fsSL "$RAW_URL" -o "$WEBROOT/index.html" || {
    echo "!! Could not fetch from GitHub (private repo?). Clone the repo and re-run"
    echo "   this script from inside it: git clone <repo> && sudo bash Angies-sandbox/showcase/deploy/hostinger-terminal.sh"
    exit 1
  }
fi

echo "==> [3/4] nginx server block"
if ! command -v nginx >/dev/null; then
  apt-get update -qq && apt-get install -y -qq nginx
fi
cat > "/etc/nginx/sites-available/$DOMAIN" << NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;
    root $WEBROOT;
    index index.html;
    location / { try_files \$uri \$uri/ =404; }
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header Referrer-Policy no-referrer;
}
NGINX
ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
nginx -t && systemctl reload nginx

echo "==> [4/4] Done — http://$DOMAIN is live (once DNS points here)"
echo
echo "   DNS: in Hostinger's panel for $DOMAIN, set A records for @ and www"
echo "        to this VPS's public IP ($(curl -fsSL -4 ifconfig.me 2>/dev/null || echo 'check hPanel'))."
echo
echo "   HTTPS (recommended, ~30s):"
echo "     apt-get install -y certbot python3-certbot-nginx"
echo "     certbot --nginx -d $DOMAIN -d www.$DOMAIN"
