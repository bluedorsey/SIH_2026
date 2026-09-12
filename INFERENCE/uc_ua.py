"""
Unsafe Act / Unsafe Condition classification (SIH26165 deliverable).

UC and UA answer a different question from the EEI verdict. The verdict asks how bad this
could be; UC/UA asks what KIND of thing it is - a state of the workplace, or something a
person did. Both can be true at once (a man with no harness on a broken scaffold), so this
returns two independent flags, never one label.

    UA   the named cause is a human behaviour
         "worker ne harness nahi pehna", "operator switched on the machine while fixing it"
    UC   the named cause is a physical state
         "floor slippery tha", "escape ladder tuta hua tha", "uncovered manhole"

Rules, not a learned head, for three reasons: the only labelled data is 56 rows (too few to
train AND evaluate), it is English paper-factory text (will not transfer to Hinglish), and the
distinction is grammatical - who or what is the subject of the unsafe thing - which rules
capture directly and a 56-row classifier would only approximate.
"""
from __future__ import annotations

import re

# --------------------------------------------------------------------------- actors
_ACTOR = re.compile(
    r"\b(operator|worker|technician|attendant|driver|electrician|engineer|helper|staff|"
    r"employee|crew|fitter|welder|rigger|foreman|supervisor|contractor|labour|labor|"
    r"roustabout|derrickman|driller|mechanic|fitter|person|man|colleague|collique|"
    r"mistri|khalasi|mazdoor|karmchari|aadmi|banda|log|karigar|JE|AE|I/C|in-?charge)\b", re.I)

# --------------------------------------------------------------------------- unsafe ACT
# a behaviour: something a person chose to do, or chose not to do
_ACT = [
    # PPE / equipment not worn or used - the single commonest UA in Indian registers
    (re.compile(r"\b(nahi|na)\s+(pehn\w*|lagay\w*|laga\w*|pahn\w*)", re.I), "ppe_not_worn"),
    (re.compile(r"\b(without|not)\s+(wearing|using|donning)\b", re.I), "ppe_not_worn"),
    (re.compile(r"\b(did\s+not|didn'?t|failed\s+to)\s+(wear|use|don|follow|check|isolate|test)\b", re.I),
     "procedure_not_followed"),
    (re.compile(r"\bpehn\w*\s+(bina|binaa)\b", re.I), "ppe_not_worn"),
    # procedure skipped
    (re.compile(r"\bbina\s+[\w\s]{0,24}?\s*(ke|kiye|liye)\b", re.I), "procedure_not_followed"),
    (re.compile(r"\b(kiye|liye|banaye|lagaye)\s+bina\b", re.I), "procedure_not_followed"),
    (re.compile(r"\bwithout\s+(a\s+)?(permit|ptw|loto|isolation|gas\s*test|jsa|authorisation|"
                r"authorization|clearance|barricad\w*|supervision)\b", re.I), "procedure_not_followed"),
    # active dangerous behaviour
    (re.compile(r"\b(bypass\w*|override\w*|overrode|disabl\w*|defeat\w*|tamper\w*)\b", re.I),
     "control_bypassed"),
    (re.compile(r"\b(hata\s*(diya|di|dena)|nikal\s*(diya|di)|utar\s*(diya|di)|khol\s*(diya|di|na\s+shuru))\b", re.I),
     "control_bypassed"),
    (re.compile(r"\b(climb\w*|jump\w*|reach\w*\s+into|lean\w*|stood\s+on|standing\s+on|"
                r"crawl\w*|crossed?\s+over)\b", re.I), "risky_position"),
    (re.compile(r"\b(chadh\s*(gaya|gayi|kar)|kood\w*|jhuk\s*kar|latak\w*)\b", re.I), "risky_position"),
    (re.compile(r"\b(switched?\s+on|started|operated|ran)\b[^.]{0,40}\bwhile\b[^.]{0,40}"
                r"\b(fixing|repair\w*|cleaning|adjust\w*|inside)\b", re.I), "operated_during_work"),
    (re.compile(r"\b(manually|by\s+hand)\s+(push\w*|lift\w*|operat\w*|open\w*)\b", re.I),
     "manual_workaround"),
    (re.compile(r"\b(push\w*|lift\w*|operat\w*|open\w*|mov\w*)\s+manually\b", re.I), "manual_workaround"),
    (re.compile(r"\b(speed\w*|rash\w*|overload\w*|short\s*cut|shortcut)\b", re.I), "risky_behaviour"),
]

# --------------------------------------------------------------------------- unsafe CONDITION
# a state of the workplace: true whether or not anyone is present
_COND = [
    (re.compile(r"\b(slip+er\w*|phisal\w*|chikn\w*|greasy|wet\s+floor|gil[ae])\b", re.I), "slippery_surface"),
    # "slipped / slid / tripped on X" names a surface state even when X is not itself a cue word
    (re.compile(r"\b(slip+ed|slid|slipping|tripp?ed|trip+ing|stumbl\w*|phisal\s*gay\w*)\b", re.I),
     "slip_trip_surface"),
    (re.compile(r"\b(spill\w*|leak\w*|seep\w*|overflow\w*|ris\w*\s+leak|tapak\w*)\b", re.I), "spill_or_leak"),
    (re.compile(r"\b(broken|damaged|defective|faulty|crack\w*|tut[ae]|toot\w*|phat[ae]|fat\s+gay\w*|"
                r"kharab|bigad\w*|collaps\w*|(rope|wire|sensor|brake|valve|switch|limit)\s+fail\w*|worn\s*out|corrod\w*|jang)\b", re.I),
     "damaged_equipment"),
    (re.compile(r"\b(uncovered|open\s+(manhole|drain|pit|trench)|khul[ai]\s+(nali|manhole|pit)|"
                r"bina\s+cover|cover\s+nahi|missing\s+(cover|guard|grating))\b", re.I), "opening_unprotected"),
    (re.compile(r"\b(unguarded|no\s+guard|guard\s+(missing|removed)|exposed\s+(wire|cable|"
                r"conductor|terminal|part)|naked\s+wire|tar\s+khul\w*)\b", re.I), "unguarded_hazard"),
    (re.compile(r"\b(barricad\w*\s+(nahi|absent|missing|not)|no\s+barricad\w*|bina\s+barricad\w*|"
                r"unbarricaded|cordon\w*\s+nahi)\b", re.I), "no_barricade"),
    (re.compile(r"\b(poor|dim|insufficient|inadequate|low)\s+(light\w*|illuminat\w*|visibility)\b", re.I),
     "poor_lighting"),
    (re.compile(r"\b(andher[aa]|roshni\s+(kam|nahi)|light\s+nahi)\b", re.I), "poor_lighting"),
    (re.compile(r"\b(obstruct\w*|cluttered|blocked|block\s+ho|jam+ed|jam\s+(hai|tha)|"
                r"kept\s+(near|along|on)|padd?[ae]\s+(the|tha|hue))\b", re.I), "obstruction"),
    (re.compile(r"\b(loose|dheel[ae]|unbalanc\w*|unstable|uneven|wobbl\w*|hil\s+rah\w*|"
                r"high\s+stack\w*|improperly\s+stack\w*)\b", re.I), "unstable_arrangement"),
    (re.compile(r"\b(sharp\s+edge|protrud\w*|nikl[ae]\s+hu\w*|dangling|hanging|latk\w*)\b", re.I),
     "protrusion_or_dangling"),
    (re.compile(r"\b(short[\s-]*circuit\w*|spark\w*|earthing\s+(nahi|missing)|no\s+earthing)\b", re.I),
     "electrical_defect"),
    (re.compile(r"\b(kaam\s+nahi\s+kar|not\s+working|non[\s-]*functional|out\s+of\s+order|"
                r"band\s+(pada|padi|hai|tha))\b", re.I), "equipment_not_working"),
    (re.compile(r"\bnot\s+(rotating|turning|running|functioning|closing|latching|holding|"
                r"locking|seated|secured)\b", re.I), "equipment_not_working"),
]

# a person merely being the VICTIM is not an unsafe act - "almost hit by a trolley" describes
# something that happened TO them, not something they did
_PASSIVE = re.compile(
    r"\b(almost|nearly|about\s+to\s+be|narrowly)\s+(hit|struck|knock\w*|injur\w*|caught|pinch\w*|"
    r"crush\w*|run\s+over)\b|\b(hit|struck|knock\w*|pinch\w*)\s+by\b", re.I)


def _hits(text: str, table) -> list[dict]:
    out, seen = [], set()
    for rx, tag in table:
        m = rx.search(text)
        if m and tag not in seen:
            seen.add(tag)
            out.append({"cue": tag, "text": m.group(0).strip(), "start": m.start(), "end": m.end()})
    return out


def classify(text: str, spans: list[dict] | None = None) -> dict:
    """Two independent flags plus the evidence for each. Never returns a single label."""
    spans = spans or []
    acts = _hits(text, _ACT)
    conds = _hits(text, _COND)
    actor = _ACTOR.search(text)
    passive = _PASSIVE.search(text)

    # a control_absent span with no human agent is a missing barrier = condition
    if not conds and any(s["role"] == "control_absent" for s in spans) and not acts:
        s = next(s for s in spans if s["role"] == "control_absent")
        conds.append({"cue": "control_absent_span", "text": s["text"],
                      "start": s["start"], "end": s["end"]})
    # a degraded control is a condition
    if any(s["role"] == "control_ineffective" for s in spans) and not conds:
        s = next(s for s in spans if s["role"] == "control_ineffective")
        conds.append({"cue": "control_degraded_span", "text": s["text"],
                      "start": s["start"], "end": s["end"]})

    ua, uc = bool(acts), bool(conds)

    # The decision that actually separates the two, validated against a real register:
    #   a physical cause is NAMED            -> UC   ("slipped on the folded carpet", "oil spill")
    #   a person is in the near-miss and no
    #   physical cause is named              -> UA   ("operator almost hit by a trolley")
    # The second case is a positioning/behaviour finding: nothing was defective, someone was
    # somewhere they should not have been. Registers file those as unsafe acts, and the
    # corrective action differs - you brief a person, you do not raise a work order.
    if not uc and not ua and (actor or passive):
        ua = True
    if not uc and not ua and spans:
        uc = True                      # a bare hazard statement with no person

    labels = [l for l, on in (("UA", ua), ("UC", uc)) if on]

    n = len(acts) + len(conds)
    conf = 0.35 + min(0.5, 0.18 * n) + (0.08 if actor else 0.0)
    return {
        "labels": labels,
        "unsafe_act": ua,
        "unsafe_condition": uc,
        "confidence": round(min(0.95, conf), 3),
        "act_cues": acts,
        "condition_cues": conds,
        "actor": actor.group(0) if actor else None,
        "passive_victim": bool(passive),
        "basis": "rules",
    }
