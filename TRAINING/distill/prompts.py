"""
Loads prompts.md (repo root) and builds the chat messages for each job.

prompts.md layout (unchanged from the repo):
  ## §0  -> one fenced block  = shared label spec (system prompt core)
  ## §1  -> block[0] system addendum, block[1] user template   (GENERATE)
  ## §2  -> block[0] system addendum, block[1] user template   (REWIND)
  ## §3  -> block[0] system addendum, block[1] user template   (LABEL)
  ## Two examples ... -> ```json blocks = few-shot examples
The OIL context (config.OIL_CONTEXT) and the few-shot examples are appended to every system prompt.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from ..config import EXEMPLARS, GENERATE_LSR_FOCUS_MIN, LANG_MIXES, LSR_FOCUS_ROTATION, OIL_CONTEXT, PROMPTS_MD

_FENCE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.S)


@lru_cache(maxsize=1)
def load_prompts(path: Path = PROMPTS_MD) -> dict:
    text = path.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    current = "_pre"
    for line in text.splitlines(keepends=True):
        m = re.match(r"^## (§\d|Two examples|How the outputs)", line)
        if m:
            current = m.group(1)
        sections[current] = sections.get(current, "") + line
    blocks = {k: _FENCE.findall(v) for k, v in sections.items()}
    if "§0" not in blocks or not blocks["§0"]:
        raise SystemExit(f"could not find the §0 block in {path}")
    out = {
        "spec": blocks["§0"][0].strip(),
        "generate_system": blocks.get("§1", [""])[0].strip(),
        "generate_user": (blocks.get("§1", ["", ""]) + [""])[1].strip(),
        "rewind_system": blocks.get("§2", [""])[0].strip(),
        "label_system": blocks.get("§3", [""])[0].strip(),
        "examples": [b.strip() for b in blocks.get("Two examples", []) if b.strip().startswith("{")],
    }
    for k in ("generate_system", "rewind_system", "label_system"):
        if not out[k]:
            raise SystemExit(f"prompts.md: missing block for {k}")
    return out


def _fewshot() -> str:
    ex = load_prompts()["examples"]
    if not ex:
        return ""
    return "\n\nFEW-SHOT EXAMPLES OF THE EXACT ELEMENT FORMAT (copy the structure, never the content):\n" + "\n".join(ex)


def _output_rule(kind: str) -> str:
    return {
        "array": ("\n\nOUTPUT RULE: reply with ONE JSON array and nothing else - no prose, no markdown fences, no comments, "
                  "no thinking out loud. The very first character of your reply must be '[' and the last must be ']'."),
        "object": "\n\nOUTPUT RULE: reply with ONE JSON object and nothing else - no prose, no markdown fences, no comments.",
    }[kind]


# --------------------------------------------------------------------------
# §1 GENERATE
# --------------------------------------------------------------------------
_LANG_KEYS = [("hinglish", r"(\d+)%\s*romani[sz]ed hinglish"), ("english", r"(\d+)%\s*(?:indian )?english"),
              ("hindi", r"(\d+)%\s*devanagari"), ("assamese_mix", r"(\d+)%\s*assamese")]
_LANG_LABEL = {"hinglish": "romanized Hinglish", "english": "Indian English", "hindi": "Devanagari Hindi script",
               "assamese_mix": "Assamese-English mix (romanized Assamese words: 'kora nohol', 'nasil', 'ase', 'cholise', 'bhitorot')"}


def language_plan(n: int, lang_mix: str) -> list[tuple[str, int, int]]:
    """Turn '40% Hinglish, 30% English, 20% Devanagari, 10% Assamese' into explicit row ranges -
    percentages are ignored by smaller models, row numbers are not.  Returns [(lang, first_row, last_row)]."""
    pct = {}
    for key, rx in _LANG_KEYS:
        m = re.search(rx, lang_mix, re.I)
        if m:
            pct[key] = int(m.group(1))
    if not pct:
        pct = {"hinglish": 50, "english": 50}
    total = sum(pct.values())
    counts = {k: int(round(n * v / total)) for k, v in pct.items()}
    # every language in the mix gets at least one row; fix rounding so the counts add up to n
    for k in counts:
        counts[k] = max(1, counts[k])
    while sum(counts.values()) > n:
        k = max(counts, key=counts.get)
        counts[k] -= 1
    while sum(counts.values()) < n:
        k = max(counts, key=counts.get)
        counts[k] += 1
    plan, row = [], 1
    for k in ("hinglish", "english", "hindi", "assamese_mix"):
        if counts.get(k):
            plan.append((k, row, row + counts[k] - 1))
            row += counts[k]
    return plan


_VERDICT_RECIPE = {
    "LOW_ENERGY": ("energy BELOW the SIF threshold - a fall under 1.2 m, a light hand tool, a 12 V circuit, "
                   "a small spill, a trip hazard. high_energy_present=false, serious_injury=false. Write the "
                   "ordinary, undramatic observations a supervisor actually files most days."),
    "INSUFFICIENT": ("the text is genuinely too vague to judge - it names an activity or a place but never says "
                     "how much energy, how high, how heavy or whether anyone was exposed ('housekeeping poor near "
                     "pump area', 'kaam theek se nahi ho raha tha'). high_energy_present='unknown'. Do NOT add "
                     "detail that would resolve it."),
    "NON_EVENT": ("nothing hazardous is described, or it is a closed/hypothetical/training statement - a completed "
                  "corrective action, a toolbox-talk note, 'agar aisa hota to'. statement_type hypothetical, "
                  "historical or training_example."),
    "CAPACITY": ("high energy WAS released but a barrier limited the harm, so nobody is seriously hurt. "
                 "high_energy_present=true, energy_released=true, serious_injury=false, direct_control_present=true."),
    "SUCCESS": ("high energy present, barrier in place and used correctly, nothing released. "
                "high_energy_present=true, energy_released=false, direct_control_present=true."),
    "EXPOSURE": ("high energy present, no barrier, nothing released yet. "
                 "high_energy_present=true, energy_released=false, direct_control_present=false."),
    "P_SIF": ("high energy released, no barrier, but nobody seriously hurt this time. "
              "high_energy_present=true, energy_released=true, serious_injury=false, direct_control_present=false."),
}


def _verdict_block(plan: list[str] | None) -> str:
    """Assign a verdict to each row number. The four questions decide the verdict, so the recipe
    spells them out - a bare 'write more LOW_ENERGY rows' is ignored at scale."""
    if not plan:
        return ""
    rows_for: dict[str, list[int]] = {}
    for i, v in enumerate(plan, 1):
        rows_for.setdefault(v, []).append(i)
    out = ["\nVERDICT PLAN (mandatory, by row number). The four questions decide the verdict - "
           "answer them as described and the verdict follows:"]
    for v, idx in rows_for.items():
        nums = ", ".join(str(i) for i in idx)
        out.append(f"  rows {nums} -> {v}: {_VERDICT_RECIPE.get(v, '')}")
    out.append("Do not drift to a more dramatic scenario than the row asks for.")
    return "\n".join(out) + "\n"


def generate_messages(n: int, batch_index: int, seed_texts: list[str], lang_mix: str | None = None,
                      verdict_plan: list[str] | None = None) -> list[dict]:
    p = load_prompts()
    lang_mix = lang_mix or LANG_MIXES[batch_index % len(LANG_MIXES)]
    plan = language_plan(n, lang_mix)
    plan_txt = "; ".join(f"rows {a}-{b}: {_LANG_LABEL[k]} (meta.lang = '{k}')" if a != b else f"row {a}: {_LANG_LABEL[k]} (meta.lang = '{k}')"
                         for k, a, b in plan)
    system = p["spec"] + "\n\n" + p["generate_system"].replace("{N}", str(n)) + "\n" + OIL_CONTEXT + _fewshot() + _output_rule("array")
    k = len(LSR_FOCUS_ROTATION)
    focus = [LSR_FOCUS_ROTATION[(2 * batch_index) % k], LSR_FOCUS_ROTATION[(2 * batch_index + 1) % k]]
    user = (f"N = {n}\nLANG_MIX = {lang_mix}\n"
            f"ROW LANGUAGE PLAN (mandatory, by row number): {plan_txt}. Devanagari rows are written in Devanagari script "
            "(technical terms like LOTO, PPE, rig, SCBA may stay in Latin letters).\n"
            f"LSR FOCUS for this batch: at least {GENERATE_LSR_FOCUS_MIN} rows must involve '{focus[0]}' and at least "
            f"{GENERATE_LSR_FOCUS_MIN} rows '{focus[1]}' (realistic Oil India situations; set life_saving_rules accordingly). "
            "The remaining rows spread over the other Life-Saving Rules and 'no rule'.\n"
            "SEED EXAMPLES (imitate register, never copy):\n" + "\n".join(f"- {t}" for t in seed_texts) +
            _verdict_block(verdict_plan) +
            f"\nBATCH_ID = {batch_index}\nWrite and annotate now. Return a JSON array of exactly {n} elements.")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# --------------------------------------------------------------------------
# §2 REWIND
# --------------------------------------------------------------------------
def _compact_record(r: dict) -> dict:
    ctx = r.get("context") or {}
    meta = r.get("meta") or {}
    cf = ctx.get("causal_factors") or []
    return {
        "source_id": r["input_id"],
        "record_type": r.get("record_type"),
        "narrative": r["text"],
        "what_went_wrong": (ctx.get("what_went_wrong") or "")[:1200] or None,
        "corrective_actions": (ctx.get("corrective_actions") or "")[:600] or None,
        "causal_factors": [f"{c.get('category')}: {c.get('factor')}" for c in cf][:8] if isinstance(cf, list) else None,
        "cause": meta.get("cause"), "activity": meta.get("activity"), "function": meta.get("function"),
        "country": meta.get("country"), "onshore_offshore": meta.get("onshore_offshore"),
        "life_saving_rules": r.get("life_saving_rules") or [],
        "number_of_deaths": meta.get("number_of_deaths"),
        "actual_fatality": bool(meta.get("number_of_deaths")) or bool((r.get("labels") or {}).get("actual_fatality")),
        "actual_outcome": (r.get("labels") or {}).get("actual_outcome"),
        "potential_consequence": (ctx.get("potential_consequence") or "")[:300] or None,
    }


def rewind_messages(records: list[dict], variants_per_seed: int = 2) -> list[dict]:
    p = load_prompts()
    system = p["spec"] + "\n\n" + p["rewind_system"] + "\n" + OIL_CONTEXT + _fewshot() + _output_rule("array")
    recs = [_compact_record(r) for r in records]
    # language rotation so the corpus is not 75 % English: every 2nd seed writes Variant A in Devanagari Hindi,
    # every 3rd seed writes Variant B as an Assamese-English mix (Oil India's Assam fields) instead of Hinglish
    dev_ids = [r["source_id"] for i, r in enumerate(recs) if i % 2 == 0]
    asm_ids = [r["source_id"] for i, r in enumerate(recs) if i % 3 == 1]
    lang_rule = ""
    if dev_ids:
        lang_rule += (f"\nLANGUAGE RULE: for source_id in {json.dumps(dev_ids)} write Variant A in Devanagari Hindi script "
                      "(देवनागरी, 10-30 words, technical terms like LOTO/PPE/rig may stay in Latin letters; meta.lang = 'hindi'). "
                      "Its barrier state stays as specified above.")
    if asm_ids:
        lang_rule += (f"\nFor source_id in {json.dumps(asm_ids)} write Variant B as romanized Assamese-English mix "
                      "(e.g. 'harness laga nasil', 'permit nohol', 'bhitorot gol', 'kaam cholise'; meta.lang = 'assamese_mix') instead of Hinglish.")
    user = ("IOGP-STYLE POST-INVESTIGATION RECORDS (rewind EACH one separately; keep every span a verbatim substring of its own row's text):\n"
            + json.dumps(recs, ensure_ascii=False) +
            f"\n\nFor every record produce {variants_per_seed} counterfactual variants PLUS the original narrative "
            "as a final annotated row.\n"
            "EACH VARIANT HAS FIXED ANSWERS TO THE FOUR QUESTIONS. Copy them exactly - the verdict is derived "
            "from them, so any other combination is rejected:\n"
            "  meta.trap 'rewind_A'  (terse Indian English)  ->  verdict CAPACITY\n"
            "     high_energy_present=true, energy_released=true, serious_injury=false, direct_control_present=true\n"
            "     MEANING: the same energy IS released as in the real record, but a barrier WAS in place and it "
            "limited the harm, so nobody is seriously hurt - the lanyard arrested the fall, the SCBA held during the "
            "gas release, the blast wall took the fragment, the guard stopped the hand. Name that barrier and say it "
            "held; tag it control_present. This is a near-miss BECAUSE the barrier worked, not a fatality.\n"
            "  meta.trap 'rewind_B'  (romanized Hinglish)  ->  verdict SUCCESS\n"
            "     high_energy_present=true, energy_released=false, serious_injury=false, direct_control_present=true\n"
            "     MEANING: same energy and task, the barrier is in place and being used correctly, and nothing has "
            "been released at all. Tag the barrier control_present.\n"
            "Both variants describe the SAME energy, equipment, task and location as the record - only the barrier "
            "and the outcome differ. They are a matched pair; that contrast is the point of the row.\n"
            "NEVER write a variant with the barrier missing (that is EXPOSURE or P_SIF) - the corpus already has "
            "thousands of those and they will be rejected as surplus.\n"
            "Variants describe people in the middle of the act (statement_type 'observed'); use 'condition_only' only "
            "when nobody is acting or exposed. The ORIGINAL row is the incident report itself: statement_type "
            "'observed' (never 'historical'), and answer its four questions truthfully from the record - if someone "
            "died or was seriously hurt that gives H_SIF. Keep the original row's text under 250 words: if the record "
            "is longer, quote only the sentences describing the event and its outcome, and take every span from that "
            "shortened text. "
            + lang_rule + " "
            f"Return a JSON array with one object per record: {{\"source_id\": ..., \"rows\": "
            f"[<{variants_per_seed + 1} annotated §1 elements: the {variants_per_seed} variants, then the original>]}}.")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# --------------------------------------------------------------------------
# §3 LABEL
# --------------------------------------------------------------------------
def label_messages(rows: list[dict]) -> list[dict]:
    p = load_prompts()
    system = p["spec"] + "\n\n" + p["label_system"] + _fewshot() + _output_rule("array")
    payload = [{"input_id": r["input_id"], "text": r["text"]} for r in rows]
    user = "ROWS:\n" + json.dumps(payload, ensure_ascii=False) + "\nAnnotate. Return a JSON array in the same order, each element including \"input_id\"."
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# --------------------------------------------------------------------------
# seed texts for §1 (never gold rows - those are the test set)
# --------------------------------------------------------------------------
def seed_pool() -> list[str]:
    texts: list[str] = []
    if EXEMPLARS.exists():
        for ln in EXEMPLARS.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    texts.append(json.loads(ln)["text"])
                except Exception:  # noqa: BLE001
                    continue
    from ..config import REGISTER_DIR  # noqa: WPS433
    for f in sorted(REGISTER_DIR.glob("*_clean.jsonl")) if REGISTER_DIR.exists() else []:
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                t = json.loads(ln)["text"]
                if 6 <= len(t.split()) <= 40:
                    texts.append(t)
            except Exception:  # noqa: BLE001
                continue
    return texts
