"""
Merge + filter + split the teacher output into the training sets.

    python -m TRAINING.distill.filter_distilled              # -> DATA/distilled/{train,dev,test}.jsonl + distill_report.md

Steps
1. load raw/{generate,rewind,label}.jsonl (all already validated by schema.py) and exemplars.jsonl
2. re-validate (cheap insurance), drop rows > MAX_TEXT_TOKENS
3. exact + near-duplicate removal inside the corpus (MinHash from CLEANING.common.dedup, Jaccard 0.70)
4. LEAKAGE GUARD: every row that near-duplicates a gold-180 or IHM row is dropped
5. quotas: verdict / trap / language shares are reported against the plan; over-represented verdicts are
   down-sampled only if --enforce-quotas is passed (default: report, don't drop)
6. seed-grouped split: all rows sharing a seed_id (rewind variants + original) stay on the same side;
   80/10/10 stratified by verdict x language; test rows are candidates for the human-checked silver test
7. writes train.jsonl / dev.jsonl / test.jsonl, plus gliner_labels.json (label names) and distill_report.md
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.distill"  # noqa: A001

from ..config import (  # noqa: E402
    DISTILLED_DIR, DISTILLED_RAW_DIR, EXEMPLARS, GOLD_JSONL, IHM_JSONL, LANG_MIXES, NEAR_DUP_JACCARD, ROLE_TO_GLINER_LABEL,
    TARGET_TRAIN_ROWS, VERDICT_QUOTA,
)
from .schema import validate_element  # noqa: E402

try:
    from CLEANING.common.dedup import mark_duplicates  # noqa: E402
except Exception:  # noqa: BLE001
    mark_duplicates = None  # type: ignore

log = logging.getLogger("distill.filter")
_DEV = re.compile(r"[ऀ-ॿ]")
_ASM = re.compile(r"[ঀ-৿]|\b(kora|nohol|nasil|ase|asil|cholise|hoy|hobo|geche|gol|bhitore|bhitorot|dhuke|dhukise|nohoi|korile|kaam kora)\b", re.I)
_HING = re.compile(r"\b(nahi|nahin|tha|thi|hai|hain|kiya|raha|rahi|rahe|gaya|gayi|mein|aur|bina|koi|kaam|hua|hui|liye|lekin|phir|abhi|upar|neeche|andar|bahar|pehle|baad|sirf|bhi|gira|toota|chal|band|khula|dekha|mila|karke|wajah|dauran|jagah|paas)\b", re.I)


def lang_of(text: str) -> str:
    if _DEV.search(text):
        return "devanagari"
    if _ASM.search(text):
        return "assamese_mix"
    return "hinglish" if len(_HING.findall(text)) >= 2 else "english"


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def _write(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_all() -> list[dict]:
    rows: list[dict] = []
    for job in ("generate", "rewind", "label"):
        rows += _read(DISTILLED_RAW_DIR / f"{job}.jsonl")
    if EXEMPLARS.exists():
        for el in _read(EXEMPLARS):
            row, probs = validate_element(el, source="exemplar", teacher="claude", model="claude", batch_id="exemplars")
            if row:
                row["seed_id"] = f"exemplar:{len(rows)}"
                rows.append(row)
            else:
                log.warning("exemplar rejected: %s | %s", probs, str(el.get("text"))[:60])
    for i, r in enumerate(rows):
        r["id"] = f"d{i:06d}"
        r["lang"] = lang_of(r["text"])
        r["trap"] = (r.get("meta") or {}).get("trap") or ("rewind" if r["source"].startswith("rewind") else "none")
    return rows


def dedupe_and_guard(rows: list[dict]) -> tuple[list[dict], dict]:
    gold = _read(GOLD_JSONL)
    ihm = _read(IHM_JSONL)
    guard = [{"id": f"gold:{g['id']}", "text": g["text"]} for g in gold] + [{"id": f"ihm:{g['id']}", "text": g["text"]} for g in ihm]
    if mark_duplicates is None:
        log.warning("CLEANING not importable - exact-dedupe only")
        seen, out = set(), []
        gold_texts = {g["text"].strip().lower() for g in guard}
        for r in rows:
            k = r["text"].strip().lower()
            if k in seen or k in gold_texts:
                continue
            seen.add(k)
            out.append(r)
        return out, {"exact_dups": len(rows) - len(out), "near_dups": 0, "leaks": "n/a"}
    pool = [{"id": r["id"], "text": r["text"], "_guard": False} for r in rows] + [{**g, "_guard": True} for g in guard]
    mark_duplicates(pool, text_field="text", id_field="id", threshold=NEAR_DUP_JACCARD,
                    priority=lambda x: 9 if x["_guard"] else 0)
    guard_ids = {g["id"] for g in guard}
    dropped_dup = dropped_leak = 0
    keep = []
    flags = {p["id"]: p for p in pool}
    for r in rows:
        p = flags[r["id"]]
        if p["is_duplicate"]:
            if p["duplicate_of"] in guard_ids:
                dropped_leak += 1
            else:
                dropped_dup += 1
            continue
        keep.append(r)
    return keep, {"exact_or_near_dups": dropped_dup, "leaks_vs_gold_ihm": dropped_leak, "threshold": NEAR_DUP_JACCARD}


def split(rows: list[dict], seed: int = 42, dev: float = 0.10, test: float = 0.10) -> tuple[list, list, list]:
    """Group by seed_id; stratify groups by (verdict, lang) of their first row."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r.get("seed_id") or r["id"]].append(r)
    strata: dict[tuple, list[str]] = defaultdict(list)
    for gid, g in groups.items():
        strata[(g[0]["verdict"], g[0]["lang"])].append(gid)
    rng = random.Random(seed)
    tr, dv, te = [], [], []
    for key, gids in strata.items():
        rng.shuffle(gids)
        n = len(gids)
        n_te, n_dv = round(n * test), round(n * dev)
        for i, gid in enumerate(gids):
            dest = te if i < n_te else dv if i < n_te + n_dv else tr
            dest.extend(groups[gid])
    for name, part in (("train", tr), ("dev", dv), ("test", te)):
        for r in part:
            r["split"] = name
    return tr, dv, te


def quota_report(rows: list[dict]) -> dict:
    n = len(rows)
    verdicts = Counter(r["verdict"] for r in rows)
    langs = Counter(r["lang"] for r in rows)
    traps = Counter(r["trap"] for r in rows)
    sources = Counter(r["source"].split(":")[0] for r in rows)
    lsr = Counter(l for r in rows for l in r["life_saving_rules"])
    roles = Counter(s["role"] for r in rows for s in r["spans"])
    target = {k: int(v * TARGET_TRAIN_ROWS) for k, v in VERDICT_QUOTA.items()}
    return {
        "rows": n, "verdicts": dict(verdicts), "verdict_target": target,
        "verdict_shortfall": {k: max(0, t - verdicts.get(k, 0)) for k, t in target.items()},
        "languages": dict(langs), "language_share": {k: round(v / max(1, n), 3) for k, v in langs.items()},
        "traps": dict(traps.most_common()), "sources": dict(sources), "lsr": dict(lsr.most_common()),
        "roles": dict(roles.most_common()), "rows_with_spans": sum(1 for r in rows if r["spans"]),
        "avg_spans_per_row": round(sum(len(r["spans"]) for r in rows) / max(1, n), 2),
        "post_injury_share": round(sum(1 for r in rows if r["verdict"] in ("H_SIF", "L_SIF")) / max(1, n), 3),
    }


def enforce_quotas(rows: list[dict], seed: int = 7, tolerance: float = 1.25) -> list[dict]:
    """Down-sample verdicts that exceed their plan share by more than `tolerance`.

    The cap is solved against the size of the KEPT set, not the input: capping against the input
    lets a flooded class inflate its own cap (10 775 EXPOSURE rows in an 18 691-row corpus gave a
    cap of 7 009, so almost nothing was trimmed and EXPOSURE stayed at half the training set).
    Shrinking N is monotone, so a short fixed-point loop converges.
    """
    rng = random.Random(seed)
    by_v: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_v[r["verdict"]].append(r)

    def caps_for(total: int) -> dict[str, int]:
        return {v: int(VERDICT_QUOTA.get(v, 0.05) * tolerance * total) for v in by_v}

    n = len(rows)
    for _ in range(60):
        caps = caps_for(n)
        kept = sum(min(len(part), caps[v]) for v, part in by_v.items())
        if kept >= n:
            break
        n = kept
    caps = caps_for(n)

    out = []
    for v, part in by_v.items():
        cap = caps[v]
        if len(part) > cap:
            rng.shuffle(part)
            log.info("quota: %s %d -> %d", v, len(part), cap)
            part = part[:cap]
        out += part
    log.info("quotas: %d rows -> %d rows", len(rows), len(out))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--enforce-quotas", action="store_true")
    ap.add_argument("--quota-tolerance", type=float, default=1.25,
                    help="how far a verdict may exceed its plan share before it is trimmed "
                         "(1.25 = at most 125%% of target; lower is better balanced but smaller)")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")

    rows = load_all()
    log.info("loaded %d validated rows", len(rows))
    if not rows:
        raise SystemExit("nothing in DATA/distilled/raw - run TRAINING.distill.run_distill first")
    rows, dedup = dedupe_and_guard(rows)
    log.info("after dedupe/leak guard: %d rows (%s)", len(rows), dedup)
    if a.enforce_quotas:
        rows = enforce_quotas(rows, a.seed, a.quota_tolerance)
    tr, dv, te = split(rows, a.seed)
    _write(tr, DISTILLED_DIR / "train.jsonl")
    _write(dv, DISTILLED_DIR / "dev.jsonl")
    _write(te, DISTILLED_DIR / "test.jsonl")
    (DISTILLED_DIR / "gliner_labels.json").write_text(json.dumps(ROLE_TO_GLINER_LABEL, indent=2), encoding="utf-8")
    rep = {"dedup": dedup, "train": quota_report(tr), "dev": quota_report(dv), "test": quota_report(te), "lang_mixes_used": LANG_MIXES}
    (DISTILLED_DIR / "distill_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    (DISTILLED_DIR / "distill_report.md").write_text(_md(rep), encoding="utf-8")
    log.info("train %d / dev %d / test %d -> %s", len(tr), len(dv), len(te), DISTILLED_DIR)
    return 0


def _md(rep: dict) -> str:
    t = rep["train"]
    L = ["# Distilled data report", "", f"- dedupe / leak guard: {rep['dedup']}",
         f"- train {t['rows']} rows, dev {rep['dev']['rows']}, test {rep['test']['rows']} (seed-grouped, stratified by verdict x language)", "",
         "## Train set vs plan", "", "| verdict | rows | target | shortfall |", "|---|---|---|---|"]
    for k, tgt in t["verdict_target"].items():
        L.append(f"| {k} | {t['verdicts'].get(k, 0)} | {tgt} | {t['verdict_shortfall'][k]} |")
    L += ["", f"- language share: {t['language_share']} (plan: hinglish .45 / english .35 / devanagari .10 / assamese .05)",
          f"- post-injury share (H_SIF+L_SIF): {t['post_injury_share']} (cap 0.06)",
          f"- rows with spans: {t['rows_with_spans']} / {t['rows']}, avg spans per row {t['avg_spans_per_row']}",
          f"- roles: {t['roles']}", f"- Life-Saving Rules: {t['lsr']}", f"- traps: {t['traps']}", f"- sources: {t['sources']}", "",
          "## Next", "", "1. If a verdict shortfall is large, run more §1 batches (`--job generate --total-rows N`) - the prompt's VERDICT QUOTA will fill it.",
          "2. Hand `test.jsonl` (or a 400-row sample of it) to two annotators -> silver test with kappa.",
          "3. `python -m TRAINING.finetune.prepare_gliner_data` and `python -m TRAINING.finetune.prepare_setfit_data`."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
