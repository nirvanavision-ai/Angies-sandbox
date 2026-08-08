/**
 * build-standalone.js — bundles the modular source into one portable HTML file.
 *
 * Output: standalone.html — works from file:// with no server, no modules, no
 * network. Useful for emailing to someone, putting on a USB stick, or hosting
 * anywhere that can't serve .js with the right MIME type.
 *
 * Run: npm run build
 *
 * Implementation note worth keeping: the replacements use *function* callbacks.
 * A plain string replacement would interpret `$$`, `$&`, and `` $` `` inside the
 * bundled JavaScript as special patterns and splice the document into itself —
 * which silently produced a duplicate-declaration crash the first time round.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const read = f => readFileSync(join(ROOT, f), "utf8");

/** Strip ES module syntax so the sources can be concatenated into one classic script. */
const strip = f => read(f)
  .replace(/^\s*import\s+[^;]+;\s*$/gm, "")
  .replace(/^export\s+/gm, "");

const bundle = [
  "/* Deception Decoder — single-file build. Modular source lives in deception-decoder/ */",
  "(function () {",
  strip("assets/js/engine/taxonomy.js"),
  strip("assets/js/engine/linguistics.js"),
  strip("assets/js/engine/analyzer.js"),
  strip("assets/js/ui/app.js"),
  "})();",
].join("\n\n");

const html = read("index.html")
  .replace('<link rel="stylesheet" href="assets/css/decoder.css">',
           () => `<style>\n${read("assets/css/decoder.css")}\n</style>`)
  .replace('<script type="module" src="assets/js/ui/app.js"></script>',
           () => `<script>\n${bundle}\n</script>`);

writeFileSync(join(ROOT, "standalone.html"), html);

// Sanity check: catches the $-splice bug described above if it ever returns.
const decls = (html.match(/const \$ = sel/g) || []).length;
if (decls !== 1) {
  console.error(`✗ build corrupt: expected 1 '$' declaration, found ${decls}`);
  process.exit(1);
}
console.log(`✓ standalone.html — ${(html.length / 1024).toFixed(1)} KB, self-contained`);
