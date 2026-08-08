/**
 * app.js — UI controller.
 *
 * Keeps DOM concerns out of the engine entirely: this module reads the textarea,
 * calls analyze(), and renders. No state is persisted anywhere — reloading the
 * page leaves nothing behind, by design.
 */

import { analyze, toReport } from "../engine/analyzer.js";
import { FAMILIES } from "../engine/taxonomy.js";

const $ = sel => document.querySelector(sel);
const $$ = sel => [...document.querySelectorAll(sel)];
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const SEVERITY_LABEL = { 1: "Concerning", 2: "Serious", 3: "Critical" };

const SAMPLES = [
  {
    name: "Layered pressure",
    text: `I can't believe you'd accuse me of that after everything I've done for you. That never happened — you're remembering it wrong, and honestly everyone agrees you've been paranoid lately. Look what you made me do by pushing me like this. If you really loved me you'd drop it. I promise things will be different this time, just give me one more chance. And what about that time you cancelled on my birthday? Fine. Whatever. Do what you want.`,
  },
  {
    name: "Ordinary conflict",
    text: `I'm frustrated. I asked twice about the weekend and didn't hear back, and I ended up making plans I now have to cancel. I'm sorry I snapped about it on the phone — that wasn't fair and you're right that I could have just said I was annoyed. Can we figure out a better way to handle scheduling?`,
  },
  {
    name: "Control & isolation",
    text: `Why didn't you answer? I checked your phone and saw you were texting your sister again. Those people are toxic and they've always hated me — it should be just us. You need to ask me first before you make plans. If you ever walk out I will make sure you regret it.`,
  },
];

let current = { text: "", result: null };

/* ---------------- rendering ---------------- */

function renderVerdict(result) {
  const { read } = result;
  const v = $("#verdict");
  v.dataset.band = read.band;
  v.innerHTML = `
    <h3>${esc(read.headline)}</h3>
    <p>${esc(read.body)}</p>
    ${read.mitigating.length
      ? `<p class="mitigating"><strong>Also present:</strong> ${esc(read.mitigating.join(" · "))}</p>`
      : ""}
  `;
}

function renderIndices(result) {
  const wrap = $("#indices");
  wrap.innerHTML = Object.entries(FAMILIES).map(([key, fam]) => `
    <div class="index-row">
      <span class="name" title="${esc(fam.blurb)}">${esc(fam.label)}</span>
      <span class="track"><span class="fill" data-target="${result.indices[key] ?? 0}"></span></span>
      <span class="val">${result.indices[key] ?? 0}</span>
    </div>`).join("");
  // animate after paint so the transition actually runs
  requestAnimationFrame(() =>
    $$("#indices .fill").forEach(f => (f.style.width = f.dataset.target + "%")));
}

function renderSafety(result) {
  const panel = $("#safety");
  if (!result.safety.length) { panel.hidden = true; return; }
  panel.hidden = false;
  panel.innerHTML = `
    <h3>Before anything else</h3>
    <p>This message contains language consistent with a threat of harm. Threats made around leaving,
       telling someone, or contacting authorities are treated seriously in danger-assessment research —
       separation is a documented high-risk period, whether or not the threat has been acted on before.</p>
    <p style="margin-top:10px"><strong>You are not overreacting by taking this seriously.</strong></p>
    <ul>
      <li><strong>US:</strong> National DV Hotline — <a href="tel:18007997233">1-800-799-7233</a>, or text START to 88788</li>
      <li><strong>US:</strong> Crisis &amp; suicide lifeline — call or text <a href="tel:988">988</a></li>
      <li><strong>UK:</strong> National DA Helpline — 0808 2000 247</li>
      <li><strong>Canada:</strong> Talk Suicide — 1-833-456-4566</li>
      <li><strong>Australia:</strong> 1800RESPECT — 1800 737 732</li>
      <li>Elsewhere: <a href="https://www.befrienders.org" rel="noopener noreferrer" target="_blank">befrienders.org</a> lists helplines by country</li>
    </ul>
    <p style="margin-top:12px">If you are in immediate danger, contact your local emergency number.</p>`;
}

function renderAnnotated(text, result) {
  const el = $("#annotated");
  let html = "", cursor = 0;
  result.hits.forEach((h, i) => {
    html += esc(text.slice(cursor, h.start));
    const t = result.tacticsById[h.tacticId];
    html += `<mark tabindex="0" role="button" data-sev="${h.severity}" data-i="${i}"
              aria-label="Finding ${i + 1}: ${esc(t.label)}. Open details.">${esc(h.text)}<sup>${i + 1}</sup></mark>`;
    cursor = h.end;
  });
  html += esc(text.slice(cursor));
  el.innerHTML = html || `<span style="color:var(--paper-faint)">No text to display.</span>`;
}

function renderFindings(result) {
  const list = $("#findings");
  const items = [];

  result.hits.forEach((h, i) => {
    const t = result.tacticsById[h.tacticId];
    items.push(`
      <button class="finding" data-sev="${h.severity}" data-i="${i}">
        <span class="top">
          <span class="name">${i + 1}. ${esc(t.label)}</span>
          <span class="sev-chip">${SEVERITY_LABEL[h.severity]}</span>
        </span>
        <span class="quote">“${esc(h.text.trim())}”</span>
        <span class="why">${esc(t.mechanism.split(". ")[0])}.</span>
      </button>`);
  });

  result.structural.forEach(s => {
    items.push(`
      <div class="finding" data-sev="${s.severity}" style="cursor:default">
        <span class="top">
          <span class="name">${esc(s.label)}</span>
          <span class="sev-chip">Structural</span>
        </span>
        <span class="why">${esc(s.why)}</span>
      </div>`);
  });

  $("#findings-count").textContent =
    `${result.hits.length} flagged phrase${result.hits.length === 1 ? "" : "s"}` +
    (result.structural.length ? ` · ${result.structural.length} structural` : "");

  list.innerHTML = items.length ? items.join("") : `
    <div class="finding" style="cursor:default;--sev:var(--accent)">
      <span class="name">Nothing in the library matched</span>
      <span class="why">That doesn't mean the message was fine. It means these particular
        catalogued patterns weren't present. Your own read still counts.</span>
    </div>`;
}

function render() {
  const { text, result } = current;
  renderVerdict(result);
  renderIndices(result);
  renderSafety(result);
  renderAnnotated(text, result);
  renderFindings(result);
  $("#results").hidden = false;
  $("#results").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
}

/* ---------------- drawer ---------------- */

function openDrawer(index) {
  const h = current.result.hits[index];
  if (!h) return;
  const t = current.result.tacticsById[h.tacticId];
  const d = $("#drawer");
  d.dataset.sev = h.severity;
  $("#drawer-body").innerHTML = `
    <span class="chip">${SEVERITY_LABEL[h.severity]} · ${esc(FAMILIES[t.family].label)}</span>
    <h3>${esc(t.label)}</h3>
    <div class="quoted">“${esc(h.text.trim())}”</div>
    <h4>What it does</h4>
    <p>${esc(t.mechanism)}</p>
    ${t.note ? `<div class="note"><strong>Careful:</strong> ${esc(t.note)}</div>` : ""}
    <h4>Where this comes from</h4>
    <p class="lineage">${esc(t.lineage)}</p>
    <h4>Non-reactive replies</h4>
    ${t.scripts.map((s, i) => `
      <div class="script">
        <span class="n">${i + 1}</span>
        <span class="s">${esc(s)}</span>
        <button class="copy" data-copy="${esc(s)}">Copy</button>
      </div>`).join("")}
    <p style="margin-top:14px;font-size:13px;color:var(--paper-faint)">
      These are starting points, not scripts you owe anyone. Flat tone, no justification,
      no counter-attack — brevity is the armour. Edit them until they sound like you.</p>`;
  d.classList.add("open");
  $("#scrim").classList.add("open");
  d.setAttribute("aria-hidden", "false");
  $("#drawer .close").focus();
}

function closeDrawer() {
  $("#drawer").classList.remove("open");
  $("#scrim").classList.remove("open");
  $("#drawer").setAttribute("aria-hidden", "true");
}

/* ---------------- actions ---------------- */

function run() {
  const text = $("#input").value;
  if (!text.trim()) { $("#input").focus(); return; }
  current = { text, result: analyze(text) };
  render();
  // Console trace: the engine's reasoning is inspectable, never hidden.
  console.info("[decoder] analysis complete", {
    flagged: current.result.hits.length,
    structural: current.result.structural.length,
    indices: current.result.indices,
    band: current.result.read.band,
  });
}

function clearAll() {
  current = { text: "", result: null };
  $("#input").value = "";
  $("#results").hidden = true;
  $("#counter").textContent = "0 characters";
  $("#input").focus();
}

function copyReport() {
  if (!current.result) return;
  const report = toReport(current.text, current.result);
  navigator.clipboard?.writeText(report).then(() => {
    const b = $("#copy-report");
    b.textContent = "Copied to clipboard";
    setTimeout(() => (b.textContent = "Copy report"), 1800);
  }).catch(() => {
    // Clipboard blocked (insecure context / permissions): fall back to a download.
    const blob = new Blob([report], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "decoder-report.txt";
    a.click();
    URL.revokeObjectURL(a.href);
  });
}

/* ---------------- wiring ---------------- */

document.addEventListener("DOMContentLoaded", () => {
  const input = $("#input");

  input.addEventListener("input", () => {
    $("#counter").textContent = `${input.value.length.toLocaleString()} characters`;
  });
  input.addEventListener("keydown", e => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); run(); }
  });

  $("#decode").addEventListener("click", run);
  $("#clear").addEventListener("click", clearAll);
  $("#copy-report").addEventListener("click", copyReport);
  $("#print-report").addEventListener("click", () => window.print());

  $("#sample").addEventListener("click", () => {
    const s = SAMPLES[Math.floor(Math.random() * SAMPLES.length)];
    input.value = s.text;
    input.dispatchEvent(new Event("input"));
    $("#sample").textContent = `Example: ${s.name}`;
    setTimeout(() => ($("#sample").textContent = "Try an example"), 2600);
  });

  // Delegated: annotated marks + finding cards both open the drawer.
  document.addEventListener("click", e => {
    const mark = e.target.closest("#annotated mark");
    if (mark) return openDrawer(+mark.dataset.i);
    const card = e.target.closest(".finding[data-i]");
    if (card) return openDrawer(+card.dataset.i);
    const copy = e.target.closest(".copy");
    if (copy) {
      navigator.clipboard?.writeText(copy.dataset.copy);
      copy.textContent = "Copied";
      setTimeout(() => (copy.textContent = "Copy"), 1400);
    }
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeDrawer();
    const mark = e.target.closest?.("#annotated mark");
    if (mark && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); openDrawer(+mark.dataset.i); }
  });
  $("#drawer .close").addEventListener("click", closeDrawer);
  $("#scrim").addEventListener("click", closeDrawer);
});
