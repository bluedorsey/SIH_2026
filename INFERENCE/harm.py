"""Harm extraction: WHAT happened to WHICH part of the body, and is that serious.

Question 3 of the EEI tree ("was anyone seriously injured?") used to be answered by one regex of
fatal outcomes. "Aankhon me bahut jalan hai" after a gas release was read as "no injury stated",
because "jalan" was not in the list and nothing looked at the body part at all.

This is a TABLE, not a model, and it is deliberately small:

    harm class      e.g. burn, chemical irritation, fracture, cut, crush, unconscious
    body part       e.g. eyes, head, chest, hand, finger
    severity        serious | moderate | minor, from (harm class, body part, minimiser)

A chemical burn or irritation to the EYES or the AIRWAY is serious; the same to a hand is not.
A fracture is serious anywhere except a finger. Any harm the text itself minimises ("halka",
"minor", "first aid") drops one level. That is the whole of it, and every line of it can be
shown to a reviewer.

The severity here decides ONLY question 3. Potential severity - the SIF question - is still the
energy and the barrier; a burned hand from a released pressure line is P_SIF/H_SIF on those
grounds, not on the hand.
"""
from __future__ import annotations

import re

from .config import HARM_ENABLED

# ---------------------------------------------------------------- vocab
# (class, regex). Latin Hinglish, English, and Devanagari for the common ones.
# Python's \b does not treat a Devanagari vowel sign (matra) as a word character, so "गया" can
# never end at a word boundary; these lookarounds are the boundary that works in both scripts.
_L = r"(?<![\w\u0900-\u097F])"
_R = r"(?![\w\u0900-\u097F])"
_HARM = [
    ("fatal",        r"fatal[\w\u0900-\u097F]*|died|death|killed|maut|mar gaya|mrityu|मृत्यु|मर गया|मौत"),
    ("amputation",   r"amputat[\w\u0900-\u097F]+|kat ?ke alag|ungli kat gayi|कट कर अलग"),
    ("fracture",     r"fractur[\w\u0900-\u097F]*|haddi (?:toot|tut)[\w\u0900-\u097F]*|हड्डी टूट[\w\u0900-\u097F]*|फ्रैक्चर"),
    # "toot gaya" is a fracture only next to a body part; "lanyard toot gaya" is a broken strap
    ("break",        r"toot gay[ai]|tut gay[ai]|टूट गय[ाी]"),
    ("unconscious",  r"unconscious|behosh|senseless|collapsed|coma|बेहोश|बेहोशी"),
    ("asphyxia",     r"saans (?:nahi|rukh|band)[\w\u0900-\u097F]*|dum ghut[\w\u0900-\u097F]*|ghutan|suffocat[\w\u0900-\u097F]*|asphyx[\w\u0900-\u097F]*|"
                     r"breath(?:ing)? (?:difficult|problem|trouble)|breathless|सांस (?:नहीं|रुक)[\w\u0900-\u097F]*|दम घुट[\w\u0900-\u097F]*"),
    ("electric_shock", r"electric shock|electrocut[\w\u0900-\u097F]*|current laga|shock laga|jhatka laga|"
                     r"करंट लग[\w\u0900-\u097F]*|बिजली का झटका|झटका लग[\w\u0900-\u097F]*"),
    ("burn",         r"burn(?:t|ed|s|ing)?\b|jal gay[ai]|jal gaya|jhulas[\w\u0900-\u097F]*|scald[\w\u0900-\u097F]*|जल गय[ाी]|जल गया|झुलस[\w\u0900-\u097F]*"),
    ("chemical_irritation", r"jalan|irritation|itch[\w\u0900-\u097F]*|khujli|watering|paani aa (?:raha|rahi)|"
                     r"redness|laal ho gay[ai]|dhundhla|blurred|dikh(?:na|ai) (?:band|nahi)|"
                     r"chubh[\w\u0900-\u097F]* raha|जलन|खुजली|लाल हो गय[ाी]|धुंधला"),
    ("poisoning",    r"ulti|vomit[\w\u0900-\u097F]*|nausea|chakkar|dizzy|dizziness|giddy|उल्टी|चक्कर|बेचैनी"),
    ("crush",        r"crush[\w\u0900-\u097F]*|kuchal[\w\u0900-\u097F]*|dab gay[ai]|pinch[\w\u0900-\u097F]*|fas gay[ai]|phas gay[ai]|कुचल[\w\u0900-\u097F]*|दब गय[ाी]|फंस गय[ाी]"),
    ("cut",          r"\bcut\b|kat gay[ai]|kat gaya|katne|laceration|bleeding|khoon (?:beh|nikal)[\w\u0900-\u097F]*|"
                     r"deep wound|gash|कट गय[ाी]|खून (?:बह|निकल)[\w\u0900-\u097F]*|घाव"),
    ("bruise",       r"bruise[\w\u0900-\u097F]*|neel pad|contusion|swelling|sujan|soojan|sprain|moch|mooch|"
                     r"splinter|chubh gay[ai]|chubha|kaanta|scratch[\w\u0900-\u097F]*|kharonch|rash|"
                     r"नील|सूजन|मोच|खरोंच"),
    ("generic",      r"injur[\w\u0900-\u097F]+|chot (?:lag|aa)[\w\u0900-\u097F]*|chot lagi|hurt|ghayal|zakhmi|चोट|घायल|ज़ख्मी|जख्मी"),
]
HARM_WORDS = re.compile(_L + "(?:" + "|".join(f"(?P<{c}>{rx})" for c, rx in _HARM) + ")" + _R, re.I | re.U)

_BODY = [
    ("eyes",     r"aankh[\w\u0900-\u097F]*|ankh[\w\u0900-\u097F]*|eyes?|nazar|आंख[\w\u0900-\u097F]*|आँख[\w\u0900-\u097F]*"),
    ("head",     r"\bsir\b|sar|head|skull|khopdi|forehead|matha|सिर|माथा"),
    ("face",     r"face|chehra|chehre|mu(?:h|nh)|mouth|hoth|lips|चेहरा|मुंह|मुँह"),
    ("airway",   r"lungs?|phephde|saans|breath[\w\u0900-\u097F]*|gala|throat|chest|seena|seene|nose|naak|"
                 r"फेफड|सांस|गला|छाती|सीना|नाक"),
    ("spine",    r"spine|reedh|peeth|back\b|kamar|neck|gardan|रीढ़|पीठ|कमर|गर्दन"),
    ("torso",    r"pet|stomach|abdomen|kandha|shoulder|पेट|कंधा"),
    ("leg",      r"pair|paon|paer|legs?|foot|feet|ghutna|knee|ankle|takhna|thigh|jangh|"
                 r"पैर|पांव|घुटन[\w\u0900-\u097F]*|टखन[\w\u0900-\u097F]*"),
    ("hand",     r"haath|hath|hands?|arm|wrist|kalai|elbow|kohni|हाथ|कलाई|कोहनी"),
    ("finger",   r"ungli[\w\u0900-\u097F]*|fingers?|thumb|angutha|toes?|उंगल[\w\u0900-\u097F]*|अंगूठ[\w\u0900-\u097F]*"),
    ("skin",     r"skin|chamdi|tvacha|body|badan|sharir|त्वचा|चमड़ी|शरीर|बदन"),
]
BODY_PARTS = re.compile(_L + "(?:" + "|".join(f"(?P<{c}>{rx})" for c, rx in _BODY) + ")" + _R, re.I | re.U)

# "koi injury nahi hui", "no burn", "chot nahi lagi": the harm word is there, the harm is not
_NEG_BEFORE = re.compile(r"\b(?:no|koi|without|nahi|not|bina|कोई|नहीं)\s+(?:\w+\s+){0,2}$", re.I | re.U)
_NEG_AFTER = re.compile(r"^\s*(?:\w+\s+){0,1}(?:nahi|nai|nahin|not|नहीं)\b", re.I | re.U)
_MINIMISER = re.compile(r"\b(halka|halki|thoda|thodi|minor|slight\w*|superficial|first aid|"
                        r"chhota|chota|small|mamuli|hairline|thoda sa|जरा|थोड़ा|हल्का|हल्की|मामूली|"
                        # treated on the spot and done: the text itself says it was minor
                        r"eye ?wash|paani se dho\w*|wash(?:ed)? (?:with water|off|it)|rest (?:diya|given|le liya)|"
                        r"kaam pe wapas|resumed work|back to work)\b", re.I | re.U)

# ---------------------------------------------------------------- severity
# base level per harm class, then body-part adjustment, then the minimiser drops one level.
_BASE = {
    "fatal": 3, "amputation": 3, "fracture": 3, "unconscious": 3, "asphyxia": 3,
    "electric_shock": 3, "burn": 3, "crush": 3,
    "chemical_irritation": 2, "poisoning": 2, "cut": 2,
    "bruise": 1, "generic": 1, "break": 0,
}
# harms that are only serious when the ENERGY that caused them is of the matching kind: dust in
# the eye is irritation, acid in the eye is a chemical injury. `energy_type` comes from the
# hazard the pipeline established (regex or corroborated semantic), or None.
_NEEDS_ENERGY = {"chemical_irritation": {"chemical"}, "poisoning": {"chemical"}}
# body parts where a level-2 harm becomes serious, and where a level-3 harm stays serious
_CRITICAL = {"eyes", "head", "face", "airway", "spine", "torso"}
_LEVEL = {3: "serious", 2: "moderate", 1: "minor", 0: "minor"}


def _severity(harm: str, part: str | None, minimised: bool, energy_type: str | None = None) -> str:
    level = _BASE.get(harm, 1)
    if harm == "break":
        level = 3 if part else 0                        # "pair toot gaya" yes, "lanyard toot gaya" no
    if harm == "fracture" and part == "finger":
        level = 2                                       # the existing finger rule, kept
    if harm in _NEEDS_ENERGY and energy_type not in _NEEDS_ENERGY[harm]:
        level = min(level, 1)                           # irritation with no chemical named: minor
    if level == 2 and part in _CRITICAL:
        level = 3                                       # chemical in the eyes / airway is serious
    if harm in ("cut", "crush") and part == "finger":
        level = 2
    if minimised and harm not in ("fatal", "amputation"):
        level -= 1
    return _LEVEL[max(0, level)]


def detect_harm(text: str, energy_type: str | None = None) -> dict:
    """{'harms': [...], 'serious': bool, 'worst': {...}|None}. Each harm carries the harm span,
    the nearest body part (within 60 characters), the severity and why."""
    empty = {"harms": [], "serious": False, "worst": None}
    if not HARM_ENABLED or not text:
        return empty
    parts = [(m.lastgroup, m.start(), m.end(), m.group(0)) for m in BODY_PARTS.finditer(text)]
    harms = []
    for m in HARM_WORDS.finditer(text):
        cls = m.lastgroup
        if _NEG_BEFORE.search(text[max(0, m.start() - 24):m.start()]) or \
                _NEG_AFTER.match(text[m.end():m.end() + 16]):
            continue                                    # negated: "koi injury nahi hui"
        lo, hi = max(0, m.start() - 60), min(len(text), m.end() + 60)
        near = [p for p in parts if p[1] >= lo and p[2] <= hi]
        part = min(near, key=lambda p: abs(p[1] - m.start()))[0] if near else None
        part_span = min(near, key=lambda p: abs(p[1] - m.start())) if near else None
        minimised = _MINIMISER.search(text[lo:hi]) is not None
        sev = _severity(cls, part, minimised, energy_type)
        if sev == "minor" and cls == "break":
            continue                                    # a broken object is not a harm
        why = f"{cls}" + (f" to {part}" if part else "") + (" (minimised in text)" if minimised else "")
        harms.append({"harm": cls, "body_part": part, "severity": sev, "why": why,
                      "text": m.group(0), "start": m.start(), "end": m.end(),
                      "body_part_text": part_span[3] if part_span else None,
                      "body_part_start": part_span[1] if part_span else None,
                      "body_part_end": part_span[2] if part_span else None})
    if not harms:
        return empty
    order = {"serious": 3, "moderate": 2, "minor": 1}
    worst = max(harms, key=lambda h: (order[h["severity"]], _BASE.get(h["harm"], 1)))
    return {"harms": harms, "serious": worst["severity"] == "serious", "worst": worst}
