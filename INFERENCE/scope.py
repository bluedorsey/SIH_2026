"""The scope gate: is this a safety observation at all?

One logistic layer over the frozen sentence encoder, run BEFORE GLiNER. It answers a different
question from the prefilter head - "is this in our domain", not "is it severe" - which is why it
can gate and the prefilter cannot (prefilter recall_sif is 0.75; a gate at 0.75 kills one
precursor in four).

Fault-tolerant like everything else here: no model folder -> `available` False -> nothing is
ever rejected and the pipeline behaves exactly as it did before the gate existed.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .config import (EVIDENCE_GATE_ENABLED, EVIDENCE_GLINER_ROLES,
                     EVIDENCE_HEAD_MIN_CONFIDENCE, EVIDENCE_SIF_LIKE, GLINER_STRONG_SCORE, SCOPE_DIR,
                     SCOPE_ENABLED, SCOPE_SOFT_THRESHOLD, SCOPE_THRESHOLD, SCOPE_VETO_ROLES,
                     SCOPE_VETO_SOURCES)
from .knowledge import safety_vocab_hit

log = logging.getLogger("inference.scope")


class ScopeGate:
    def __init__(self) -> None:
        self.clf = None
        self.encoder = None
        self.available = False
        self.threshold = SCOPE_THRESHOLD
        self.enabled = SCOPE_ENABLED
        self.meta: dict = {}

    def load(self, encoder=None) -> "ScopeGate":
        """`encoder` re-uses the SentenceTransformer the heads already hold - the gate then costs
        one extra dot product, not a second 118M-parameter model in memory."""
        if self.clf is not None:
            return self
        d = Path(SCOPE_DIR)
        if not d.is_dir():
            log.info("no scope gate at %s - every report goes to the full pipeline", d)
            return self
        try:
            import joblib  # noqa: WPS433

            self.clf = joblib.load(d / "scope.joblib")
            mp = d / "scope_meta.json"
            self.meta = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
            # the threshold chosen against gold-180 at training time wins over the config default
            self.threshold = float(self.meta.get("threshold", SCOPE_THRESHOLD))
            self.enabled = bool(self.meta.get("scope_enabled", True)) and SCOPE_ENABLED
            self.encoder = encoder
            if self.encoder is None:
                from sentence_transformers import SentenceTransformer  # noqa: WPS433
                from .config import ENCODER_DIR  # noqa: WPS433
                self.encoder = SentenceTransformer(str(ENCODER_DIR), device="cpu")
            self.available = True
            log.info("scope gate loaded (threshold %.2f, enabled=%s)", self.threshold, self.enabled)
        except Exception as exc:                       # noqa: BLE001
            log.warning("scope gate not loadable: %s", str(exc)[:160])
            self.clf = None
        return self

    def p_out_of_scope(self, text: str) -> float | None:
        if not self.available:
            return None
        try:
            vec = self.encoder.encode([text], normalize_embeddings=True)
            proba = self.clf.predict_proba(vec)[0]
            col = list(self.clf.classes_).index(0)
            return float(proba[col])
        except Exception as exc:                       # noqa: BLE001
            log.warning("scope gate inference failed: %s", str(exc)[:140])
            return None

    def check(self, text: str, rule_spans: list[dict]) -> dict:
        """{'reject': bool, 'p_out_of_scope': float|None, 'reason': str, 'veto': str|None}

        Hard evidence (a safety-domain word or a hand-written release / outcome span) vetoes
        rejection whatever the score says. Both are regex and cost microseconds, so the veto is
        free and it is the layer a classifier cannot overrule."""
        p = self.p_out_of_scope(text) if self.enabled else None
        if p is None:
            return {"reject": False, "p_out_of_scope": None, "veto": None,
                    "reason": "scope gate unavailable" if self.enabled else "scope gate disabled"}
        veto = hard_evidence(text, rule_spans)
        if p <= self.threshold:
            return {"reject": False, "p_out_of_scope": round(p, 4), "veto": None,
                    "reason": f"in scope (p_out={p:.2f} <= {self.threshold:.2f})"}
        if veto:
            return {"reject": False, "p_out_of_scope": round(p, 4), "veto": veto,
                    "reason": f"gate said out of scope (p_out={p:.2f}) but {veto} "
                              f"vetoed it - hard evidence wins"}
        return {"reject": True, "p_out_of_scope": round(p, 4), "veto": None,
                "reason": f"not a safety observation (p_out={p:.2f} > {self.threshold:.2f}, "
                          f"no safety vocabulary, no hard rule span)"}


def hard_evidence(text: str, rule_spans: list[dict]) -> str | None:
    """The deterministic reason a text is a safety observation, or None.

    A safety-domain word (hazard, barrier, PPE, site or "unsafe"/"khatra" itself) or a
    hand-written release / outcome span. Generic negations ("nahi tha", "loose", "empty")
    are span roles but not evidence - "Mess mein paratha nahi tha" is a control_absent span
    and not a safety report. Mined-lexicon spans never count."""
    word = safety_vocab_hit(text)
    if word:
        return f"safety vocabulary {word!r}"
    for s in rule_spans:
        if (s["role"] in SCOPE_VETO_ROLES + ("energy_cue",)
                and s.get("source", "rules") in SCOPE_VETO_SOURCES
                and not _GENERIC.fullmatch(s["text"].strip())):
            return f"rule span {s['role']}={s['text']!r}"
    return None


# span texts the hand-written patterns produce that say nothing about the domain: a bare
# Hinglish negation, "bina <anything>", and the state words of control_ineffective. A span that
# names its barrier ("harness nahi", "not isolated") is caught by SAFETY_VOCAB before this runs.
_GENERIC = re.compile(
    r"(?:nahi|nai|nahin)\s+(?:tha|thi|the|kiya|liya|hua|hui)|bina(?:\s+\w+){0,3}|"
    r"almost|nearly|about to|abhi tak|loose|empty|expired|overdue|partially|damaged|"
    r"defective|missing|removed|disabled|discharged|blocked|jam(?:med)?|broken|dheela", re.I)


# A report that says nothing at all: a placeholder, a pointer to an attachment, or a handful of
# words. These are NOT out of scope - they are unscorable, and the tree already routes them to
# INSUFFICIENT -> human review, which is the right queue for them. Dismissing them as
# OUT_OF_SCOPE would quietly close the one case where a person genuinely has to open the record.
_UNSCORABLE = re.compile(
    r"^\W*(nil|na|n\.?a\.?|none|kuch nahi|same as above|as per (?:annexure|attached|above)|"
    r"refer (?:to )?(?:attach|annex)\w*|photo|screenshot|image|attach\w*|dekh\w* attach\w*)\b",
    re.I)


def is_unscorable(text: str) -> bool:
    """True for a report with no describable content - a placeholder or three stray words."""
    return bool(_UNSCORABLE.match(text.strip())) or len(text.split()) <= 3


def evidence_check(text: str, scope: dict, rule_spans: list[dict], gliner_spans: list[dict],
                   energy: dict, head_pred: dict, hazard_name: str | None = None) -> dict | None:
    """Second look at a row the scope gate let through. Returns None to keep the row, or a
    scope block ({'reject': True, ...}) when nothing downstream corroborates that the text is a
    safety observation.

    Everything here is fault-tolerant in the same direction as the gate: no gate score, no
    heads, or the kill switch off -> None, and the pipeline behaves exactly as before."""
    if not EVIDENCE_GATE_ENABLED or not scope or scope.get("reject"):
        return None
    p = scope.get("p_out_of_scope")
    if p is None or p < SCOPE_SOFT_THRESHOLD:
        return None                                    # the gate vouches for this row
    if not head_pred:
        return None                                    # nobody downstream to say "no"
    if is_unscorable(text):
        return None                                    # empty report, not an off-domain one

    evidence: list[str] = []
    # 1. deterministic: a safety-domain word, or a hand-written release / outcome span. The
    #    mined lexicon is deliberately NOT evidence: it fires on "paper", "kaam" and
    #    "housekeeping" and would corroborate every canteen complaint.
    hard = hard_evidence(text, rule_spans)
    if hard:
        evidence.append(hard)
    if hazard_name:
        evidence.append(f"hazard {hazard_name}")
    # 2. a number with a unit answered question 1 outright
    if energy.get("gate") in ("EXCEEDS", "BELOW"):
        evidence.append(f"numeric energy gate {energy['gate']}")
    # 3. GLiNER only counts when it is sure AND the role means something
    strong = [g for g in gliner_spans if float(g.get("score", 0.0)) >= GLINER_STRONG_SCORE
              and g["role"] in EVIDENCE_GLINER_ROLES]
    if strong:
        g = max(strong, key=lambda s: s.get("score", 0.0))
        evidence.append(f"gliner {g['role']}={g['text']!r}@{g['score']:.2f}")
    # 4. either sentence head thinks this could be a precursor
    pf = head_pred.get("prefilter") or {}
    if str(pf.get("label")) == "1":
        evidence.append(f"prefilter head says SIF@{pf.get('confidence')}")
    vh = head_pred.get("verdict") or {}
    if (vh.get("label") in EVIDENCE_SIF_LIKE
            and (vh.get("confidence") or 0.0) >= EVIDENCE_HEAD_MIN_CONFIDENCE):
        evidence.append(f"verdict head says {vh['label']}@{vh.get('confidence')}")
    if evidence:
        return None

    best = max((float(g.get("score", 0.0)) for g in gliner_spans
                if g["role"] in EVIDENCE_GLINER_ROLES), default=0.0)
    return {"reject": True, "p_out_of_scope": round(p, 4), "veto": None,
            "stage": "evidence_gate",
            "reason": (f"not a safety observation: p_out={p:.2f} >= {SCOPE_SOFT_THRESHOLD:.2f} and "
                       f"nothing corroborates it (no safety vocabulary, no hard rule span, no numeric "
                       f"energy, best GLiNER span {best:.2f} < {GLINER_STRONG_SCORE:.2f}, "
                       f"prefilter={pf.get('label')}@{pf.get('confidence')}, "
                       f"verdict head={vh.get('label')}@{vh.get('confidence')})")}


_GATE: ScopeGate | None = None


def get_scope_gate(encoder=None) -> ScopeGate:
    global _GATE                                       # noqa: PLW0603
    if _GATE is None:
        _GATE = ScopeGate().load(encoder)
    return _GATE
