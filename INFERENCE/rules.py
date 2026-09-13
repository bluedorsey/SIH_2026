"""Deterministic layer: language id, statement type, span evidence and negation scope.

Runs first and always. It is the only layer that works with no tuned model present, so the
pipeline degrades to rules-only rather than failing.
"""
from __future__ import annotations

import re

from .config import SPAN_ROLES  # noqa: F401  (documents the vocabulary these patterns emit)
from .knowledge import HAZARDS
from .lexicon import MINED

# ------------------------------------------------------------------ language
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_ASSAMESE = re.compile(r"[ঀ-৿]|\b(nasil|nohol|hoise|ase|asil|cholise|bhitorot|"
                       r"gol|dhukise|korile|nohoi)\b", re.I)
_HINGLISH = re.compile(r"\b(nahi|nahin|tha|thi|the|hai|hain|kiya|raha|rahi|rahe|gaya|gayi|mein|"
                       r"aur|bina|koi|kaam|hua|hui|liye|lekin|phir|upar|neeche|niche|andar|bahar|"
                       r"pehle|baad|sirf|bhi|gira|toota|chal|band|khula|dekha|mila|karke|wajah|"
                       r"dauran|jagah|paas|log|admi|se|par|pe)\b", re.I)


def detect_language(text: str) -> str:
    if _DEVANAGARI.search(text):
        return "hindi"
    if len(_ASSAMESE.findall(text)) >= 2:
        return "assamese_mix"
    hits = [h.lower() for h in _HINGLISH.findall(text)]
    # "the" is Hinglish (plural of "tha") AND the commonest English word; on its own it says
    # nothing. It counts only alongside a word that is unambiguously Hinglish.
    if any(h != "the" for h in hits) and len(hits) >= 2:
        return "hinglish"
    return "english"


# ------------------------------------------------------------ statement type
_HYPOTHETICAL = re.compile(r"\b(if|agar|could have|would have|might have|ho sakta|sakta tha|"
                           r"suppose|imagine|what if)\b", re.I)
_HISTORICAL = re.compile(r"\b(last (month|week|year)|pichle|purane|puran[ai]|do saal|"
                         r"\d+ saal purane|previously|earlier incident|"
                         r"in 20\d\d|history|past incident)\b", re.I)
_TRAINING = re.compile(r"\b(training|drill|mock|toolbox talk|TBT|demonstration|exercise|induction|"
                       r"case (?:study|ka study)|awareness session|discuss kiya gaya)\b", re.I)
_CORRECTIVE = re.compile(r"\b(has been (rectified|corrected|closed)|rectified|action closed|"
                         r"theek kar diya|thik kar diya|resolved|完成)\b", re.I)
_PERSON_ACTING = re.compile(r"\b(worker|employee|operator|technician|rigger|roustabout|crew|"
                            r"person|log|aadmi|admi|banda|he|she|they|was|were|is|are)\b", re.I)


def detect_statement_type(text: str) -> str:
    if _TRAINING.search(text):
        return "training_example"
    if _HYPOTHETICAL.search(text):
        return "hypothetical"
    if _HISTORICAL.search(text):
        return "historical"
    if _CORRECTIVE.search(text):
        return "corrective_completed"
    return "observed" if _PERSON_ACTING.search(text) else "condition_only"


# ------------------------------------------------------------- span evidence
PATTERNS: dict[str, str] = {
    "energy_cue": r"\b(\d+(?:[.,]\d+)?\s?(?:m|meter|metre|ft|feet|kg|ton|kv|volt|bar|psi|deg ?c)\b"
                  r"|monkey ?board|derrick|suspended load|live (?:panel|equipment|line)|H2S|"
                  r"rotating|pressuris\w+|excavat\w+|confined space)",
    "release_cue": r"\b(gir(?:a|i|e)\w*|fell|fall(?:en|ing)?|dropp?ed|slipp?ed|struck|hit|"
                   r"released|leak(?:ed|age)?|burst|ruptur\w+|caught fire|toot\w+|contacted)\b",
    "no_exposure_cue": r"\b(koi bhi\s+\w+\s+(?:nahi|nai)\s+(?:gaya|gaye|gayi|tha)|"
                       r"na hi koi (?:exposure|chot|injury)|"
                       r"(?:no ?body|no one|nobody) (?:was |were )?(?:exposed|present|inside|entered)|"
                       r"koi (?:andar )?nahi (?:gaya|tha)|area (?:was )?(?:clear|vacant|empty))",
    "no_release_cue": r"\b(no (?:fall|drop|release|contact|spill)|nahi gir\w*|did not (?:fall|drop)|"
                      r"abhi tak nahi|about to|almost|nearly|prevented)\b",
    "exposure_cue": r"\b(neeche|niche|below|underneath|under the|line of fire|standing near|"
                    r"paas (?:khada|khade)|inside (?:the )?(?:tank|vessel)|in the way|"
                    r"\d+\s?(?:log|people|persons?|workers?) (?:the|were|standing))",
    "control_present": r"\b(harness (?:worn|clipped|anchored)|barricad\w+ (?:was |were )?(?:done|"
                       r"in place|erected)|LOTO (?:done|verified|applied)|permit (?:taken|issued|valid)|"
                       r"gas test (?:done|completed)|SCBA (?:worn|used)|guard (?:in place|fitted)|"
                       r"exclusion zone (?:set|established)|lanyard (?:anchored|clipped)"
                       r"|(?:harness|barricading|barricade|permit|PTW|LOTO|gas ?test|guard|SCBA|"
                       r"lifeline|lanyard|shoring|isolation)\s+"
                       r"(?:sahi\s+)?(?:laga\w*|pehn\w*|li?y[ae]|kiy[ae]|hua|hui|tha|thi|thee)\b"
                       r"|\bsahi\s+(?:tarike se\s+)?(?:barricading|isolation|harness)\b)",
    "control_absent": r"(?:\bno\s+(?:\w+\s+){0,2}(?:harness|barricad\w+|permit|PTW|LOTO|lockout|gas ?test\w*|"
                      r"guard|SCBA|BA set|exclusion zone|banksman|spotter|shoring|lifeline|lanyard|"
                      r"isolation|tag|supervision|training|test)"
                      r"|\bwithout\s+(?:\w+\s+){0,2}(?:harness|permit|PTW|LOTO|barricad\w+|guard|SCBA|"
                      r"gas ?test\w*|isolation|lifeline|lanyard|approval|authoris\w+|authoriz\w+)"
                      r"|\bbina\s+(?:\w+\s+){0,2}(?:kiye|kiya|ke)?"
                      r"|\b(?:harness|barricading|barricade|permi(?:t|ssion)|PTW|LOTO|gas ?test\w*|guard|SCBA|"
                      r"shoring|isolation|lifeline|lanyard|training|test|authori[sz]ation|clearance)\s+(?:nahi|nai|nahin)\b"
                      r"|\bnahi\s+(?:tha|thi|kiya|liya|hua)\b"
                      r"|\bnot\s+(?:isolated|barricaded|guarded|tested|tagged|anchored|clipped|"
                      r"authorised|authorized|permitted|supervised)\b)",
    "control_ineffective": r"\b(worn but not clipped|not anchored|not verified|expired|overdue|"
                           r"defective|damaged|bypassed|disabled|partially|loose|not tightened|"
                           r"discharged|empty)\b",
    "pseudo_control": r"\b(hard ?hat|helmet|safety shoes|training (?:given|provided)|signage|"
                      r"sign board|experienced (?:worker|operator)|cone (?:placed|kept)|"
                      r"toolbox talk|briefing (?:given|done)|careful)\b",
    "negation_cue": r"\b(no|not|nahi|nahin|nai|bina|without|never|koi nahi)\b",
    "outcome_cue": r"\b(no injury|koi (?:chot|injury) nahi|injur\w+|fracture|amputat\w+|"
                   r"hospitalis\w+|hospitaliz\w+|fatal\w*|died|death|burn\w*|first aid|"
                   r"medevac\w*|unconscious|LTI|near ?miss)\b",
    "statement_cue": r"\b(if|agar|could have|would have|last (?:month|week|year)|pichle|"
                     r"during (?:training|drill|mock)|has been rectified|action closed)\b",
}
_RX = {role: re.compile(p, re.I) for role, p in PATTERNS.items()}


# The hazard cues in knowledge.py already name every energy type we care about; reusing them as
# energy_cue patterns lifted coverage from 31 rows in 180 to most of the set. Without an energy
# span the tree cannot answer question 1, and the row falls through to INSUFFICIENT.
_HAZARD_RX = [re.compile(h["cues"], re.I) for h in HAZARDS.values()]


def find_spans(text: str) -> list[dict]:
    """Every rule hit as a span with real character offsets."""
    spans: list[dict] = []
    for role, rx in _RX.items():
        for m in rx.finditer(text):
            spans.append({"role": role, "text": m.group(0), "start": m.start(), "end": m.end(),
                          "source": "rules"})
    taken = {(s["start"], s["end"]) for s in spans}
    # corpus-mined vocabulary: terms the teachers actually used on real incident text.
    # This is what closes the "no energy cue found" gap - hand-written patterns missed
    # isolate / depressurise / calibration / flange and 80 % of the rest.
    for role, rx in MINED.items():
        for m in rx.finditer(text):
            if (m.start(), m.end()) in taken:
                continue
            if any(s["start"] <= m.start() < s["end"] for s in spans):
                continue                         # a hand-written rule already claimed this text
            spans.append({"role": role, "text": m.group(0), "start": m.start(),
                          "end": m.end(), "source": "rules:mined"})
            taken.add((m.start(), m.end()))
    for rx in _HAZARD_RX:                       # hazard vocabulary -> energy_cue
        for m in rx.finditer(text):
            if (m.start(), m.end()) in taken:
                continue
            if any(s["start"] <= m.start() < s["end"] for s in spans
                   if s["role"] not in ("negation_cue", "energy_cue")):
                continue                         # already covered by a control/outcome span
            spans.append({"role": "energy_cue", "text": m.group(0), "start": m.start(),
                          "end": m.end(), "source": "rules:hazard_lexicon"})
            taken.add((m.start(), m.end()))
    spans.sort(key=lambda s: (s["start"], s["end"]))
    return spans


# --------------------------------------------------------- negation scoping
_OUTCOME_WORDS = re.compile(r"\b(injur\w+|chot|damage|harm|casualt\w+|loss)\b", re.I)
_CONTROL_WORDS = re.compile(r"\b(harness|barricad\w+|permit|PTW|LOTO|guard|SCBA|gas test|"
                            r"shoring|banksman|exclusion zone)\b", re.I)
_RELEASE_WORDS = re.compile(r"\b(fall|fell|gir\w*|drop|release|contact|spill|leak)\b", re.I)


def negation_scope(text: str, spans: list[dict]) -> dict:
    """What a negation actually negates decides whether it lowers the verdict.

    'Koi injury nahi hui' negates the OUTCOME - the exposure still happened, so potential is
    unchanged. 'Barricading nahi tha' negates a CONTROL, which RAISES severity. Treating the
    two alike is the classic way a SIF precursor gets closed as a non-event.
    """
    negs = [s for s in spans if s["role"] == "negation_cue"]
    if not negs:
        return {"negation_detected": False, "negation_scope": None, "note": None}
    scopes = set()
    for n in negs:
        window = text[max(0, n["start"] - 40): min(len(text), n["end"] + 40)]
        if _OUTCOME_WORDS.search(window):
            scopes.add("outcome_only")
        if _CONTROL_WORDS.search(window):
            scopes.add("control")
        if _RELEASE_WORDS.search(window):
            scopes.add("release")
    if not scopes:
        scopes.add("unclear")
    note = None
    if "outcome_only" in scopes:
        note = ("negation applies to the outcome, not to the exposure - potential severity is "
                "unchanged")
    if "control" in scopes:
        note = ("negation applies to a control (a barrier is missing) - this raises severity, "
                "it does not lower it")
    return {"negation_detected": True,
            "negation_scope": "+".join(sorted(scopes)),
            "note": note}
