/**
 * linguistics.js — structural features, independent of the tactic lexicon.
 *
 * Signature matching answers "which known tactics appear?". These functions answer
 * "what shape does this message have?" — the discourse-level properties that show
 * up in coercive communication even when no catchphrase does. They are deliberately
 * simple and explainable: every number here can be traced to a countable thing in
 * the text, which matters when the output is shown to someone whose judgement is
 * already under attack.
 */

const SENT_SPLIT = /(?<=[.!?])\s+|\n+/;

/** Split into sentences, keeping the original character offsets. */
export function sentences(text) {
  const out = [];
  let idx = 0;
  for (const raw of text.split(SENT_SPLIT)) {
    const start = text.indexOf(raw, idx);
    if (raw.trim()) out.push({ text: raw, start, end: start + raw.length });
    idx = start + raw.length;
  }
  return out;
}

export function words(text) {
  return (text.toLowerCase().match(/[a-z']+/g) || []);
}

const ABSOLUTES = ["always", "never", "everyone", "nobody", "no one", "everything", "nothing", "constantly", "every time"];
const HEDGES = ["maybe", "perhaps", "i think", "i feel", "it seems", "possibly", "might", "could be"];
const REPAIR = ["i'm sorry", "im sorry", "i apologize", "you're right", "youre right", "i understand", "fair enough",
                "that makes sense", "thank you", "i hear you", "my fault", "i was wrong"];
const OBLIGATION_MODALS = /\b(?:you (?:should|must|have to|need to|better|ought to)|don'?t you dare)\b/gi;

/**
 * Second-person density: how much of the message is aimed at the listener rather
 * than owned by the speaker. High "you" with low "I" is the linguistic shape of
 * accusation; the inverse is the shape of disclosure.
 */
export function pronounBalance(text) {
  const w = words(text);
  const you = w.filter(t => ["you", "your", "yours", "youre", "you're"].includes(t)).length;
  const i = w.filter(t => ["i", "me", "my", "mine", "im", "i'm"].includes(t)).length;
  const total = Math.max(w.length, 1);
  return {
    you, i,
    youRate: you / total,
    ratio: i === 0 ? (you > 0 ? Infinity : 1) : you / i,
  };
}

export function absoluteCount(text) {
  const lower = " " + text.toLowerCase() + " ";
  return ABSOLUTES.reduce((n, a) => n + (lower.split(a).length - 1), 0);
}

export function hedgeCount(text) {
  const lower = text.toLowerCase();
  return HEDGES.reduce((n, h) => n + (lower.split(h).length - 1), 0);
}

/**
 * Repair attempts — apologies, concessions, acknowledgements. Their presence is a
 * genuine mitigating signal, and counting them keeps the tool from reading every
 * heated message as predatory.
 */
export function repairCount(text) {
  const lower = text.toLowerCase();
  return REPAIR.reduce((n, r) => n + (lower.split(r).length - 1), 0);
}

export function obligationDensity(text) {
  const m = text.match(OBLIGATION_MODALS) || [];
  return { count: m.length, per100: (m.length / Math.max(words(text).length, 1)) * 100 };
}

/** ALL-CAPS shouting and exclamation stacking — intensity markers, not content. */
export function intensityMarkers(text) {
  const caps = (text.match(/\b[A-Z]{3,}\b/g) || []).filter(w => !["OK", "TV", "USA", "PM", "AM"].includes(w));
  const bangs = (text.match(/!/g) || []).length;
  const multiBang = (text.match(/!{2,}/g) || []).length;
  return { capsWords: caps.length, exclamations: bangs, stacked: multiBang };
}

/**
 * Conditional-consequence constructions: "if you X, (then) I/you Y".
 * This is the grammatical skeleton of a threat or a bargain, and it is detectable
 * without knowing which specific words fill the slots.
 */
export function conditionalThreats(text) {
  const re = /\bif you\b[^.!?\n]{3,80}?(?:,|then)?\s*(?:i(?:'?ll| will| am going to)|you(?:'?ll| will))\b[^.!?\n]*/gi;
  return (text.match(re) || []);
}

/**
 * Agency deletion: harm described with the actor removed ("it happened",
 * "things got out of hand"). A well-documented rhetorical move for reporting
 * one's own actions as weather.
 */
export function agencyDeletion(text) {
  const re = /\b(?:things? (?:got|escalated|happened)|it (?:just )?happened|mistakes were made|things got out of hand)\b[^.!?\n]*/gi;
  return (text.match(re) || []);
}

/** Everything at once, for the analyzer. */
export function structuralProfile(text) {
  const sents = sentences(text);
  const w = words(text);
  return {
    charCount: text.length,
    wordCount: w.length,
    sentenceCount: sents.length,
    pronouns: pronounBalance(text),
    absolutes: absoluteCount(text),
    hedges: hedgeCount(text),
    repairs: repairCount(text),
    obligation: obligationDensity(text),
    intensity: intensityMarkers(text),
    conditionals: conditionalThreats(text),
    agencyDeleted: agencyDeletion(text),
    questionCount: (text.match(/\?/g) || []).length,
  };
}
