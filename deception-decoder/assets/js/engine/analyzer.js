/**
 * analyzer.js — the pipeline.
 *
 *   text ──▶ signature pass ──▶ overlap resolution ──▶ structural pass
 *        ──▶ family indices ──▶ pattern read ──▶ AnalysisResult
 *
 * Design commitments, all of them deliberate:
 *
 *  1. Runs entirely in the caller's process. No network, no storage, no telemetry.
 *  2. Describes *text*, never people. The output never concludes that anyone is
 *     an abuser — it reports which documented patterns appear in a message, and
 *     hands interpretation back to the reader.
 *  3. Mitigating evidence counts. Repair attempts and hedging pull scores down,
 *     because a tool that can only escalate is not an instrument, it's a mirror.
 *  4. Everything is explainable. Each number traces to matched spans you can see
 *     highlighted in the original text.
 */

import { TAXONOMY, FAMILIES, SAFETY_SIGNALS } from "./taxonomy.js";
import { structuralProfile } from "./linguistics.js";

const SEVERITY_WEIGHT = { 1: 4, 2: 9, 3: 16 };

/** Run every signature and return raw, possibly-overlapping hits. */
function signaturePass(text) {
  const hits = [];
  for (const tactic of TAXONOMY) {
    for (const re of tactic.patterns) {
      re.lastIndex = 0;
      let m;
      while ((m = re.exec(text)) !== null) {
        const matched = m[0];
        if (matched.trim().length >= 4) {
          hits.push({
            start: m.index,
            end: m.index + matched.length,
            text: matched,
            tacticId: tactic.id,
            severity: tactic.severity,
            family: tactic.family,
          });
        }
        if (m.index === re.lastIndex) re.lastIndex++; // zero-width guard
      }
    }
  }
  return hits;
}

/**
 * Resolve overlaps so highlighting stays valid HTML and no phrase is double-counted.
 * Priority: higher severity wins; then the longer span; then the earlier start.
 */
function resolveOverlaps(hits) {
  const sorted = [...hits].sort((a, b) =>
    b.severity - a.severity || (b.end - b.start) - (a.end - a.start) || a.start - b.start);
  const kept = [];
  for (const h of sorted) {
    if (!kept.some(k => h.start < k.end && k.start < h.end)) kept.push(h);
  }
  return kept.sort((a, b) => a.start - b.start);
}

/** Structural findings become pseudo-hits so they appear in the same UI stream. */
function structuralFindings(text, profile) {
  const found = [];
  const push = (id, label, family, severity, why, spans = []) =>
    found.push({ id, label, family, severity, why, spans });

  if (profile.conditionals.length) {
    push("struct-conditional", "Conditional consequence", "coercion", 3,
      `${profile.conditionals.length} "if you… then I/you…" construction${profile.conditionals.length > 1 ? "s" : ""} — ` +
      `the grammatical skeleton of a bargain or threat.`, profile.conditionals);
  }
  if (profile.agencyDeleted.length) {
    push("struct-agency", "Agency deletion", "blame", 2,
      "Harm described with the actor removed — events reported as weather rather than choices.",
      profile.agencyDeleted);
  }
  if (profile.obligation.count >= 2) {
    push("struct-obligation", "Obligation stacking", "obligation", 2,
      `${profile.obligation.count} directives aimed at you ("you should / must / have to").`);
  }
  if (profile.wordCount >= 25 && profile.pronouns.ratio >= 3 && profile.pronouns.you >= 4) {
    push("struct-youfocus", "Second-person saturation", "blame", 1,
      `"You" outnumbers "I" ${profile.pronouns.ratio === Infinity ? "with no first-person ownership at all" :
        `${profile.pronouns.ratio.toFixed(1)} to 1`} — the shape of accusation rather than disclosure.`);
  }
  if (profile.absolutes >= 3) {
    push("struct-absolutes", "Absolutist framing", "escalation", 1,
      `${profile.absolutes} absolutes (always / never / everyone) — closes the door on specifics.`);
  }
  if (profile.intensity.capsWords >= 3 || profile.intensity.stacked >= 2) {
    push("struct-intensity", "Intensity escalation", "escalation", 1,
      "Sustained shouting markers (caps runs, stacked exclamation) used as pressure.");
  }
  return found;
}

/** Weighted 0–100 index per family, damped by message length and repair attempts. */
function familyIndices(hits, structural, profile) {
  const raw = {};
  for (const key of Object.keys(FAMILIES)) raw[key] = 0;

  for (const h of hits) raw[h.family] += SEVERITY_WEIGHT[h.severity];
  for (const s of structural) raw[s.family] += SEVERITY_WEIGHT[s.severity] * 0.6;

  // Longer messages get more chances to match; normalize gently (sqrt, not linear,
  // so a long coercive message doesn't score lower than a short blunt one).
  const lengthDamp = Math.sqrt(Math.max(profile.wordCount, 12) / 45);
  // Genuine repair attempts reduce pressure readings — capped so they can't mask threats.
  const repairRelief = Math.min(0.35, profile.repairs * 0.09);

  const indices = {};
  for (const [key, val] of Object.entries(raw)) {
    const scaled = (val / lengthDamp) * (1 - repairRelief);
    indices[key] = Math.max(0, Math.min(100, Math.round(scaled)));
  }
  return indices;
}

/** A short, plain-language read of the whole message. Never diagnostic. */
function patternRead(hits, indices, profile, safety) {
  const distinct = new Set(hits.map(h => h.tacticId));
  const top = Object.entries(indices).sort((a, b) => b[1] - a[1])[0];
  const composite = Math.round(
    Object.values(indices).reduce((a, b) => a + b, 0) / Object.keys(indices).length * 1.6);

  let band, headline, body;
  if (safety.length) {
    band = "critical";
    headline = "Language consistent with threat is present";
    body = "At least one phrase in this message reads as a threat of harm. That is a safety question before " +
           "it is a communication question. Please read the panel below.";
  } else if (composite >= 55 || distinct.size >= 5) {
    band = "high";
    headline = "Multiple reinforcing pressure patterns";
    body = `${distinct.size} distinct tactic classes appear together. Individually these can be clumsy conflict; ` +
           `layered like this, they function as a system — each one makes the others harder to name.`;
  } else if (composite >= 25 || distinct.size >= 2) {
    band = "moderate";
    headline = "Identifiable pressure, mixed with ordinary conflict";
    body = "Some recognized tactics are present but not saturating. Context and repetition over time matter " +
           "more than any single message — one heated exchange is not a pattern.";
  } else if (distinct.size >= 1) {
    band = "low";
    headline = "Isolated markers, low density";
    body = "A small number of flagged phrases. People under stress reach for these without strategy. " +
           "Worth noticing, not worth alarm on its own.";
  } else {
    band = "clear";
    headline = "No catalogued tactics detected";
    body = "This message doesn't match the patterns in the library. That is not proof it felt fine — " +
           "harm can be conveyed in ways no text analyzer will catch. Your experience of it still counts as data.";
  }

  const mitigating = [];
  if (profile.repairs) mitigating.push(`${profile.repairs} repair attempt${profile.repairs > 1 ? "s" : ""} (apology, concession, acknowledgement)`);
  if (profile.hedges >= 2) mitigating.push(`${profile.hedges} hedged statements — room left for other views`);
  if (profile.pronouns.ratio < 1.2 && profile.wordCount > 25) mitigating.push("balanced I/you ownership");

  return { band, headline, body, composite: Math.min(100, composite), dominantFamily: top?.[0] ?? null, mitigating };
}

/**
 * Analyze a message.
 * @param {string} text
 * @returns {{
 *   hits: Array, structural: Array, indices: Object, profile: Object,
 *   safety: Array, read: Object, tacticsById: Object
 * }}
 */
export function analyze(text) {
  const clean = String(text ?? "");
  if (!clean.trim()) {
    return {
      hits: [], structural: [], indices: {}, profile: structuralProfile(""),
      safety: [], read: { band: "empty", headline: "Nothing to analyze", body: "", composite: 0, mitigating: [] },
      tacticsById: {},
    };
  }

  const profile = structuralProfile(clean);
  const hits = resolveOverlaps(signaturePass(clean));
  const structural = structuralFindings(clean, profile);

  const safety = [];
  for (const re of SAFETY_SIGNALS) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(clean)) !== null) {
      safety.push(m[0]);
      if (m.index === re.lastIndex) re.lastIndex++;
    }
  }

  const indices = familyIndices(hits, structural, profile);
  const read = patternRead(hits, indices, profile, safety);
  const tacticsById = Object.fromEntries(TAXONOMY.map(t => [t.id, t]));

  return { hits, structural, indices, profile, safety, read, tacticsById };
}

/** Plain-text report for export. Deliberately printable and paste-able. */
export function toReport(text, result, { includeSource = true } = {}) {
  const { hits, structural, indices, read, tacticsById, profile } = result;
  const L = [];
  L.push("DECEPTION DECODER — PATTERN REPORT");
  L.push("Generated " + new Date().toLocaleString());
  L.push("Analysis performed locally in the browser. Nothing was uploaded.");
  L.push("");
  L.push("SUMMARY");
  L.push(`  ${read.headline}`);
  L.push(`  ${read.body}`);
  L.push(`  Composite pressure index: ${read.composite}/100`);
  if (read.mitigating.length) L.push(`  Mitigating signals: ${read.mitigating.join("; ")}`);
  L.push("");
  L.push("INDICES");
  for (const [k, v] of Object.entries(indices)) {
    L.push(`  ${String(FAMILIES[k].label).padEnd(22)} ${String(v).padStart(3)}/100`);
  }
  L.push("");
  L.push(`FLAGGED PHRASES (${hits.length})`);
  hits.forEach((h, i) => {
    const t = tacticsById[h.tacticId];
    L.push(`  ${String(i + 1).padStart(2, "0")}. [${t.label}] "${h.text.trim()}"`);
    L.push(`      ${t.mechanism.split(". ")[0]}.`);
    L.push(`      Source: ${t.lineage}`);
  });
  if (structural.length) {
    L.push("");
    L.push(`STRUCTURAL FINDINGS (${structural.length})`);
    structural.forEach(s => L.push(`  · ${s.label}: ${s.why}`));
  }
  L.push("");
  L.push("TEXT PROFILE");
  L.push(`  ${profile.wordCount} words · ${profile.sentenceCount} sentences · ` +
         `you:I ratio ${profile.pronouns.ratio === Infinity ? "∞" : profile.pronouns.ratio.toFixed(1)}`);
  if (includeSource) {
    L.push("");
    L.push("SOURCE TEXT");
    L.push(text.split("\n").map(l => "  " + l).join("\n"));
  }
  L.push("");
  L.push("This report describes patterns in a piece of text. It is not a psychological");
  L.push("assessment, a diagnosis, or evidence about any person's intent or character.");
  return L.join("\n");
}
