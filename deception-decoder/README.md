# Deception Decoder

A browser-based tool that analyzes a message for manipulation, coercive-control, and
reasoning-distortion patterns — then shows which phrases matched, what each pattern does,
where the construct comes from in the literature, and how to respond without getting pulled in.

**Everything runs on the user's device.** No server, no API calls, no storage, no analytics,
no accounts. The text never leaves the browser tab.

---

## Why this stack

The brief asked for the *best* stack, not the most fashionable one. For this problem that
means **zero-dependency vanilla ES modules**, and the reasoning is worth stating because it
is a design decision rather than a shortcut:

| Requirement | Consequence |
|---|---|
| **Privacy is the core feature** | Any server-side inference means the most intimate text a person owns is transiting a network. A client-side engine makes the privacy promise *structural* rather than a policy claim — you can verify it with devtools' network tab. |
| **Trauma-informed** | Users may be in crisis on poor connections. 40 KB of JS with no framework boot, no hydration, no CLS. Works offline after first load. |
| **Auditable** | The whole knowledge base is one readable data file. A clinician or survivor advocate can review, correct, or extend it without knowing a build system. |
| **Deployable anywhere** | Static files. Netlify drag-and-drop, Hostinger VPS, S3, GitHub Pages, a USB stick. No build step, no Node runtime in production, nothing to patch. |
| **Long-lived** | No dependency tree means no supply-chain surface and no bit-rot. This will still run in ten years. |

An LLM-backed version would read nuance better. It would also require sending abuse
transcripts to a third party, and that trade is not worth making for this particular tool.
The architecture leaves the door open: `analyze()` is a pure function with a stable return
shape, so an optional server-side enrichment path can be layered on later without touching
the UI.

## Project structure

```
deception-decoder/
├── index.html                     Single page; semantic, accessible markup
├── package.json                   Test + dev scripts only — no runtime dependencies
├── netlify.toml                   Static config + security headers
├── README.md
├── assets/
│   ├── css/decoder.css            Design system (dark, calm, print + reduced-motion aware)
│   └── js/
│       ├── engine/
│       │   ├── taxonomy.js        ★ The knowledge base: 15 tactic classes + safety signals
│       │   ├── linguistics.js     Structural/discourse features (no lexicon needed)
│       │   └── analyzer.js        Pipeline, scoring, report export — pure, DOM-free
│       └── ui/app.js              DOM controller; the only file that touches the page
└── tests/engine.test.js           17 tests, Node's built-in runner, zero deps
```

## How the analysis works

```
text ──▶ signature pass ──▶ overlap resolution ──▶ structural pass
     ──▶ family indices ──▶ pattern read ──▶ result
```

1. **Signature pass** — regex families per tactic class, written to match clauses so
   highlights stay tight.
2. **Overlap resolution** — higher severity wins, then longer span, then earlier position.
   Guarantees valid highlight markup and no double-counting.
3. **Structural pass** — properties that appear even when no catchphrase does:
   conditional-consequence constructions (`if you… then I'll…`), agency deletion
   ("things got out of hand"), obligation stacking, second-person saturation,
   absolutist framing, intensity markers.
4. **Family indices** — severity-weighted 0–100 scores across six families
   (reality distortion, blame transfer, coercive pressure, manufactured debt,
   emotional escalation, argument distortion). Normalized by √length so long messages
   don't inflate, and **damped by repair attempts** — apologies and concessions
   genuinely lower the reading, capped so they can never mask a threat.
5. **Pattern read** — a plain-language summary in one of five bands
   (clear / low / moderate / high / critical), plus any mitigating signals found.
6. **Safety layer** — separate from scoring. Explicit harm, weapon references, self-harm
   leverage, and retaliation threats conditioned on *leaving or telling* (the documented
   peak-risk windows) surface a crisis-resource panel above everything else.

### Research grounding

Each tactic carries a `lineage` field shown to the user verbatim, so the tool never asserts
authority it hasn't earned: Freyd (DARVO), Stark (coercive control), Sweet (sociology of
gaslighting), Bancroft (entitlement/externalized responsibility), Gottman & Levenson
(contempt), Walker (cycle theory), Braiker and Forward (emotional blackmail), Rogers and
Assor (conditional regard), the Duluth model, and standard treatments of informal fallacies.

> **Note on sources:** the Google Drive collections and Gemini gems supplied in the original
> brief could not be retrieved (the build environment's network policy blocks non-development
> hosts, and Drive links require account authentication). The taxonomy is therefore built on
> the published literature above. `taxonomy.js` is designed to be extended — adding a tactic
> is appending one object; no other file changes.

## Ethical design constraints

These are enforced in code, not just intention:

- **Describes text, never people.** No output concludes anyone is an abuser. The word
  "diagnosis" appears only in the disclaimer denying it.
- **Mitigating evidence counts.** A tool that can only escalate is a mirror, not an
  instrument. Repair attempts and hedging reduce scores; the sample set includes an
  ordinary-conflict message that correctly reads as clear.
- **A clear result is not absolution.** The empty-state copy says so explicitly: harm can be
  conveyed in ways no text analyzer catches, and the user's own read still counts.
- **Calm visual language.** No sirens, no red alerts, no gamified score. Users arrive with
  their judgement already under attack; the interface aims for steadiness.
- **Crisis resources are unmissable** when danger language appears, and correct for multiple
  countries.

## Accessibility

WCAG-minded throughout: skip link, semantic landmarks, `aria-live` results region, modal
dialog semantics with focus management and Escape-to-close, keyboard-operable highlights
(`Enter`/`Space`), visible focus rings, AA-contrast palette, full `prefers-reduced-motion`
path, and a print stylesheet so a report can be saved as PDF.

## Develop & test

```bash
cd deception-decoder
npm test          # 17 engine tests, Node's built-in runner — no install needed
npm run dev       # http://localhost:8080  (ES modules need http://, not file://)
```

There is no build step. Edit a file, reload the page.

## Deploy

### Netlify — drag & drop
Drag the `deception-decoder/` folder onto <https://app.netlify.com/drop>. Live in seconds.

### Netlify — CLI
```bash
npm install -g netlify-cli
netlify login
cd deception-decoder
netlify deploy --dir=. --prod
```

### Netlify — continuous deploys
Import the repo, set **Base directory** `deception-decoder`, leave the build command empty,
**Publish directory** `deception-decoder`. Every push redeploys.

### Hostinger VPS + custom domain (e.g. bullshitdecoder.com)

```bash
# 1 — upload
rsync -avz deception-decoder/ user@YOUR-VPS-IP:/var/www/decoder/

# 2 — nginx server block: /etc/nginx/sites-available/bullshitdecoder.com
server {
    listen 80;
    server_name bullshitdecoder.com www.bullshitdecoder.com;
    root /var/www/decoder;
    index index.html;
    location / { try_files $uri $uri/ =404; }

    # .js must be served as JavaScript or ES modules will be refused
    include /etc/nginx/mime.types;

    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header Referrer-Policy no-referrer;
}

# 3 — enable + reload
sudo ln -s /etc/nginx/sites-available/bullshitdecoder.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 4 — DNS: A records for @ and www → your VPS IP (Hostinger DNS panel)

# 5 — HTTPS
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d bullshitdecoder.com -d www.bullshitdecoder.com
```

**One deployment gotcha:** the app uses native ES modules, so it must be served over
`http(s)://` — opening `index.html` from the filesystem will fail CORS. Any static host
handles this; only double-clicking the file locally does not.

### Post-deploy check
- [ ] Page loads over HTTPS
- [ ] Paste text → **Decode message** → highlights appear
- [ ] Click a highlight → drawer opens with mechanism, lineage, 3 scripts
- [ ] Devtools **Network** tab shows no request carrying the pasted text — this is the
      privacy claim, verified rather than promised

## Extending the taxonomy

```js
// assets/js/engine/taxonomy.js
{
  id: "your-tactic",
  label: "Human-readable name",
  family: "reality",              // reality | blame | coercion | obligation | escalation | rhetoric
  severity: 2,                    // 1 concerning · 2 serious · 3 critical
  lineage: "Author (Year) — what the construct is called in the literature.",
  mechanism: "What it does to the listener, in plain language.",
  patterns: [/regex/gi],          // must be global + case-insensitive (enforced by tests)
  scripts: ["…", "…", "…"],       // exactly three (enforced by tests)
  note: "Optional caveat to prevent over-reading.",
}
```

Run `npm test` — the suite validates structure, uniqueness, flags, and score bounds.

## License & disclaimer

This is a pattern-recognition aid, not a psychological assessment, diagnosis, lie detector,
or evidence about anyone's character or intent. Language is ambiguous and context is
everything. If you are in danger, contact a local emergency number or a domestic-violence
service; the app lists several.

Built with Claude Code.
