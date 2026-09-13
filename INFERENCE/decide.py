"""Fusion + the EEI decision tree.

Spans from the rules layer and from GLiNER are merged into the FOUR questions, and the verdict is
DERIVED from those four answers - never asserted directly. That is what makes every verdict
explainable: the response can always show which span produced which answer.
"""
from __future__ import annotations

import re

from .config import (CONFORMAL_ALPHA, EVIDENCE_HEAD_MIN_CONFIDENCE, FAST_LANE_MIN_CONFIDENCE,
                     REVIEW_MAX_CONFIDENCE, REVIEW_PREFILTER_MIN_CONFIDENCE, SPAN_THRESHOLD)

# a barrier that is present-but-degraded still counts as PRESENT: that is the CAPACITY branch
_CONTROL_PRESENT_ROLES = {"control_present", "control_ineffective"}
# A person is never a barrier. The mined lexicon learned "the worker" as control_present from
# "the worker was protected", and GLiNER will tag "ek worker" the same way; either one turns a
# burned worker into CAPACITY. Any control span that is just a person noun is dropped.
_PERSON = re.compile(
    r"^\W*(?:the |ek |a |one |do |teen |\d+ )?(?:worker|workers|employee|operator|technician|"
    r"rigger|roustabout|helper|crew|person|people|log|aadmi|admi|banda|bande|mazdoor|labour|"
    r"labor|staff|supervisor|engineer|contractor|driver|he|she|they)s?\W*$", re.I)
# verdicts that mean "a precursor may be here" - the only ones worth a reviewer's time
_SIF_LIKE = {"H_SIF", "L_SIF", "P_SIF", "EXPOSURE", "CAPACITY"}
_SERIOUS = re.compile(
    r"\b(fatal\w*|died|death|killed|amputat\w+|fractur\w+|hospitalis\w+|hospitaliz\w+|"
    r"surgery|concussion|unconscious|coma|paralys\w+|LTI|lost time|maut|mar gaya|"
    r"haddi (?:toot|tut)\w*|2nd degree|3rd degree|second degree|third degree)\b", re.I)
_NO_INJURY = re.compile(r"\b(no injury|no injuries|koi (?:chot|injury) nahi|nobody (?:was )?(?:hurt|injured)|"
                        r"uninjured|without injury|bach gay[ae]|near ?miss)\b", re.I)
_FINGER_ONLY = re.compile(r"\b(finger|toe|ungli)\b", re.I)
_DEGRADED = re.compile(
    r"\b(khula|khuli|tuta|tuti|toota|tooti|blocked|block|jam|jammed|damaged|broken|defective|"
    r"faulty|expired|overdue|missing|removed|bypass\w*|disabled|inhibited|not (?:working|"
    r"functioning|anchored|clipped|verified|secured|tested)|kaam nahi kar|band tha|band thi|"
    r"loose|dheela|partially|incomplete|adhura)\b", re.I)
# a barrier in the act of being opened, removed or bypassed is not a barrier
_BEING_REMOVED = re.compile(
    r"\b(khol\w*|hata\w*|nikal\w*|utar\w*|kaat\w*|open(?:ing|ed)?|remov\w*|dismantl\w*|"
    r"loosen\w*|slack\w*|break\w*|todd?\w*)\b", re.I)


def _barrier_effective(text: str, span: dict | None) -> bool:
    """False when a degradation word sits within ~60 chars of the barrier span."""
    if span is None:
        return True
    lo, hi = max(0, span["start"] - 60), min(len(text), span["end"] + 60)
    window = text[lo:hi]
    return _DEGRADED.search(window) is None and _BEING_REMOVED.search(window) is None
# Below-threshold energy stated in words rather than numbers. The hazard lexicon fires on the
# noun ("box", "tool"), so without this every minor event was read as high energy.
_LOW_ENERGY = re.compile(
    r"\b(chota|chhota|minor|small|slight|superficial|first aid (?:only|diya|given)|"
    r"cardboard|carton|paper cut|hand tool|screwdriver|scratch|graze|bruise|"
    r"knee height|waist height|ankle|stool|step ?stool|low level|ground level|"
    r"12 ?v|24 ?v|battery|torch)\b", re.I)
# "chhoti si baat" / "sirf ek" minimise a REAL hazard - the classic sarcasm trap. If a
# minimiser appears next to a missing barrier, the low-energy marker must not fire.
_MINIMISER = re.compile(
    r"\b(sirf ek|chhoti si baat|choti si baat|bas itna|itni si baat|sab kuch theek|"
    r"sab kuch perfect|koi badi baat nahi|minor si|just a|only a small)\b", re.I)


def _pick(spans: list[dict], roles: set[str] | str) -> dict | None:
    """Highest-confidence span for a role; rules spans count as 1.0 (deterministic)."""
    want = {roles} if isinstance(roles, str) else roles
    cands = [s for s in spans if s["role"] in want]
    if not cands:
        return None
    return max(cands, key=lambda s: s.get("score", 1.0))


def _fact(span: dict | None, value, source: str) -> dict:
    return {"value": value,
            "span": span["text"] if span else None,
            "span_start": span["start"] if span else None,
            "span_end": span["end"] if span else None,
            "source": source}


def fuse_spans(rule_spans: list[dict], gliner_spans: list[dict], threshold: float = SPAN_THRESHOLD) -> list[dict]:
    """One span list. A span both layers agree on is marked rules+gliner and wins ties."""
    keep = [s for s in gliner_spans if s.get("score", 1.0) >= threshold]
    out: list[dict] = []
    for r in rule_spans:
        match = next((g for g in keep if g["role"] == r["role"]
                      and not (g["end"] <= r["start"] or g["start"] >= r["end"])), None)
        # a hand-written pattern (1.0) outranks a corpus-mined term (0.9) when both answer the
        # same question: "burn" should be the outcome span, not the mined "breaking"
        base = 0.9 if r.get("source") == "rules:mined" else 1.0
        out.append({**r, "source": ("rules+gliner" if match else r.get("source", "rules")),
                    "score": max(base, match.get("score", 0)) if match else base})
    for g in keep:
        if not any(o["role"] == g["role"] and not (o["end"] <= g["start"] or o["start"] >= g["end"])
                   for o in out):
            out.append(g)
    out.sort(key=lambda s: (s["start"], s["end"]))
    return out


def four_questions(text: str, spans: list[dict], energy: dict, neg: dict,
                   semantic: dict | None = None, harm: dict | None = None) -> dict:
    """The four EEI questions, each with the span that answered it."""
    # ---- 1. high energy above the SIF threshold?
    gate = energy.get("gate")
    e_span = _pick(spans, "energy_cue")
    low_m = _LOW_ENERGY.search(text)
    if gate == "EXCEEDS":
        high = _fact(e_span, True, "energy_model")
    elif gate == "BELOW":
        high = _fact(e_span, False, "energy_model")
    elif low_m is not None and not (_MINIMISER.search(text) and _pick(spans, "control_absent")):
        # a stated small-energy marker beats the hazard lexicon's noun match
        high = {"value": False, "span": low_m.group(0), "span_start": low_m.start(),
                "span_end": low_m.end(), "source": "rules:low_energy_marker"}
    elif e_span is not None:
        high = _fact(e_span, True, e_span.get("source", "rules"))     # named energy, size unknown
    else:
        # A barrier only exists because an energy does. "gas test nahi hua" names no hazard word,
        # but a missing gas test is only meaningful where there is a confined space.
        implied = _pick(spans, "control_absent") or _pick(spans, _CONTROL_PRESENT_ROLES)
        if implied is not None:
            high = _fact(implied, True, "derived(barrier implies its energy)")
        elif semantic:
            # no word in any list named the energy, but the sentence MEANS one: "sulphur ki gas
            # se ulti", "garam steam", "गैस लीक". Meaning-typed, so no span to point at.
            high = {"value": True, "span": None, "span_start": None, "span_end": None,
                    "source": f"semantic({semantic['hazard']}@{semantic['score']:.2f})"}
        else:
            high = _fact(None, "unknown", "none")

    # ---- 3. serious injury? (computed first: it tells us whether energy was released)
    out_span = _pick(spans, "outcome_cue")
    m = _SERIOUS.search(text)
    worst = (harm or {}).get("worst")
    if m and not (_FINGER_ONLY.search(text[max(0, m.start() - 30):m.end() + 30]) and "fractur" in m.group(0).lower()):
        injury = _fact(out_span, True, "rules")
    elif worst and (harm or {}).get("serious"):
        # harm.py: WHAT happened to WHICH body part - "aankhon me jalan" after a gas release is
        # a chemical injury to the eyes, and that is serious; the same to a hand is not.
        injury = {"value": True, "span": worst["text"], "span_start": worst["start"],
                  "span_end": worst["end"], "source": f"rules:harm({worst['why']})"}
    elif _NO_INJURY.search(text):
        injury = _fact(out_span, False, "rules")
    elif worst:
        injury = {"value": False, "span": worst["text"], "span_start": worst["start"],
                  "span_end": worst["end"], "source": f"rules:harm({worst['why']}, {worst['severity']})"}
    elif out_span is not None:
        injury = _fact(out_span, False, out_span.get("source", "rules"))
    else:
        injury = _fact(None, False, "default_no_injury_stated")

    # The mirror image: an event that already happened and left only a MINOR harm (a splinter,
    # a bruise, a scratch), with no named energy source, was a low-energy event. Only when the
    # energy answer rests on meaning alone - never over a rule span or a number.
    worst = (harm or {}).get("worst")
    if (high["value"] is True and worst and worst["severity"] == "minor"
            and (high["source"].startswith("semantic") or high["source"] == "gliner+semantic")):
        high = {"value": False, "span": worst["text"], "span_start": worst["start"],
                "span_end": worst["end"], "source": f"derived(minor harm '{worst['why']}', no named energy)"}

    # A serious injury can only have come from an energy that was there and went off. "Haath jal
    # gaya" names no pipe, no pressure, no kV - but the burn IS the evidence. Without this the row
    # falls to INSUFFICIENT and the one report that describes an actual injury is the one that
    # gets no verdict.
    if high["value"] == "unknown" and injury["value"] is True:
        high = {"value": True, "span": injury["span"], "span_start": injury["span_start"],
                "span_end": injury["span_end"], "source": "derived(serious injury implies high energy)"}

    # ---- 2. was the energy released?
    rel, no_rel = _pick(spans, "release_cue"), _pick(spans, "no_release_cue")
    if no_rel is not None and rel is None:
        released = _fact(no_rel, False, no_rel.get("source", "rules"))
    elif rel is not None and no_rel is None:
        released = _fact(rel, True, rel.get("source", "rules"))
    elif rel is not None and no_rel is not None:
        released = _fact(no_rel, False, "rules(no_release overrides release)")
    elif injury["value"] is True:
        released = _fact(out_span, True, "derived(serious injury implies release)")
    else:
        # A precursor report describes a hazard that has NOT yet gone off; it rarely says so
        # explicitly. Defaulting to "unknown" here sent every such row to INSUFFICIENT and cost
        # all of the recall, so the absence of a release cue is read as "not released".
        released = _fact(None, False, "default_no_release_stated")

    # ---- 4. a direct control in place? (degraded still counts as present -> CAPACITY)
    pres, absent = _pick(spans, _CONTROL_PRESENT_ROLES), _pick(spans, "control_absent")
    pseudo = _pick(spans, "pseudo_control")
    if absent is not None and pres is None:
        control = _fact(absent, False, absent.get("source", "rules"))
    elif pres is not None and absent is None:
        control = _fact(pres, True, pres.get("source", "rules"))
    elif pres is not None and absent is not None:
        control = _fact(absent, False, "rules(absent overrides present)")
    elif pseudo is not None:
        control = _fact(pseudo, False, "pseudo_control_not_a_barrier")
    elif high["value"] is True:
        # high energy and NO barrier mentioned: for triage that is an unprotected exposure.
        # Reading it as "unknown" hides the precursor; a reviewer can still overturn it.
        control = _fact(None, False, "default_no_control_stated")
    else:
        control = _fact(None, "unknown", "none")

    return {"high_energy_present": high, "energy_released": released,
            "serious_injury": injury, "direct_control_present": control}


def rules_verdict(q: dict, statement_type: str, control_effective: bool = True) -> tuple[str | None, str]:
    """EEI tree. Returns (verdict, human-readable decision path)."""
    if statement_type in ("hypothetical", "historical", "training_example"):
        return "NON_EVENT", f"statement_type={statement_type} -> NON_EVENT"
    he = q["high_energy_present"]["value"]
    rel = q["energy_released"]["value"]
    inj = q["serious_injury"]["value"]
    ctl = q["direct_control_present"]["value"]
    p = f"high_energy={he}"
    if he == "unknown":
        return "INSUFFICIENT", p + " -> INSUFFICIENT"
    if he is False:
        if inj is True:
            return "L_SIF", p + f" AND serious_injury={inj} -> L_SIF"
        return "LOW_ENERGY", p + " -> LOW_ENERGY"
    p += f" AND energy_released={rel}"
    if rel == "unknown":
        return "INSUFFICIENT", p + " -> INSUFFICIENT"
    if rel is True:
        p += f" AND serious_injury={inj}"
        if inj is True:
            return "H_SIF", p + " -> H_SIF"
        if inj == "unknown":
            return "INSUFFICIENT", p + " -> INSUFFICIENT"
        p += f" AND control_present={ctl}"
        if ctl is True:
            return "CAPACITY", p + " -> CAPACITY (barrier limited the harm)"
        if ctl is False:
            return "P_SIF", p + " -> P_SIF (no barrier, nobody hurt this time)"
        return "INSUFFICIENT", p + " -> INSUFFICIENT"
    if statement_type == "corrective_completed":
        return None, p + " AND statement_type=corrective_completed -> teacher/heads decide"
    p += f" AND control_present={ctl}"
    if ctl is True and control_effective:
        return "SUCCESS", p + " -> SUCCESS (barrier held)"
    if ctl is True and not control_effective:
        # a barrier that is broken / open / blocked has not held anything yet
        return "EXPOSURE", p + " AND barrier_degraded=True -> EXPOSURE (barrier present but not effective)"
    if ctl is False:
        return "EXPOSURE", p + " -> EXPOSURE (no barrier, not released yet)"
    return "INSUFFICIENT", p + " -> INSUFFICIENT"


def decide(text: str, spans: list[dict], energy: dict, neg: dict, statement_type: str,
           head_pred: dict | None = None, semantic: dict | None = None,
           harm: dict | None = None) -> dict:
    """Fuse everything into the verdict block of the response."""
    # The hazard's own noun is not a control. GLiNER tags "Pipeline", "flange", "excavated soil"
    # as control_present; those are the energy source. A control span overlapping an energy_cue
    # span is a mislabel - drop it before the tree can answer question 4 with it.
    _e = [(s["start"], s["end"]) for s in spans if s["role"] == "energy_cue"]
    spans = [s for s in spans
             if not (s["role"] in _CONTROL_PRESENT_ROLES
                     and (any(s["start"] < b and a < s["end"] for a, b in _e)
                          or _PERSON.match(s["text"])))]
    q = four_questions(text, spans, energy, neg, semantic, harm)
    ctl_span = _pick(spans, _CONTROL_PRESENT_ROLES)
    # A control_ineffective ROLE alone is not enough - the mined lexicon carries noise
    # ("anchor point" mined as ineffective). Require the text to actually say the barrier is
    # degraded, near either the ineffective span or the control span itself.
    effective = (_barrier_effective(text, ctl_span)
                 and all(_barrier_effective(text, s)
                         for s in spans if s["role"] == "control_ineffective"))
    # an explicit "nobody was exposed" ends it: there is no line of fire to protect
    no_exp = _pick(spans, "no_exposure_cue")
    if no_exp is not None and q["serious_injury"]["value"] is not True:
        tree_verdict = "NON_EVENT"
        path = f"no_exposure_cue={no_exp['text']!r} -> nobody in the line of fire -> NON_EVENT"
    else:
        tree_verdict, path = rules_verdict(q, statement_type, effective)
    head = (head_pred or {}).get("verdict") or {}
    head_verdict, head_conf = head.get("label"), head.get("confidence")

    layers = ["rules"]
    if any(s.get("source", "").endswith("gliner") or s.get("source") == "gliner" for s in spans):
        layers.append("gliner")
    if head_verdict:
        layers.append("setfit")

    if tree_verdict is None:                      # tree abstained -> fall back to the head
        verdict, agreed = head_verdict or "INSUFFICIENT", ["setfit"] if head_verdict else []
        confidence = head_conf or 0.4
    else:
        verdict = tree_verdict
        agreed = [l for l in layers if l != "setfit"] + (["setfit"] if head_verdict == tree_verdict else [])
        # a verdict every layer supports, backed by verbatim spans, is worth more than a soft score
        # Confidence must track EVIDENCE, not span count. Counting raw spans let the model lane
        # inflate confidence just by finding more text, and the review rate collapsed to 2% -
        # confidently wrong. A question answered by a safety default, or by a model span alone,
        # is worth less than one answered by a verbatim rule match.
        known = evidenced = model_only = assumed = 0
        for f in q.values():
            if f["value"] == "unknown":
                continue
            known += 1
            src = f.get("source") or "none"
            if src.startswith("default") or src.startswith("derived"):
                assumed += 1
            elif src.startswith("rules"):
                evidenced += 1           # verbatim rule match - "rules+gliner" is agreement, not doubt
            elif "gliner" in src or src.startswith("semantic"):
                model_only += 1
            else:
                evidenced += 1
        confidence = 0.34 + 0.13 * evidenced + 0.08 * model_only + 0.06 * assumed
        if not effective:
            confidence = min(confidence, 0.62)   # a degraded barrier is exactly the ambiguous case
        if head_verdict == tree_verdict:
            confidence = min(0.97, confidence + 0.08)
        elif head_verdict:
            confidence = max(0.30, confidence - 0.12)              # layers disagree -> less sure

    conformal = [verdict]
    if confidence < 1 - CONFORMAL_ALPHA and head_verdict and head_verdict != verdict:
        conformal.append(head_verdict)                              # keep the runner-up in the set

    route = "fast_lane" if confidence >= FAST_LANE_MIN_CONFIDENCE else "slow_lane"
    review = confidence < REVIEW_MAX_CONFIDENCE or verdict == "INSUFFICIENT"
    reason = None
    # Low confidence alone is not a reason to spend a reviewer. When the tree, the verdict head
    # AND the prefilter head all say "not a precursor", the row is closed - a human looking at a
    # LOW_ENERGY row every layer agreed on finds nothing to overturn. Any layer dissenting
    # (head says EXPOSURE, prefilter says SIF) keeps the row in the queue.
    # ...but a coin-flip disagreement is not a dissent. The verdict head must be at least
    # EVIDENCE_HEAD_MIN_CONFIDENCE sure of its SIF-like label, and the prefilter head at least
    # REVIEW_PREFILTER_MIN_CONFIDENCE sure of "SIF" - a prefilter "1" at 0.52 on "small oil leak,
    # no one exposed" was sending a NON_EVENT to a human.
    prefilter = (head_pred or {}).get("prefilter") or {}
    head_dissents = (head_verdict in _SIF_LIKE
                     and (head_conf or 0.0) >= EVIDENCE_HEAD_MIN_CONFIDENCE)
    prefilter_dissents = (str(prefilter.get("label", "0")) == "1"
                          and (prefilter.get("confidence") or 0.0) >= REVIEW_PREFILTER_MIN_CONFIDENCE)
    all_layers_say_no = (verdict not in _SIF_LIKE and verdict != "INSUFFICIENT"
                         and not head_dissents and not prefilter_dissents)
    if review and all_layers_say_no:
        review = False
        reason = None
    elif review:
        reason = ("verdict INSUFFICIENT - the text does not answer the four questions"
                  if verdict == "INSUFFICIENT" else f"confidence {confidence:.2f} below review threshold")
    return {"questions": q,
            "verdict": {"label": verdict, "confidence": round(confidence, 3),
                        "conformal_set": conformal, "route": route,
                        "layers_agreed": agreed, "llm_invoked": False,
                        "decision_path": path,
                        "head_verdict": head_verdict, "head_confidence": head_conf},
            "review": {"required": review, "reason": reason,
                       "human_reviewed": False, "reviewer_verdict": None}}
