/**
 * Engine tests — run with:  node --test tests/
 * Zero dependencies; uses Node's built-in test runner and native ES modules.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { analyze, toReport } from "../assets/js/engine/analyzer.js";
import { TAXONOMY, FAMILIES } from "../assets/js/engine/taxonomy.js";
import { structuralProfile, conditionalThreats, repairCount } from "../assets/js/engine/linguistics.js";

test("taxonomy is internally consistent", () => {
  const ids = new Set();
  for (const t of TAXONOMY) {
    assert.ok(t.id && !ids.has(t.id), `duplicate or missing id: ${t.id}`);
    ids.add(t.id);
    assert.ok(FAMILIES[t.family], `${t.id} has unknown family ${t.family}`);
    assert.ok([1, 2, 3].includes(t.severity), `${t.id} bad severity`);
    assert.equal(t.scripts.length, 3, `${t.id} must offer exactly 3 scripts`);
    assert.ok(t.lineage.length > 10, `${t.id} missing lineage`);
    for (const re of t.patterns) {
      assert.ok(re.flags.includes("g"), `${t.id} pattern must be global`);
      assert.ok(re.flags.includes("i"), `${t.id} pattern must be case-insensitive`);
    }
  }
});

test("empty and whitespace input is safe", () => {
  for (const input of ["", "   ", "\n\n", null, undefined]) {
    const r = analyze(input);
    assert.equal(r.hits.length, 0);
    assert.equal(r.read.band, "empty");
  }
});

test("detects DARVO", () => {
  const r = analyze("How dare you accuse me of that. You're the one who lies constantly.");
  assert.ok(r.hits.some(h => h.tacticId === "darvo"));
});

test("detects gaslighting and reports the reality family", () => {
  const r = analyze("That never happened. You're remembering it wrong, you're being paranoid again.");
  assert.ok(r.hits.some(h => h.tacticId === "gaslighting"));
  assert.ok(r.indices.reality > 0);
});

test("detects threats and raises the safety flag", () => {
  const r = analyze("If you leave I will make sure you regret it.");
  assert.ok(r.hits.some(h => h.tacticId === "threat"));
  assert.ok(r.safety.length > 0, "separation-conditioned threat should trip a safety signal");
  assert.equal(r.read.band, "critical");
});

test("safety signals cover violence, weapons, and self-harm leverage", () => {
  for (const t of [
    "I'll hurt you if you keep this up.",
    "If I can't have you nobody will.",
    "Maybe I should just get the gun and show you.",
    "I'll kill myself if you walk out that door.",
  ]) {
    assert.ok(analyze(t).safety.length > 0, `missed safety signal in: ${t}`);
  }
});

test("ordinary conflict does not trip the safety panel", () => {
  for (const t of [
    "I'm frustrated that you were late again.",
    "You always leave the dishes and it drives me up the wall.",
    "If you go to the party I'll just stay home and watch a movie.",
  ]) {
    assert.equal(analyze(t).safety.length, 0, `false safety positive on: ${t}`);
  }
});

test("detects isolation and monitoring", () => {
  const r1 = analyze("Your friends are toxic and they hate me. Stop talking to your sister.");
  assert.ok(r1.hits.some(h => h.tacticId === "isolation"));
  const r2 = analyze("I checked your phone. Why didn't you answer? You need to ask me first.");
  assert.ok(r2.hits.some(h => h.tacticId === "monitoring"));
});

test("neutral warm text produces a clear read", () => {
  const text = "Hey, I'm sorry about last night — you were right that I interrupted you. " +
               "Can we talk after dinner? I'd like to hear how you saw it.";
  const r = analyze(text);
  assert.equal(r.read.band, "clear");
  assert.ok(r.read.mitigating.length > 0, "apology should register as mitigating");
});

test("repair attempts damp the composite score", () => {
  const harsh = "You always do this. It's your fault. You're being ridiculous.";
  const withRepair = harsh + " I'm sorry, you're right, that was unfair of me. I understand.";
  assert.ok(analyze(withRepair).read.composite < analyze(harsh).read.composite);
});

test("highlight spans never overlap and map back to the source", () => {
  const text = "You're the one who's crazy. After everything I've done for you, you owe me. " +
               "If you tell anyone I'll make sure everyone knows what you did. That never happened anyway.";
  const { hits } = analyze(text);
  assert.ok(hits.length >= 3);
  for (let i = 1; i < hits.length; i++) {
    assert.ok(hits[i].start >= hits[i - 1].end, "spans must not overlap");
  }
  for (const h of hits) assert.equal(text.slice(h.start, h.end), h.text);
});

test("structural pass catches conditionals without lexicon help", () => {
  assert.equal(conditionalThreats("If you go out tonight I will not be here tomorrow.").length, 1);
  const r = analyze("If you keep bringing this up I'll stop paying for the car.");
  assert.ok(r.structural.some(s => s.id === "struct-conditional"));
});

test("second-person saturation is detected on accusatory text", () => {
  const r = analyze(
    "You never listen to what anyone says and you always turn everything around on other people, " +
    "you make everyone uncomfortable and you refuse to see how you behave in front of your friends.");
  assert.ok(r.structural.some(s => s.id === "struct-youfocus"));
});

test("indices stay within 0-100 for extreme input", () => {
  const brutal = ("You're the one who's crazy. It's your fault. You owe me. If you leave I'll destroy you. " +
                  "That never happened. Everyone agrees you're insane. ").repeat(12);
  const r = analyze(brutal);
  for (const v of Object.values(r.indices)) {
    assert.ok(v >= 0 && v <= 100, `index out of range: ${v}`);
  }
  assert.ok(r.read.composite <= 100);
});

test("length normalization keeps short blunt messages meaningful", () => {
  const short = analyze("It's your fault. You made me do it.");
  assert.ok(short.read.composite > 0, "a short coercive message must not score zero");
});

test("report export contains findings, lineage, and the no-diagnosis disclaimer", () => {
  const text = "After everything I've done for you, you owe me. That never happened.";
  const report = toReport(text, analyze(text));
  assert.match(report, /PATTERN REPORT/);
  assert.match(report, /Freyd|Sweet|Braiker|Forward|Bancroft|Stark/);
  assert.match(report, /not a psychological/i);
  assert.match(report, /Nothing was uploaded/);
});

test("profile counts are accurate", () => {
  const p = structuralProfile("I am here. You are there! Are you okay?");
  assert.equal(p.sentenceCount, 3);
  assert.equal(p.questionCount, 1);
  assert.equal(repairCount("I'm sorry. You're right. Thank you."), 3);
});
