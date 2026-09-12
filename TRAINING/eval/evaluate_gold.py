"""
Evaluate the sentence heads on the held-out sets:

  gold-180  (DATA/Processed/gold/gold.jsonl)  - SIF potential YES/NO/UNCERTAIN, per trap family, LSR
  IHM       (DATA/Processed/ihm/ihm_eval.jsonl) - agreement with Potential Accident Level (IV-VI -> SIF)

    python -m TRAINING.eval.evaluate_gold                       # uses SERVER/Classfication/Models/Tunned/sif_heads
    python -m TRAINING.eval.evaluate_gold --heads path/to/dir
    -> TRAINING/eval/reports/gold_eval.json + gold_eval.md

Verdict -> gold mapping: YES = P_SIF, EXPOSURE, H_SIF, L_SIF, CAPACITY ; NO = LOW_ENERGY, NON_EVENT, SUCCESS ;
UNCERTAIN = INSUFFICIENT.  A prediction also counts as "candidate-correct" when it is in the row's
verdict_candidates (looser, since gold carries 3 classes, not 9).
Metrics led by SIF recall and F2 (missing a real precursor costs more than an extra review).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.eval"  # noqa: A001

from ..config import GOLD_JSONL, IHM_JSONL, OUTPUT_MODELS_DIR, TRAINING_DIR  # noqa: E402
from ..finetune.heads import SifHeads  # noqa: E402

REPORT_DIR = TRAINING_DIR / "eval" / "reports"
YES = {"P_SIF", "EXPOSURE", "H_SIF", "L_SIF", "CAPACITY"}
NO = {"LOW_ENERGY", "NON_EVENT", "SUCCESS"}


def verdict_to_gold(v: str | None, prefilter: int | None) -> str:
    if v in YES:
        return "YES"
    if v in NO:
        return "NO"
    if v == "INSUFFICIENT":
        return "UNCERTAIN"
    return "YES" if prefilter == 1 else "NO"


def _prf(tp, fp, fn, beta=1.0):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    b2 = beta * beta
    f = (1 + b2) * p * r / (b2 * p + r) if (b2 * p + r) else 0.0
    return round(p, 3), round(r, 3), round(f, 3)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heads", default=str(OUTPUT_MODELS_DIR / "sif_heads"))
    a = ap.parse_args(argv)
    heads = SifHeads.load(Path(a.heads))
    gold = [json.loads(ln) for ln in open(GOLD_JSONL, "r", encoding="utf-8") if ln.strip()]
    preds = heads.predict([g["text"] for g in gold])

    rows = []
    for g, p in zip(gold, preds):
        pg = verdict_to_gold(p.get("verdict"), p.get("prefilter"))
        rows.append({"gold_id": g["gold_id"], "text": g["text"], "gold": g["sif_potential"], "pred": pg,
                     "pred_verdict": p.get("verdict"), "pred_prefilter": p.get("prefilter"),
                     "candidate_ok": p.get("verdict") in set(g.get("verdict_candidates") or []),
                     "trap_family": g["trap_family"], "lang": g["language"],
                     "gold_lsr": g["life_saving_rules"], "pred_lsr": p.get("lsr", []),
                     "gold_statement": g["statement_type"], "pred_statement": p.get("statement_type")})
    n = len(rows)
    acc = sum(r["gold"] == r["pred"] for r in rows) / n
    # SIF recall / F2 on YES vs not-YES (UNCERTAIN predicted for a YES row counts as a miss for recall - conservative)
    tp = sum(1 for r in rows if r["gold"] == "YES" and r["pred"] == "YES")
    fp = sum(1 for r in rows if r["gold"] != "YES" and r["pred"] == "YES")
    fn = sum(1 for r in rows if r["gold"] == "YES" and r["pred"] != "YES")
    p1, r1, f1 = _prf(tp, fp, fn)
    _, _, f2 = _prf(tp, fp, fn, beta=2.0)
    # prefilter view: anything not LOW_ENERGY/NON_EVENT should be flagged
    pf_tp = sum(1 for r in rows if r["gold"] in ("YES", "UNCERTAIN") and r["pred_prefilter"] == 1)
    pf_fn = sum(1 for r in rows if r["gold"] in ("YES", "UNCERTAIN") and r["pred_prefilter"] == 0)
    pf_fp = sum(1 for r in rows if r["gold"] == "NO" and r["pred_prefilter"] == 1)
    per_trap = {}
    for fam, grp in _group(rows, "trap_family").items():
        per_trap[fam] = {"n": len(grp), "accuracy": round(sum(r["gold"] == r["pred"] for r in grp) / len(grp), 3),
                         "sif_recall": _prf(sum(1 for r in grp if r["gold"] == "YES" and r["pred"] == "YES"), 0,
                                            sum(1 for r in grp if r["gold"] == "YES" and r["pred"] != "YES"))[1]}
    per_lang = {l: round(sum(r["gold"] == r["pred"] for r in grp) / len(grp), 3) for l, grp in _group(rows, "lang").items()}
    # LSR micro-F1 (only rows with a gold rule)
    ltp = lfp = lfn = 0
    for r in rows:
        g, p = set(r["gold_lsr"]), set(r["pred_lsr"])
        ltp += len(g & p)
        lfp += len(p - g)
        lfn += len(g - p)
    lsr_p, lsr_r, lsr_f = _prf(ltp, lfp, lfn)
    st_acc = round(sum(r["gold_statement"] == r["pred_statement"] for r in rows) / n, 3)
    confusion = Counter((r["gold"], r["pred"]) for r in rows)

    ihm = None
    if IHM_JSONL.exists():
        ih = [json.loads(ln) for ln in open(IHM_JSONL, "r", encoding="utf-8") if ln.strip()]
        ip = heads.predict([x["text"] for x in ih])
        agree = Counter()
        for x, p in zip(ih, ip):
            pg = verdict_to_gold(p.get("verdict"), p.get("prefilter"))
            exp = x["expected_verdict_group"]
            key = "SIF_POTENTIAL->YES" if exp == "SIF_POTENTIAL" else "LOW_ENERGY->NO" if exp == "LOW_ENERGY" else "BORDERLINE"
            if exp == "SIF_POTENTIAL":
                agree[key] += pg == "YES"
            elif exp == "LOW_ENERGY":
                agree[key] += pg == "NO"
            agree[f"{key}:n"] += 1
        ihm = {"sif_potential_flagged_yes": round(agree["SIF_POTENTIAL->YES"] / max(1, agree["SIF_POTENTIAL->YES:n"]), 3),
               "low_energy_flagged_no": round(agree["LOW_ENERGY->NO"] / max(1, agree["LOW_ENERGY->NO:n"]), 3),
               "n": len(ih)}

    rep = {"heads": a.heads, "n": n, "accuracy_3class": round(acc, 3),
           "sif_yes": {"precision": p1, "recall": r1, "f1": f1, "f2": f2, "tp": tp, "fp": fp, "fn": fn},
           "prefilter": {"recall": _prf(pf_tp, pf_fp, pf_fn)[1], "precision": _prf(pf_tp, pf_fp, pf_fn)[0], "f2": _prf(pf_tp, pf_fp, pf_fn, 2.0)[2]},
           "candidate_match_rate": round(sum(r["candidate_ok"] for r in rows) / n, 3),
           "confusion_gold_vs_pred": {f"{g}->{p}": c for (g, p), c in sorted(confusion.items())},
           "per_trap_family": per_trap, "per_language": per_lang,
           "lsr": {"precision": lsr_p, "recall": lsr_r, "f1": lsr_f}, "statement_type_accuracy": st_acc, "ihm": ihm}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "gold_eval.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    (REPORT_DIR / "gold_eval_rows.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    (REPORT_DIR / "gold_eval.md").write_text(_md(rep), encoding="utf-8")
    print(_md(rep))
    return 0


def _group(rows, key):
    g = defaultdict(list)
    for r in rows:
        g[r[key]].append(r)
    return g


def _md(rep: dict) -> str:
    L = [f"# Gold-180 evaluation ({rep['heads']})", "",
         f"- 3-class accuracy (YES/NO/UNCERTAIN): **{rep['accuracy_3class']}**  ·  candidate-match rate: {rep['candidate_match_rate']}",
         f"- SIF=YES: recall **{rep['sif_yes']['recall']}**, precision {rep['sif_yes']['precision']}, F2 **{rep['sif_yes']['f2']}** (tp {rep['sif_yes']['tp']}, fp {rep['sif_yes']['fp']}, fn {rep['sif_yes']['fn']})",
         f"- prefilter (flag anything not LOW_ENERGY/NON_EVENT): recall {rep['prefilter']['recall']}, precision {rep['prefilter']['precision']}, F2 {rep['prefilter']['f2']}",
         f"- Life-Saving Rules micro: P {rep['lsr']['precision']} R {rep['lsr']['recall']} F1 {rep['lsr']['f1']}  ·  statement-type accuracy {rep['statement_type_accuracy']}",
         f"- confusion: {rep['confusion_gold_vs_pred']}", "", "## Per trap family", "", "| family | n | accuracy | SIF recall |", "|---|---|---|---|"]
    for fam, m in sorted(rep["per_trap_family"].items(), key=lambda kv: -kv[1]["n"]):
        L.append(f"| {fam} | {m['n']} | {m['accuracy']} | {m['sif_recall']} |")
    L += ["", f"## Per language: {rep['per_language']}", ""]
    if rep.get("ihm"):
        L += [f"## Kaggle IHM agreement (n={rep['ihm']['n']}): potential IV-VI flagged YES {rep['ihm']['sif_potential_flagged_yes']}, potential I-II flagged NO {rep['ihm']['low_energy_flagged_no']}", ""]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
