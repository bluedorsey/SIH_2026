"""The one entry point: text in, the SIF-precursor JSON out.

    from INFERENCE.pipeline import analyse
    analyse("Monkey board se tool box neeche gira...", report_id="OIL-ASM-2026-04412")
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import logging

from . import __version__
from .config import (MAX_TEXT_CHARS, PIPELINE_VERSION, SEMANTIC_GLINER_ASSIST_SCORE,
                     SPAN_THRESHOLD)
from .decide import decide, fuse_spans
from .energy import estimate
from .harm import detect_harm
from .knowledge import detect_hazard
from .models import get_extractor, get_heads
from .normalise import normalise
from .scope import evidence_check, get_scope_gate
from .semantic import get_semantic, hazard_entry
from .uc_ua import classify as classify_uc_ua
from .rules import detect_language, detect_statement_type, find_spans, negation_scope

log = logging.getLogger("inference.pipeline")


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def analyse(text: str, *, report_id: str | None = None, meta: dict | None = None,
            use_models: bool = True) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    original = text.strip()[:MAX_TEXT_CHARS]
    meta = dict(meta or {})

    # ---- layer 0: spelling. Every layer below matches on the normalised text ("permited" ->
    # "permitted", "jl gya" -> "jal gaya"); every offset is mapped back to `original` at the end
    # so the UI highlights what the reporter actually typed.
    norm = normalise(original)
    text = norm.text

    # ---- layer 1: deterministic
    language = detect_language(text)
    statement_type = detect_statement_type(text)
    rule_spans = find_spans(text)

    # ---- layer 1b: scope gate. Cheapest question first - is this a safety report at all?
    # Rejected rows skip GLiNER entirely, which is most of the compute when real traffic is
    # mostly mundane. Rejection is a verdict, never a deletion: the row keeps the full contract
    # and stays auditable, it just leaves the human queue.
    heads_for_scope = get_heads() if use_models else None
    gate = get_scope_gate((heads_for_scope.bundle or {}).get("encoder")
                          if (heads_for_scope and heads_for_scope.available) else None) if use_models else None
    scope = gate.check(text, rule_spans) if gate else {"reject": False, "p_out_of_scope": None,
                                                      "veto": None, "reason": "models disabled"}
    if scope["reject"]:
        return _restore(_out_of_scope(text, report_id, meta, language, statement_type, rule_spans,
                                      scope, heads_for_scope, gate), norm)

    # ---- layer 2: GLiNER spans. Asked once at the lower "assist" threshold; only spans at or
    # above SPAN_THRESHOLD enter the tree on their own.
    extractor = get_extractor() if use_models else None
    gliner_raw = (extractor.spans(text, threshold=min(SPAN_THRESHOLD, SEMANTIC_GLINER_ASSIST_SCORE))
                  if (extractor and extractor.available) else [])
    gliner_spans = [g for g in gliner_raw if g.get("score", 0.0) >= SPAN_THRESHOLD]

    # ---- layer 3: sentence heads
    heads = heads_for_scope if use_models else None
    head_pred = heads.predict(text) if (heads and heads.available) else {}

    # ---- knowledge + energy. Regex first; when no list names the hazard, the semantic layer
    # types it by meaning on the same encoder ("sulphur ki gas", "garam steam", "गैस लीक").
    hazard_name, hazard = detect_hazard(text)
    sem, sem_available = None, False
    if use_models:
        semantic = get_semantic((heads.bundle or {}).get("encoder") if (heads and heads.available) else None)
        sem_available = semantic.available
        sem = semantic.match(text) if sem_available else None
    # Similarity says which energy a sentence is ABOUT, not that the energy was large: a stair
    # slip scored 0.82 against excavation. So the semantic answer only counts when GLiNER
    # independently sees an energy span in the text, even a weak one - two weak signals that
    # agree, never one alone. Uncorroborated, it is reported in `semantic` and nothing more.
    weak = [g for g in gliner_raw if g["role"] == "energy_cue"] if sem else []
    sem_ok = sem if weak else None
    if hazard_name is None and sem_ok:
        hazard_name, hazard = sem_ok["hazard"], hazard_entry(sem_ok["hazard"])
    if sem_ok and not any(g["role"] == "energy_cue" for g in gliner_spans) \
            and not any(r["role"] == "energy_cue" for r in rule_spans):
        g = max(weak, key=lambda x: x.get("score", 0.0))
        gliner_spans.append({**g, "source": "gliner+semantic"})
    spans = fuse_spans(rule_spans, gliner_spans)
    neg = negation_scope(text, spans)
    energy = estimate(text, hazard.get("energy_type"))

    # ---- harm: what happened to which body part. Feeds question 3 and the highlighted text.
    harm = detect_harm(text, hazard.get("energy_type"))
    for hm in harm["harms"]:
        if not any(s["role"] == "outcome_cue" and s["start"] < hm["end"] and hm["start"] < s["end"] for s in spans):
            spans.append({"role": "outcome_cue", "text": hm["text"], "start": hm["start"], "end": hm["end"],
                          "source": "rules:harm", "score": 1.0})
    spans.sort(key=lambda s: (s["start"], s["end"]))

    # ---- layer 3b: evidence gate. The scope gate said "probably not ours" but not loudly
    # enough to reject on its own. Now that every cheap layer has looked, dismiss the row if
    # none of them found anything - otherwise a lone GLiNER span becomes EXPOSURE and a human
    # is asked to review an AC-remote complaint.
    dismissed = evidence_check(text, scope, rule_spans, gliner_spans, energy, head_pred, hazard_name,
                               semantic=sem_ok)
    if dismissed:
        return _restore(_out_of_scope(text, report_id, meta, language, statement_type, spans, dismissed,
                                      heads, gate, extractor=extractor, head_pred=head_pred), norm)

    # ---- UC / UA (SIH26165 deliverable) - independent of the verdict: the verdict says how
    # bad this could be, UC/UA says what kind of finding it is and who owns the fix.
    ucua = classify_uc_ua(text, spans)

    # ---- fuse -> verdict
    d = decide(text, spans, energy, neg, statement_type, head_pred, semantic=sem_ok, harm=harm)

    facts = d["questions"]
    return _restore({
        "report_id": report_id or "SIF-" + hashlib.sha1(original.encode("utf-8")).hexdigest()[:12],
        "input": {"text": text, "chars": len(text)},
        "meta": {**{"site": None, "date": None, "activity": None, "department": None}, **meta,
                 "language_detected": language, "statement_type": statement_type},
        "verdict": d["verdict"],
        "eei_facts": facts,
        "energy": energy,
        "safety_knowledge": {
            "hazard": hazard_name,
            "barrier": hazard.get("barrier"),
            "barrier_failure_mode": _failure_mode(spans, facts),
            "lsr": _lsr(hazard, head_pred),
            "potential_consequence": hazard.get("consequence"),
            "precursor_cluster": hazard.get("cluster"),
        },
        "spans": [{"role": s["role"], "text": s["text"], "start": s["start"], "end": s["end"],
                   "source": s.get("source", "rules"), "score": round(float(s.get("score", 1.0)), 3)}
                  for s in spans],
        "traps_checked": neg,
        "uc_ua": ucua,
        "harm": harm,
        "semantic": ({**sem, "corroborated": sem_ok is not None} if sem else None),
        "scope": scope,
        "review": d["review"],
        "provenance": {
            "pipeline_version": PIPELINE_VERSION,
            "package_version": __version__,
            "models": {
                "gliner": (extractor.source if extractor and extractor.available else None),
                "heads": (",".join(heads.names) if heads and heads.available else None),
                "semantic": ("prototype_similarity" if sem_available else None),
                "llm": None,
            },
            "head_predictions": {k: {"label": v["label"], "confidence": v["confidence"]}
                                 for k, v in head_pred.items()},
            "normalisation": norm.changes,
            "processed_at": _now(),
        },
    }, norm)


def _restore(resp: dict, norm) -> dict:
    """Map every offset from the normalised text back onto the original, and show the original
    words. The reporter typed "permited"; the highlight must land on "permited"."""
    resp["input"]["text"] = norm.original
    resp["input"]["chars"] = len(norm.original)
    if not norm.changes:
        return resp

    def fix(obj: dict, ks: str, ke: str, kt: str | None) -> None:
        if obj.get(ks) is None or obj.get(ke) is None:
            return
        s0, e0, t = norm.restore(obj[ks], obj[ke])
        obj[ks], obj[ke] = s0, e0
        if kt:
            obj[kt] = t

    for sp in resp.get("spans", []):
        fix(sp, "start", "end", "text")
    for f in (resp.get("eei_facts") or {}).values():
        fix(f, "span_start", "span_end", "span")
    for key in ("act_cues", "condition_cues"):
        for c in (resp.get("uc_ua") or {}).get(key, []) or []:
            fix(c, "start", "end", "text")
    hm = resp.get("harm") or {}
    seen: set[int] = set()
    for h in list(hm.get("harms", [])) + ([hm["worst"]] if hm.get("worst") else []):
        if id(h) in seen:
            continue                                    # `worst` IS one of `harms`: map it once
        seen.add(id(h))
        fix(h, "start", "end", "text")
        fix(h, "body_part_start", "body_part_end", "body_part_text")
    return resp


def _failure_mode(spans: list[dict], facts: dict) -> str | None:
    if any(s["role"] == "control_ineffective" for s in spans):
        return "present_but_degraded"
    if any(s["role"] == "pseudo_control" for s in spans) and facts["direct_control_present"]["value"] is False:
        return "pseudo_control_only"
    ctl = facts["direct_control_present"]["value"]
    if ctl is False:
        return "not_established"
    if ctl is True:
        return "effective"
    return None


def _lsr(hazard: dict, head_pred: dict) -> list[str]:
    """Knowledge-base rules first; the LSR head adds anything it is confident about."""
    out = list(hazard.get("lsr") or [])
    h = head_pred.get("lsr") or {}
    lbl = h.get("label")
    if lbl and (h.get("confidence") or 0) >= 0.5:
        for part in (lbl if isinstance(lbl, list) else [lbl]):
            key = str(part).strip().lower().replace(" ", "_")
            if key and key not in out:
                out.append(key)
    return out


def _out_of_scope(text, report_id, meta, language, statement_type, rule_spans, scope,
                  heads, gate, extractor=None, head_pred=None) -> dict:
    """Same contract, verdict OUT_OF_SCOPE. The tree never ran, so every EEI fact is "not
    asked" rather than a fabricated default. Rejected by the scope gate: no model ran either
    and every model field is null. Rejected by the evidence gate: GLiNER and the heads DID run
    and found nothing - their output is kept so a reviewer can audit the dismissal."""
    stage = scope.get("stage", "scope_gate")
    unknown = {"value": "unknown", "span": None, "span_start": None, "span_end": None,
               "source": f"not_asked({stage})"}
    head_pred = head_pred or {}
    layers = (["scope_gate", "rules", "gliner", "setfit"] if stage == "evidence_gate"
              else ["scope_gate"])
    return {
        "report_id": report_id or "SIF-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:12],
        "input": {"text": text, "chars": len(text)},
        "meta": {**{"site": None, "date": None, "activity": None, "department": None}, **meta,
                 "language_detected": language, "statement_type": statement_type},
        "verdict": {"label": "OUT_OF_SCOPE",
                    "confidence": round(scope["p_out_of_scope"] or 0.0, 3),
                    "conformal_set": ["OUT_OF_SCOPE"],
                    "route": "gated",
                    "layers_agreed": layers,
                    "llm_invoked": False,
                    "decision_path": f"{stage} -> OUT_OF_SCOPE ({scope['reason']})",
                    "head_verdict": (head_pred.get("verdict") or {}).get("label"),
                    "head_confidence": (head_pred.get("verdict") or {}).get("confidence")},
        "eei_facts": {"high_energy_present": dict(unknown), "energy_released": dict(unknown),
                      "serious_injury": dict(unknown), "direct_control_present": dict(unknown)},
        "energy": {"type": None, "estimate_j": None, "range_j": None, "basis": None,
                   "formula": None, "inputs": {}, "threshold_j": None, "gate": "NOT_ASSESSED"},
        "safety_knowledge": {"hazard": None, "barrier": None, "barrier_failure_mode": None,
                             "lsr": [], "potential_consequence": None, "precursor_cluster": None},
        "spans": [{"role": s["role"], "text": s["text"], "start": s["start"], "end": s["end"],
                   "source": s.get("source", "rules"), "score": round(float(s.get("score", 1.0)), 3)}
                  for s in rule_spans],
        "traps_checked": {"negation_detected": False, "negation_scope": None, "note": None},
        "uc_ua": {"labels": [], "unsafe_act": False, "unsafe_condition": False,
                  "confidence": 0.0, "act_cues": [], "condition_cues": [], "actor": None,
                  "passive_victim": False, "basis": f"not_assessed({stage})"},
        "harm": {"harms": [], "serious": False, "worst": None},
        "semantic": None,
        "scope": scope,
        "review": {"required": False, "reason": None, "human_reviewed": False, "reviewer_verdict": None},
        "provenance": {
            "pipeline_version": PIPELINE_VERSION, "package_version": __version__,
            "models": {"gliner": (extractor.source if extractor and extractor.available else None),
                       "heads": (",".join(heads.names) if heads and heads.available else None),
                       "llm": None,
                       "scope_gate": (f"threshold={gate.threshold}" if gate and gate.available else None)},
            "head_predictions": {k: {"label": v["label"], "confidence": v["confidence"]}
                                 for k, v in head_pred.items()},
            "normalisation": [],
            "processed_at": _now(),
        },
    }
