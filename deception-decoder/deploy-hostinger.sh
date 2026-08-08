#!/bin/bash
# ============================================================
# Deploy the Deception Decoder to bullshitdecoder.com
# Run ON the Hostinger VPS as root (or with sudo):
#   curl -fsSL https://raw.githubusercontent.com/nirvanavision-ai/Angies-sandbox/claude/exa-mcp-setup-wvhwwc/deception-decoder/deploy-hostinger.sh | sudo bash
# Idempotent — re-run any time to update.
# ============================================================
set -euo pipefail

DOMAIN="bullshitdecoder.com"
WEBROOT="/var/www/decoder"
BRANCH="claude/exa-mcp-setup-wvhwwc"
BASE="https://raw.githubusercontent.com/nirvanavision-ai/Angies-sandbox/${BRANCH}/deception-decoder"

echo "==> [1/4] Fetching app into $WEBROOT"
mkdir -p "$WEBROOT/assets/css" "$WEBROOT/assets/js/engine" "$WEBROOT/assets/js/ui"
for f in index.html \
         assets/css/decoder.css \
         assets/js/engine/taxonomy.js \
         assets/js/engine/linguistics.js \
         assets/js/engine/analyzer.js \
         assets/js/ui/app.js; do
  curl -fsSL "$BASE/$f" -o "$WEBROOT/$f"
done

echo "==> [2/4] nginx server block"
command -v nginx >/dev/null || { apt-get update -qq && apt-get install -y -qq nginx; }
cat > "/etc/nginx/sites-available/$DOMAIN" << NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;
    root $WEBROOT;
    index index.html;

    # ES modules are refused unless .js is served as JavaScript.
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    location / { try_files \$uri \$uri/ =404; }

    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header Referrer-Policy no-referrer;
}
NGINX
ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"

echo "==> [3/4] Testing and reloading nginx"
nginx -t && systemctl reload nginx

echo "==> [4/4] Live at http://$DOMAIN (once DNS resolves here)"
echo
echo "   DNS: Hostinger panel → $DOMAIN → A records for @ and www → $(curl -fsSL -4 ifconfig.me 2>/dev/null || echo 'this VPS IP')"
echo
echo "   HTTPS:"
echo "     apt-get install -y certbot python3-certbot-nginx"
echo "     certbot --nginx -d $DOMAIN -d www.$DOMAIN"
