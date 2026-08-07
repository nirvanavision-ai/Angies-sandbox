# Deploying the Triptych — Netlify & Hostinger Guide

Three static sites, zero build step. Everything in `showcase/` is plain HTML/CSS/JS,
so any static host serves it unmodified. This guide covers **Netlify** (fastest) and a
**Hostinger VPS** with custom domains (full control).

## What you're deploying

```
showcase/
├── index.html            ← landing page (the triptych)
├── terminal/index.html   ← Site 1 · The Sovereign Logic Terminal
├── dungeon/index.html    ← Site 2 · Dungeon of Agreements
├── matrix/index.html     ← Site 3 · The Discrepancy Matrix
├── guide/index.html      ← this guide, styled, at /guide
├── netlify-guide.md      ← this file
└── netlify.toml          ← Netlify config (headers, no build)
```

No `npm install`. No bundler. The only external requests are Google Fonts, and every
page falls back to system fonts if they're unreachable.

## Preview locally (10 seconds)

```bash
cd showcase
python3 -m http.server 8080
# open http://localhost:8080
```

## Option A — Netlify

### A1. Drag & drop (fastest)
1. Go to https://app.netlify.com/drop
2. Drag the `showcase/` folder onto the page.
3. Done. You get a live `https://<random-name>.netlify.app` URL immediately;
   rename it under **Site settings → Change site name**.

### A2. Netlify CLI
```bash
npm install -g netlify-cli
netlify login                      # opens browser for OAuth
cd showcase
netlify deploy --dir=. --prod      # first run walks you through creating the site
```
The CLI prints the live URL when the deploy finishes.

### A3. Continuous deploys from Git
1. **Add new site → Import an existing project** in the Netlify dashboard.
2. Pick this repository; set **Base directory** to `showcase` and leave the
   build command empty (**Publish directory**: `showcase`).
3. Every push to your chosen branch redeploys automatically.

### Custom domains on Netlify
**Domain management → Add a domain** → enter e.g. `bullshitdecoder.com` → follow the
DNS instructions (either point the domain's nameservers at Netlify DNS, or add a
`CNAME`/`A` record at your registrar). HTTPS via Let's Encrypt is automatic.

## Option B — Hostinger VPS (nginx, custom domains per site)

This maps each site to its own domain — e.g. `bullshitdecoder.com` → the Terminal,
`theeggplantfiles.com` → the Matrix — on a single VPS.

### B1. Upload the files
```bash
# from the repo root, on your machine
rsync -avz showcase/ user@YOUR-VPS-IP:/var/www/triptych/
```
(`scp -r showcase/* user@YOUR-VPS-IP:/var/www/triptych/` works too.)

### B2. nginx — one server block per domain
Create `/etc/nginx/sites-available/bullshitdecoder.com`:
```nginx
server {
    listen 80;
    server_name bullshitdecoder.com www.bullshitdecoder.com;
    root /var/www/triptych/terminal;
    index index.html;
    location / { try_files $uri $uri/ =404; }
}
```
And `/etc/nginx/sites-available/theeggplantfiles.com` pointing its `root` at
`/var/www/triptych/matrix` (or `/var/www/triptych` to serve the whole triptych
with the landing page — the sites link to each other with relative paths, so
serving the full folder from one domain is the smoothest experience).

Enable and reload:
```bash
sudo ln -s /etc/nginx/sites-available/bullshitdecoder.com /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/theeggplantfiles.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### B3. Point DNS
In Hostinger's DNS panel for each domain, set an **A record** (`@` and `www`)
to your VPS IP. Propagation is usually minutes.

### B4. Free HTTPS
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d bullshitdecoder.com -d www.bullshitdecoder.com \
                     -d theeggplantfiles.com -d www.theeggplantfiles.com
```
Certbot rewrites the server blocks for TLS and auto-renews.

## Sanity checklist

- [ ] `python3 -m http.server` preview looks right locally
- [ ] All four pages load over the live URL (`/`, `/terminal/`, `/dungeon/`, `/matrix/`, `/guide/`)
- [ ] HTTPS active (padlock) — Netlify: automatic; VPS: certbot
- [ ] Open each site's devtools console: each prints its build iteration log — a quick
      integrity check that scripts loaded and ran

## Notes

- Everything runs client-side. The Terminal's decryption, the Matrix's audio
  "exhibits" (synthesized in WebAudio — no recordings exist), and the Sanity Record
  compiler never transmit anything.
- The Matrix is a labeled forensic *fiction*; keep its disclaimer intact if you fork it.

---
*Built end-to-end by Claude Code — three sites, three measured iteration passes each,
deployed from a repo with no build pipeline at all.*
