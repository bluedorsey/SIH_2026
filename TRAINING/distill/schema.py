"""
Validation of teacher output against prompts.md §0.

`validate_element(el)` -> (clean_row | None, problems[list[str]])

Checks (a row is REJECTED on any hard failure, soft issues are recorded in `row["issues"]`):
  hard - text present (>= 3 words), events non-empty
       - every role span / question span / barrier span is a VERBATIM substring of text (else the span is dropped;
         a role whose span is missing is a hard failure, question spans may be null)
       - role names, question keys/values, barrier names/status, verdict, statement_type in the §0 vocabularies
       - spans <= MAX_SPAN_TOKENS words (GLiNER max_width)
       - the verdict recomputed from the four questions by the EEI rules (`rules_verdict`) must agree with the
         teacher's verdict (a mismatch means the teacher contradicted itself - drop, do not "fix")
  soft - rationale should quote at least one span verbatim; PPE barriers must be `pseudo`; life_saving_rules
         are canonicalised (Lifting Operations -> Safe Mechanical Lifting); energy_types limited to the list.

Also produces char offsets for every kept span (`spans` = [{role, text, start, end}]) - GLiNER data prep uses them.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.distill"  # noqa: A001

from ..config import (  # noqa: E402
    BARRIER_STATUS, BARRIERS, ENERGY_TYPES, LSR_NAMES, MAX_SPAN_TOKENS, MAX_TEXT_TOKENS, QUESTIONS, ROLES, STATEMENT_TYPES, VERDICTS,
)

try:  # reuse CLEANING's Life-Saving-Rule canonicaliser
    from CLEANING.common.lsr import canonical_lsr_list  # noqa: E402
except Exception:  # noqa: BLE001 - CLEANING not importable (e.g. Colab with only TRAINING copied)
    def canonical_lsr_list(raw):  # type: ignore
        parts = raw if isinstance(raw, list) else [raw]
        out, un = [], []
        for p in parts:
            p = str(p).strip()
            hit = next((n for n in LSR_NAMES if n.lower() == p.lower()), None)
            if p.lower() in ("lifting operations", "lifting"):
                hit = "Safe Mechanical Lifting"
            if p.lower() == "work authorization":
                hit = "Work Authorisation"
            (out.append(hit) if hit and hit not in out else un.append(p)) if p else None
        return out, un

# GLiNER's default splitter is r"\w+(?:[-_]\w+)*|\S"; \w does NOT cover Devanagari/Bengali vowel signs (category Mc/Mn),
# which would split "मिस्त्री" into several tokens. This Indic-aware variant is used here AND at training/inference
# (TRAINING/finetune/tokenization.py) so span widths mean the same thing everywhere.
_WORD_RE = re.compile(r"[\w\u0900-\u097F\u0980-\u09FF]+(?:[-_][\w\u0900-\u097F\u0980-\u09FF]+)*|\S", re.UNICODE)


def n_tokens(s: str) -> int:
    return len(_WORD_RE.findall(s or ""))


def _find_span(text: str, span: str) -> tuple[int, int] | None:
    """Exact substring first; then whitespace-tolerant; then case-insensitive. None if absent."""
    if not span or not isinstance(span, str):
        return None
    i = text.find(span)
    if i >= 0:
        return i, i + len(span)
    pat = r"\s+".join(re.escape(w) for w in span.split())
    m = re.search(pat, text)
    if m:
        return m.start(), m.end()
    m = re.search(pat, text, re.I)
    if m:
        return m.start(), m.end()
    # "operator ... exposure me aa sakta hai": the teacher abbreviated a span with an ellipsis -> take prefix..suffix
    parts = [x.strip() for x in re.split(r"\s*(?:\.\.\.|…)\s*", span) if x.strip()]
    if len(parts) >= 2:
        a = _find_span(text, parts[0])
        if a:
            b = _find_span(text[a[1]:], parts[-1])
            if b:
                return a[0], a[1] + b[1]
    return None


# statement_cue must mark a hypothetical / historical / training / closed-action signal - teachers like to tag the
# location phrase ("Derrick floor pe", "Flare area pe") with it, which would teach GLiNER the wrong thing
_STATEMENT_MARKER_RE = re.compile(
    r"\b(agar|if|could|would|might|may|had|ho sakta|ho sakti|hota|hoti|kya hoga|suppose|hypothetic\w*|"
    r"last (?:year|month|week)|pichle|pichhle|purana|earlier|previous\w*|in 20\d\d|20\d\d me|"
    r"training|mock|drill|tbt|toolbox|example|udaharan|scenario|"
    r"closed|completed|rectified|repaired|replaced|fixed|done|ho gaya|kar diya gaya|action taken|corrective|"
    r"yaad|remember|recalled|dekha tha|hua tha|thi jab)\b", re.I)
_CONTROL_ROLES = {"control_present", "control_absent", "control_ineffective", "pseudo_control"}


# teacher models invent barrier names freely - fold the common ones onto the taxonomy instead of dropping them
BARRIER_ALIASES = {
    "work_authorisation": "ptw", "work_authorization": "ptw", "permit": "ptw", "permit_to_work": "ptw", "work_permit": "ptw",
    "sop": "ptw", "procedure": "ptw", "jsa": "ptw", "risk_assessment": "ptw", "toolbox_talk": "ppe", "training": "ppe",
    "supervision": "ppe", "competent_person": "ppe", "banksman": "exclusion_zone", "spotter": "exclusion_zone",
    "harness": "fall_arrest", "fall_protection": "fall_arrest", "lifeline": "fall_arrest", "guardrail": "fall_arrest",
    "edge_protection": "fall_arrest", "scaffold_tagging": "fall_arrest",
    "barricade": "drop_zone_barricade", "barrication": "drop_zone_barricade", "hard_barricade": "drop_zone_barricade",
    "drop_zone": "drop_zone_barricade", "cordon": "exclusion_zone", "exclusion": "exclusion_zone",
    "loto": "energy_isolation", "lockout": "energy_isolation", "isolation": "energy_isolation", "lock_out_tag_out": "energy_isolation",
    "guard": "machine_guard", "guarding": "machine_guard", "interlock": "machine_guard",
    "gas_testing": "gas_test", "gas_detector": "gas_test", "gas_monitoring": "gas_test",
    "confined_space_permit": "entry_permit", "confined_space_entry_permit": "entry_permit",
    "lift_plan": "lifting_plan", "lifting_plan_and_rigging": "lifting_plan", "rigging": "lifting_plan", "sling_inspection": "lifting_plan",
    "hot_work": "hot_work_permit", "fire_watch": "hot_work_permit", "tool_tether": "tool_lanyard", "lanyard": "tool_lanyard",
}
# an actual serious injury stated in the text while the teacher answered serious_injury=false -> hard reject
_SERIOUS_RE = re.compile(
    r"\b(fatal(?:ity|ities|ly)?|died|death|killed|amputat\w*|fractur\w*|broke(?:n)?\s+(?:\w+\s+){0,3}?"
    r"(?:leg|arm|tibia|fibula|femur|skull|pelvis|hip|spine|back|neck|ribs?|wrist|ankle|jaw|collar ?bone|bones?)\b|"
    r"unconscious|concussion|hospitali[sz]ed|admitted to (?:the )?hospital|surgery|third[- ]degree|second[- ]degree|"
    r"crushed (?:his |her |their |the )?(?:head|chest|pelvis|torso|abdomen)|electrocut\w*|asphyxiat\w*|"
    r"maut|mar gaya|mrityu|haddi toot)", re.I)
_DIGIT_ONLY_RE = re.compile(r"\b(finger|fingertip|thumb|toe|pinky|digit)s?\b", re.I)
_NO_INJURY_RE = re.compile(r"\b(no (?:one was )?(?:injur\w*|hurt)|uninjured|koi chot nahi|first aid only|could have|would have|might have|potential(?:ly)?|"
                           r"agar|ho sakta|last year|pichle saal|in 20\d\d|training|drill|mock)\b", re.I)

def rules_verdict(q: dict, statement_type: str) -> str | None:
    """EEI decision tree from the four questions (mirrors §0). Returns None when it cannot decide."""
    if statement_type in ("hypothetical", "historical", "training_example"):
        return "NON_EVENT"
    he = q["high_energy_present"]["value"]
    rel = q["energy_released"]["value"]
    inj = q["serious_injury"]["value"]
    ctl = q["direct_control_present"]["value"]
    if he == "unknown":
        return "INSUFFICIENT"
    if he is False:
        if inj is True:
            return "L_SIF"
        return "LOW_ENERGY"          # unknown injury with no high energy is safely LOW_ENERGY
    # high energy present
    if rel == "unknown":
        return "INSUFFICIENT"
    if rel is True:
        if inj is True:
            return "H_SIF"
        if inj == "unknown":
            return "INSUFFICIENT"
        if ctl is True:
            return "CAPACITY"
        if ctl is False:
            return "P_SIF"
        return "INSUFFICIENT"
    # not released
    if statement_type == "corrective_completed":
        return None                  # exposure unknown by definition -> accept teacher's EXPOSURE / SUCCESS / INSUFFICIENT
    if ctl is True:
        return "SUCCESS"
    if ctl is False:
        return "EXPOSURE"
    return "INSUFFICIENT"


def _norm_value(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "yes"):
            return True
        if s in ("false", "no"):
            return False
        if s in ("unknown", "unclear", "null", "none", ""):
            return "unknown"
    if v is None:
        return "unknown"
    return None


def validate_element(el: dict, *, source: str = "", teacher: str = "", model: str = "", batch_id: str = "",
                     seed_id: str | None = None, input_id: str | None = None) -> tuple[dict | None, list[str]]:
    problems: list[str] = []
    issues: list[str] = []
    if not isinstance(el, dict):
        return None, ["element is not an object"]
    text = el.get("text")
    if not isinstance(text, str) or n_tokens(text) < 3:
        return None, ["text missing or < 3 words"]
    text = text.strip()
    if n_tokens(text) > MAX_TEXT_TOKENS:
        problems.append(f"text longer than {MAX_TEXT_TOKENS} tokens")
    events = el.get("events")
    if not isinstance(events, list) or not events:
        return None, ["events missing"]

    clean_events: list[dict] = []
    all_spans: list[dict] = []
    for ei, ev in enumerate(events):
        if not isinstance(ev, dict):
            problems.append(f"event {ei} not an object")
            continue
        # ---- roles
        roles_out: list[dict] = []
        for r in ev.get("roles") or []:
            if not isinstance(r, dict):
                continue
            role, span = r.get("role"), r.get("span")
            if role not in ROLES:
                issues.append(f"unknown role {role!r} dropped")
                continue
            pos = _find_span(text, span) if isinstance(span, str) else None
            if pos is None:
                problems.append(f"role {role} span not in text: {str(span)[:40]!r}")
                continue
            if n_tokens(text[pos[0]:pos[1]]) > MAX_SPAN_TOKENS:
                problems.append(f"role {role} span > {MAX_SPAN_TOKENS} tokens")
                continue
            if role == "statement_cue" and not _STATEMENT_MARKER_RE.search(text[pos[0]:pos[1]]):
                issues.append(f"statement_cue without a marker dropped: {text[pos[0]:pos[1]][:40]!r}")
                continue
            roles_out.append({"role": role, "span": text[pos[0]:pos[1]], "start": pos[0], "end": pos[1]})
        # the same span tagged as energy_cue AND as a control (e.g. "SCBA pehna tha") - PPE/controls are not energy
        ctl_spans = {(r["start"], r["end"]) for r in roles_out if r["role"] in _CONTROL_ROLES}
        if ctl_spans:
            before = len(roles_out)
            roles_out = [r for r in roles_out if not (r["role"] == "energy_cue" and (r["start"], r["end"]) in ctl_spans)]
            if len(roles_out) < before:
                issues.append("energy_cue on a control span dropped")
        # a repeated short span (e.g. "not", "nahi") is anchored inside another role span of the same event when possible
        for r in roles_out:
            occ = [m.start() for m in re.finditer(re.escape(r["span"]), text)]
            if len(occ) > 1:
                hosts = [(o["start"], o["end"]) for o in roles_out if o is not r and o["end"] - o["start"] > len(r["span"])]
                inside = [o for o in occ if any(a <= o and o + len(r["span"]) <= b for a, b in hosts)]
                if inside:
                    r["start"], r["end"] = inside[0], inside[0] + len(r["span"])
                    r["span"] = text[r["start"]:r["end"]]
        # ---- questions
        q_in = ev.get("questions") or {}
        q_out: dict = {}
        for qk in QUESTIONS:
            qv = q_in.get(qk)
            if not isinstance(qv, dict):
                problems.append(f"question {qk} missing")
                q_out[qk] = {"value": "unknown", "span": None}
                continue
            val = _norm_value(qv.get("value"))
            if val is None:
                problems.append(f"question {qk} value invalid {qv.get('value')!r}")
                val = "unknown"
            span = qv.get("span")
            pos = _find_span(text, span) if isinstance(span, str) else None
            if isinstance(span, str) and span and pos is None:
                issues.append(f"question {qk} span not in text -> null")
            q_out[qk] = {"value": val, "span": text[pos[0]:pos[1]] if pos else None,
                         "start": pos[0] if pos else None, "end": pos[1] if pos else None}
        # a stated serious injury (fracture, amputation, fatality ...) answered as serious_injury=false is the most
        # damaging teacher error for this task (it turns H_SIF into P_SIF) -> hard reject so the row is re-done / dropped
        if q_out["serious_injury"]["value"] is False and _NO_INJURY_RE.search(text) is None:
            m = _SERIOUS_RE.search(text)
            if m and not (m.group(0).lower().startswith(("fractur", "broke")) and _DIGIT_ONLY_RE.search(text[m.end():m.end() + 40])):
                problems.append(f"serious_injury=false but text states {m.group(0)!r}")
        # ---- barriers
        b_out: list[dict] = []
        for b in ev.get("barriers") or []:
            if not isinstance(b, dict):
                continue
            name, status, span = b.get("barrier"), b.get("status"), b.get("span")
            key = str(name).strip().lower().replace(" ", "_").replace("-", "_")
            name = key if key in BARRIERS else BARRIER_ALIASES.get(key, name)
            if name not in BARRIERS:
                issues.append(f"unknown barrier {key!r} dropped")
                continue
            if status not in BARRIER_STATUS:
                issues.append(f"barrier {name} status {status!r} invalid -> dropped")
                continue
            if name == "ppe" and status != "pseudo":
                issues.append("ppe barrier forced to pseudo")
                status = "pseudo"
            pos = _find_span(text, span) if isinstance(span, str) else None
            b_out.append({"barrier": name, "status": status, "span": text[pos[0]:pos[1]] if pos else None,
                          "start": pos[0] if pos else None, "end": pos[1] if pos else None})
        # ---- categorical
        st = str(ev.get("statement_type") or "").strip().lower()
        if st not in STATEMENT_TYPES:
            problems.append(f"statement_type invalid {st!r}")
            st = "observed"
        verdict = str(ev.get("verdict") or "").strip().upper()
        if verdict not in VERDICTS:
            problems.append(f"verdict invalid {verdict!r}")
        energy = [e for e in (ev.get("energy_types") or []) if isinstance(e, str) and e.lower() in ENERGY_TYPES]
        energy = [e.lower() for e in energy]
        lsr, unmapped = canonical_lsr_list(ev.get("life_saving_rules") or [])
        if unmapped:
            issues.append("lsr unmapped: " + "|".join(map(str, unmapped)))
        rationale = ev.get("rationale_one_line")
        if isinstance(rationale, str) and rationale.strip():
            quoted = re.findall(r'"([^"]{3,})"', rationale)
            if not any(qq in text for qq in quoted) and not any(r["span"] in rationale for r in roles_out):
                issues.append("rationale quotes no span")
        else:
            rationale = None
        # ---- consistency: rules verdict vs teacher verdict
        rv = rules_verdict(q_out, st)
        if verdict in VERDICTS:
            if rv is None:
                if verdict not in ("EXPOSURE", "SUCCESS", "INSUFFICIENT"):
                    problems.append(f"corrective_completed verdict {verdict} not allowed")
            elif rv != verdict:
                # NON_EVENT is also legitimate for duplicates / "no hazard described" when no high energy
                if not (verdict == "NON_EVENT" and rv == "LOW_ENERGY"):
                    problems.append(f"verdict {verdict} contradicts questions ({rv})")
        # ---- hard: an event with no roles at all cannot train GLiNER
        if not roles_out and verdict not in ("NON_EVENT", "INSUFFICIENT", "LOW_ENERGY"):
            problems.append("no valid role spans")
        clean_events.append({
            "roles": roles_out, "questions": q_out, "barriers": b_out, "energy_types": energy,
            "life_saving_rules": lsr, "statement_type": st, "verdict": verdict, "rules_verdict": rv,
            "rationale_one_line": rationale,
        })
        all_spans += [{"role": r["role"], "text": r["span"], "start": r["start"], "end": r["end"]} for r in roles_out]

    if problems:
        return None, problems
    meta = el.get("meta") if isinstance(el.get("meta"), dict) else {}
    primary = clean_events[0]
    row = {
        "text": text,
        "meta": {k: meta.get(k) for k in ("site", "location", "activity", "shift", "lang", "trap")},
        "events": clean_events,
        "spans": all_spans,
        "verdict": primary["verdict"],
        "statement_type": primary["statement_type"],
        "life_saving_rules": sorted({l for e in clean_events for l in e["life_saving_rules"]}),
        "energy_types": sorted({x for e in clean_events for x in e["energy_types"]}),
        "n_events": len(clean_events),
        "source": source, "teacher": teacher, "model": model, "batch_id": batch_id,
        "seed_id": seed_id, "input_id": input_id,
        "issues": issues,
    }
    return row, []


def validate_many(elements: list, **kw) -> tuple[list[dict], list[dict]]:
    ok, bad = [], []
    for i, el in enumerate(elements if isinstance(elements, list) else []):
        row, probs = validate_element(el, **kw)
        if row:
            row["batch_pos"] = i
            ok.append(row)
        else:
            bad.append({"batch_pos": i, "problems": probs, "text": (el.get("text") if isinstance(el, dict) else None), **{k: kw.get(k) for k in ("batch_id", "teacher", "model")}})
    return ok, bad
