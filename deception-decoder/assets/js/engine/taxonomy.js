/**
 * taxonomy.js — the analytical knowledge base.
 *
 * Each entry is a *tactic class*: a named pattern of interpersonal influence
 * documented in the clinical, forensic, or rhetorical literature. Everything the
 * engine can say about a message ultimately comes from this file, which makes it
 * the single place to audit, extend, or localize the app's claims.
 *
 * Field contract
 * ---------------
 *   id         stable slug (used in URLs, exports, tests — do not rename casually)
 *   label      human name shown in the UI
 *   family     grouping used for the index bars: reality | blame | coercion |
 *              obligation | escalation | rhetoric
 *   severity   1 concerning · 2 serious · 3 critical (drives colour + weighting)
 *   lineage    where the construct comes from — shown to the user verbatim so the
 *              app never asserts authority it hasn't earned
 *   mechanism  what the tactic *does* to the listener, in plain language
 *   patterns   RegExp signatures. Written to match a clause, not a whole sentence,
 *              so highlights stay tight. Always global + case-insensitive.
 *   scripts    non-reactive ("gray rock") replies — flat, brief, unarguable
 *   note       optional caveat surfaced in the drawer to prevent over-reading
 *
 * Extending: append an object. No other file needs to change — the analyzer,
 * scoring, and UI all iterate this array.
 */

export const FAMILIES = {
  reality:    { label: "Reality distortion", blurb: "Pressure on your memory, perception, and judgement." },
  blame:      { label: "Blame transfer",     blurb: "Responsibility relocated from speaker to listener." },
  coercion:   { label: "Coercive pressure",  blurb: "Compliance extracted by attaching a cost to refusal." },
  obligation: { label: "Manufactured debt",  blurb: "Obligation created from past acts, then called in." },
  escalation: { label: "Emotional escalation", blurb: "Contempt, absolutes, and intensity used as leverage." },
  rhetoric:   { label: "Argument distortion", blurb: "Logical structure bent so the point can't be reached." },
};

export const TAXONOMY = [
  {
    id: "darvo",
    label: "DARVO",
    family: "blame",
    severity: 3,
    lineage: "Freyd (1997); Harsey & Freyd (2020) — Deny, Attack, Reverse Victim and Offender.",
    mechanism:
      "When confronted, the speaker denies the behaviour, attacks the credibility of the person raising it, " +
      "and re-casts themselves as the injured party. The conversation stops being about what happened and " +
      "becomes about your cruelty in mentioning it. Research finds exposure to DARVO increases the " +
      "confronter's self-blame.",
    patterns: [
      /you'?re (?:the one|actually the one|really the one)\b[^.!?\n]*/gi,
      /(?:how dare you|i can'?t believe you(?:'?d| would)?\s*(?:accuse|say|think))[^.!?\n]*/gi,
      /(?:i'?m the (?:real )?victim|you'?re attacking me|now i'?m the bad guy|so i'?m the villain)[^.!?\n]*/gi,
      /you'?re (?:the )?(?:abusive|toxic|controlling) one\b[^.!?\n]*/gi,
      /(?:this is|that'?s) why (?:i|nobody) (?:can'?t|don'?t) (?:talk to|trust) you\b[^.!?\n]*/gi,
    ],
    scripts: [
      "I hear that you see it differently. The thing I raised still happened, and it still needs addressing.",
      "I'm not going to debate who the victim is. I'm telling you what I observed and what I need.",
      "We can talk about your feelings separately. Right now I'm talking about [the specific event].",
    ],
  },
  {
    id: "gaslighting",
    label: "Reality denial / gaslighting",
    family: "reality",
    severity: 3,
    lineage: "Sweet (2019), sociology of gaslighting; Stern (2007); Stark (2007) on 'crazy-making'.",
    mechanism:
      "Repeated assertion that documented events did not happen, or happened entirely differently, until you " +
      "outsource the question of what is real to the speaker. The damage isn't a single lie — it's the slow " +
      "transfer of epistemic authority away from your own memory.",
    patterns: [
      /that (?:never|literally never) happened\b[^.!?\n]*/gi,
      /you'?re (?:imagining|making (?:that|this|it) up|remembering (?:it|that) wrong|misremembering|inventing)[^.!?\n]*/gi,
      /(?:you'?re|you are|your) (?:being )?(?:crazy|insane|delusional|paranoid|unstable|unhinged|losing it)\b[^.!?\n]*/gi,
      /i never said (?:that|anything like that)\b[^.!?\n]*/gi,
      /(?:that'?s not what (?:i said|happened)|you (?:always )?twist (?:my words|everything))\b[^.!?\n]*/gi,
      /(?:you need help|you should see (?:a therapist|someone)|get help)\b[^.!?\n]*/gi,
    ],
    scripts: [
      "My memory of it is clear, and I'm confident in it.",
      "We remember it differently. I'm going to trust my own record.",
      "I'm not willing to argue about whether it happened. It did.",
    ],
    note:
      "A single disagreement about facts is not gaslighting — people genuinely misremember. The pattern " +
      "matters: repetition over time, paired with attacks on your stability.",
  },
  {
    id: "blame-transfer",
    label: "Blame transfer",
    family: "blame",
    severity: 3,
    lineage: "Bancroft (2002) on entitlement and externalized responsibility.",
    mechanism:
      "The speaker's choices are re-described as involuntary reactions to you. Their actions become your " +
      "fault; the logical endpoint is a person who is never the author of anything they do.",
    patterns: [
      /(?:this is|it'?s|that'?s) (?:all |really )?your fault\b[^.!?\n]*/gi,
      /look what you (?:made me do|make me do)\b[^.!?\n]*/gi,
      /you (?:drove|pushed|forced) me to (?:this|it|do)\b[^.!?\n]*/gi,
      /if you (?:hadn'?t|didn'?t|weren'?t)[^.!?\n]{0,60}?(?:i wouldn'?t|i would never|none of this)[^.!?\n]*/gi,
      /you made me (?:do|say|feel|act)\b[^.!?\n]*/gi,
    ],
    scripts: [
      "Your actions are your choices. Mine are mine.",
      "I'm responsible for what I did. I'm not responsible for what you did.",
      "We can discuss my part separately. It doesn't erase yours.",
    ],
  },
  {
    id: "threat",
    label: "Threat / intimidation",
    family: "coercion",
    severity: 3,
    lineage: "Stark (2007), coercive control; Duluth Model — 'Using Intimidation' and 'Using Coercion and Threats'.",
    mechanism:
      "Compliance is purchased with a stated cost for refusal: abandonment, exposure, escalation, financial " +
      "harm, or harm to people, pets, or property. Coercive control research treats credible threat as the " +
      "load-bearing structure of entrapment — the threat does not need to be carried out to work.",
    patterns: [
      /if you (?:leave|go|tell|call|report|don'?t)[^.!?\n]{0,70}?(?:i'?ll|i will|you'?ll (?:regret|be sorry|lose))[^.!?\n]*/gi,
      /you'?ll (?:regret|be sorry|never see|lose everything)\b[^.!?\n]*/gi,
      /i'?ll (?:make sure|see to it|tell everyone|ruin|destroy)\b[^.!?\n]*/gi,
      /(?:no one|nobody) (?:else )?(?:will|would) (?:ever )?(?:love|want|believe|put up with) you\b[^.!?\n]*/gi,
      /(?:you'?ll never|i'?ll take) (?:get|see|keep) the (?:kids|children|house|money)\b[^.!?\n]*/gi,
      /don'?t make me\b[^.!?\n]*/gi,
    ],
    scripts: [
      "I've heard the threat. It doesn't change my decision.",
      "I won't negotiate under pressure. When it stops, we can talk.",
      "That statement is noted. I'm ending this conversation now.",
    ],
    note: "If any threat involves physical harm, weapons, or your children, please read the safety panel below.",
  },
  {
    id: "isolation",
    label: "Isolation pressure",
    family: "coercion",
    severity: 3,
    lineage: "Stark (2007); Duluth Model — 'Using Isolation'. A core, under-recognized control mechanism.",
    mechanism:
      "Contact with the people who could corroborate your account is restricted, discouraged, or poisoned. " +
      "Isolation is what makes every other tactic durable: with no outside reference points, the speaker " +
      "becomes the only available witness to reality.",
    patterns: [
      /(?:your|those) (?:friends?|family|mother|sister|brother)[^.!?\n]{0,40}?(?:toxic|bad for you|hate me|poison|turning you)[^.!?\n]*/gi,
      /(?:you (?:don'?t|shouldn'?t) need|why do you (?:even )?need) (?:them|anyone else|other (?:friends|people))\b[^.!?\n]*/gi,
      /(?:stop|quit) (?:talking to|seeing|texting)\b[^.!?\n]*/gi,
      /(?:it'?s|its) (?:just )?(?:me and you|us against)\b[^.!?\n]*/gi,
      /who (?:are you (?:talking|texting) to|were you with)\b[^.!?\n]*/gi,
    ],
    scripts: [
      "My relationships aren't up for negotiation.",
      "I'm keeping the people in my life. That isn't a threat to us.",
      "I'll decide who I spend time with.",
    ],
  },
  {
    id: "monitoring",
    label: "Surveillance & rule-setting",
    family: "coercion",
    severity: 2,
    lineage: "Stark (2007) on micro-regulation of daily life; Duluth 'Using Male Privilege' / rule-making.",
    mechanism:
      "Ordinary autonomy is converted into something requiring permission, accounting, or proof. The content " +
      "of any single rule matters less than the accumulating principle that your day is subject to review.",
    patterns: [
      /(?:you (?:need|have) to (?:ask|check with|tell) me|ask me first)\b[^.!?\n]*/gi,
      /(?:send|show) me (?:a )?(?:proof|pic|screenshot|your location)\b[^.!?\n]*/gi,
      /(?:why (?:didn'?t|haven'?t) you (?:answer|reply|call))\b[^.!?\n]*/gi,
      /i (?:checked|saw|looked at) your (?:phone|messages|email|location)\b[^.!?\n]*/gi,
      /you'?re not (?:allowed|going) to\b[^.!?\n]*/gi,
    ],
    scripts: [
      "I'm not going to account for my whereabouts.",
      "I'll share what I choose to share.",
      "Checking my phone isn't something I consent to.",
    ],
  },
  {
    id: "obligation",
    label: "Guilt leverage / manufactured debt",
    family: "obligation",
    severity: 2,
    lineage: "Braiker (2004) on emotional blackmail; Forward (1997), 'FOG' — fear, obligation, guilt.",
    mechanism:
      "Past favours, sacrifices, or suffering are converted into a ledger you are permanently behind on, and " +
      "payment is taken in compliance. Care is reframed as credit extended.",
    patterns: [
      /after (?:all|everything) (?:i'?ve|i have|i) (?:done|sacrificed|given|put up with)[^.!?\n]*/gi,
      /(?:i gave up|i sacrificed|i lost)[^.!?\n]{0,50}? for you\b[^.!?\n]*/gi,
      /you owe me\b[^.!?\n]*/gi,
      /if you (?:really |actually |truly )?(?:loved|cared about) me,? you'?d\b[^.!?\n]*/gi,
      /(?:a good|any (?:decent|real)) (?:partner|wife|husband|person|friend|mother|father) would\b[^.!?\n]*/gi,
      /after everything i'?ve been through\b[^.!?\n]*/gi,
    ],
    scripts: [
      "I appreciate what you've done. It doesn't obligate me to agree to this.",
      "Care isn't a debt. I'm still saying no.",
      "I hear that you're disappointed. My answer stands.",
    ],
  },
  {
    id: "minimization",
    label: "Minimization",
    family: "reality",
    severity: 2,
    lineage: "Bancroft (2002); minimization/denial cluster in batterer-intervention literature.",
    mechanism:
      "The event stays exactly the same size; only your right to react to it is reduced. 'It was a joke' and " +
      "'you're too sensitive' relocate the problem from the act to your response to the act.",
    patterns: [
      /(?:it was|i was) (?:just|only) (?:a joke|joking|kidding|teasing|playing)\b[^.!?\n]*/gi,
      /you'?re (?:too|being|so) (?:sensitive|dramatic|emotional|defensive)\b[^.!?\n]*/gi,
      /(?:calm down|relax|chill out|settle down)\b[^.!?\n]*/gi,
      /you'?re (?:overreacting|blowing (?:this|it) (?:way )?out of proportion|making a big deal)\b[^.!?\n]*/gi,
      /it'?s not (?:that|a) big (?:of a )?deal\b[^.!?\n]*/gi,
      /(?:get over it|let it go|move on already)\b[^.!?\n]*/gi,
    ],
    scripts: [
      "It mattered to me. I'm not debating the size of it.",
      "Jokes land as jokes. That didn't. I'm telling you how it landed.",
      "My reaction is proportionate to my experience of it.",
    ],
  },
  {
    id: "contempt",
    label: "Contempt & character attack",
    family: "escalation",
    severity: 2,
    lineage: "Gottman & Levenson (1992) — contempt is the single strongest predictor of relationship dissolution.",
    mechanism:
      "The disagreement is escalated from behaviour ('you did X') to identity ('you ARE X'). Character attacks " +
      "cannot be resolved by any change in behaviour, which is precisely what makes them useful for control.",
    patterns: [
      /you'?re (?:such )?(?:a |an )?(?:idiot|moron|stupid|pathetic|worthless|useless|disgusting|selfish|lazy)\b[^.!?\n]*/gi,
      /(?:what'?s wrong with you|grow up|act your age)\b[^.!?\n]*/gi,
      /you (?:always|never) [^.!?\n]{0,50}/gi,
      /(?:typical|classic) you\b[^.!?\n]*/gi,
      /(?:nobody|no one) else (?:has a problem with|would put up with)\b[^.!?\n]*/gi,
    ],
    scripts: [
      "I'm not going to continue a conversation with name-calling in it.",
      "Tell me the behaviour you want changed. I won't discuss my character.",
      "I'll come back to this when we can talk without insults.",
    ],
    note:
      "'Always/never' absolutes are flagged as escalation, not proof of intent — stressed people use them too. " +
      "Weight them by how often they appear.",
  },
  {
    id: "withdrawal",
    label: "Punitive withdrawal",
    family: "coercion",
    severity: 2,
    lineage: "Stonewalling in Gottman's 'Four Horsemen'; silent treatment as coercive discipline (Williams, 2001).",
    mechanism:
      "Connection itself becomes the currency: affection, communication, or basic acknowledgement is withdrawn " +
      "until you correct course. It teaches that disagreement costs the relationship.",
    patterns: [
      /(?:i'?m|im) done (?:talking|with this|with you)\b[^.!?\n]*/gi,
      /don'?t (?:bother|even) (?:talking|speaking|texting) (?:to )?me\b[^.!?\n]*/gi,
      /(?:fine|whatever)\.?\s*(?:do what you want|forget it|have it your way)\b[^.!?\n]*/gi,
      /(?:lose my number|we'?re done|forget i said anything)\b[^.!?\n]*/gi,
      /(?:i (?:guess|suppose) i'?ll just|maybe i should just) (?:leave|go|disappear)\b[^.!?\n]*/gi,
    ],
    scripts: [
      "I'm open to talking when you're ready to engage.",
      "Silence won't change my position, but I'm here when you want to discuss it.",
      "I'll take the space too. My point stands for when we resume.",
    ],
  },
  {
    id: "future-faking",
    label: "Future faking",
    family: "obligation",
    severity: 2,
    lineage: "Walker (1979), cycle-of-abuse 'reconciliation' phase; hoovering in coercive-control literature.",
    mechanism:
      "A vivid promise of change is issued to defuse the present consequence — with no mechanism, timeline, or " +
      "track record attached. The promise itself is the payment.",
    patterns: [
      /i (?:promise|swear)[^.!?\n]{0,40}?(?:i'?ll|i will|things will|it will|never again)[^.!?\n]*/gi,
      /(?:things|it) will be different (?:this time|now|from now on)\b[^.!?\n]*/gi,
      /i'?m (?:going to|gonna) change\b[^.!?\n]*/gi,
      /(?:just )?give me (?:one more|another) chance\b[^.!?\n]*/gi,
      /(?:this will )?never happen again\b[^.!?\n]*/gi,
    ],
    scripts: [
      "I'll believe the change when I see it sustained, not when I hear it promised.",
      "What is the concrete plan, and what happens if it doesn't hold?",
      "Past promises are my data. I'm deciding on the data.",
    ],
  },
  {
    id: "triangulation",
    label: "Triangulation / manufactured consensus",
    family: "rhetoric",
    severity: 2,
    lineage: "Bowen family-systems theory; appeal to popularity (argumentum ad populum).",
    mechanism:
      "Absent third parties are recruited as a jury. 'Everyone thinks' converts an unverifiable claim into " +
      "social pressure and leaves you outnumbered inside your own conversation.",
    patterns: [
      /every(?:one|body) (?:thinks|says|agrees|knows|can see)\b[^.!?\n]*/gi,
      /even (?:your|my) (?:friends?|family|mom|mother|sister|brother|therapist) (?:thinks?|says?|agrees?)\b[^.!?\n]*/gi,
      /people are (?:talking|saying|noticing)\b[^.!?\n]*/gi,
      /(?:no one|nobody) else (?:thinks|has a problem)\b[^.!?\n]*/gi,
    ],
    scripts: [
      "I'm talking with you, not a committee. What do you say?",
      "If someone has a concern, they can raise it with me directly.",
      "Consensus isn't evidence. Let's stay on what actually happened.",
    ],
  },
  {
    id: "deflection",
    label: "Circular deflection / whataboutism",
    family: "rhetoric",
    severity: 1,
    lineage: "Tu quoque and red-herring fallacies; 'kitchen-sinking' in couples research.",
    mechanism:
      "The topic is never allowed to stabilize. Counter-accusations and ancient history rotate fast enough " +
      "that the original question dies of exhaustion rather than resolution.",
    patterns: [
      /(?:what about|whatabout) (?:you|the time|when you|that time)\b[^.!?\n]*/gi,
      /(?:this is|that'?s) just like (?:that time|when you)\b[^.!?\n]*/gi,
      /(?:oh )?so now (?:i'?m|you'?re|it'?s|suddenly)\b[^.!?\n]*/gi,
      /(?:you'?re one to talk|look who'?s talking|pot calling)\b[^.!?\n]*/gi,
      /why are we (?:even )?talking about this\b[^.!?\n]*/gi,
    ],
    scripts: [
      "That's a separate topic. I'll finish this one first.",
      "We can schedule that conversation. Today's question is still open.",
      "I notice we've changed subjects. Returning to my question: …",
    ],
  },
  {
    id: "conditional-love",
    label: "Conditional regard",
    family: "obligation",
    severity: 2,
    lineage: "Rogers (1959) on conditions of worth; Assor et al. (2004) on parental conditional regard.",
    mechanism:
      "Acceptance is made contingent and revocable — love arrives as a reward for compliance and is withdrawn " +
      "as a penalty. Over time this trains self-monitoring rather than self-knowledge.",
    patterns: [
      /i (?:could|would) love you (?:more |again )?if\b[^.!?\n]*/gi,
      /(?:i'?ll stay|we'?ll be fine|i'?ll forgive you) (?:if|as long as|once) you\b[^.!?\n]*/gi,
      /(?:you'?re lucky|be grateful) (?:i|that i)\b[^.!?\n]*/gi,
      /(?:this is )?your (?:last|final) chance\b[^.!?\n]*/gi,
    ],
    scripts: [
      "Love with conditions attached isn't something I can negotiate for.",
      "I'd rather know where I actually stand than earn my way back.",
      "I'm not going to perform to keep this.",
    ],
  },
  {
    id: "false-dilemma",
    label: "False dilemma",
    family: "rhetoric",
    severity: 1,
    lineage: "Classical informal fallacy; Walton (1992) on argumentation schemes.",
    mechanism:
      "A landscape of options is compressed into two, one of which is unacceptable. The narrowing is the " +
      "argument — it does the work before you get a chance to think.",
    patterns: [
      /(?:either|its either|it'?s either) [^.!?\n]{0,50}? or [^.!?\n]{0,50}/gi,
      /(?:if you'?re not|you'?re either) (?:with me|on my side)\b[^.!?\n]*/gi,
      /(?:you|we) (?:have|has) no (?:other )?choice\b[^.!?\n]*/gi,
      /(?:it'?s me or|choose:? me or)\b[^.!?\n]*/gi,
    ],
    scripts: [
      "Those aren't the only two options. Here's a third.",
      "I'm not accepting the framing. Let me restate the problem.",
      "I need time to think rather than pick between two bad doors.",
    ],
  },
];

/**
 * Crisis-escalation signatures. Matching any of these surfaces the safety panel.
 *
 * Two categories are included, both grounded in danger-assessment research
 * (Campbell's Danger Assessment; Stark on separation violence):
 *   (a) explicit references to physical harm, weapons, or self-harm as leverage;
 *   (b) retaliation threats attached to leaving or telling — separation and
 *       disclosure are the documented peak-risk windows, so a threat conditioned
 *       on either is treated as safety-relevant rather than merely rhetorical.
 */
export const SAFETY_SIGNALS = [
  /\b(?:kill|hurt|beat|strangle|choke|stab|shoot|smash|break) (?:you|him|her|them|myself|the (?:kids|children|dog|cat))\b/gi,
  /\b(?:i(?:'?m| am)? ?(?:going to|gonna)|i'?ll|i will) [^.!?\n]{0,24}?\bmake (?:sure )?(?:you|him|her|them) (?:pay|regret|sorry|suffer)\b/gi,
  /\b(?:i(?:'?m| am)? ?(?:going to|gonna)|i'?ll|i will) end (?:it|you|this|myself)\b/gi,
  /\bif i can'?t have you\b/gi,
  /\b(?:gun|knife|weapon)\b[^.!?\n]{0,40}?\b(?:you|show|use|get)\b/gi,
  /\byou'?ll (?:be sorry|regret (?:it|this)|never (?:see|leave))\b/gi,
  // Separation/disclosure-conditioned retaliation. The consequence side is
  // constrained to harmful outcomes so benign conditionals ("if you go to the
  // party I'll stay home") do not trip the safety panel.
  /\bif you (?:ever )?(?:leave|walk out|tell (?:anyone|him|her|them)|call the (?:cops|police)|report me|go to the (?:cops|police))\b[^.!?\n]{0,70}?\b(?:i'?ll|i will|you'?ll)\s*(?:\w+\s+){0,3}?(?:regret|sorry|suffer|pay|destroy|ruin|end|hurt|kill|take the (?:kids|children)|never see|lose (?:everything|the kids))\b/gi,
  /\b(?:i(?:'?ll| will)) (?:hurt|kill) myself if you\b/gi,
];
