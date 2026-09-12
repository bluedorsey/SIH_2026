"""Run the FULL pipeline over gold-180 and write results + a self-contained HTML report.

    python -m INFERENCE.evaluate                      # full pipeline (rules + GLiNER + heads)
    python -m INFERENCE.evaluate --no-models          # rules only, to isolate each layer's value
    python -m INFERENCE.evaluate --out-dir REPORTS

Unlike TRAINING/eval/evaluate_gold.py (which scores the SetFit heads alone) this measures what
production actually returns, so the numbers are the ones a reviewer would experience.
"""
from __future__ import annotations

import argparse
import collections
import json
import logging
import time
from pathlib import Path

from .config import REPO_ROOT
from .pipeline import analyse

GOLD = REPO_ROOT / "DATA" / "Processed" / "gold" / "gold.jsonl"
SIF_VERDICTS = {"H_SIF", "L_SIF", "P_SIF", "EXPOSURE", "CAPACITY"}
UNCERTAIN_VERDICTS = {"INSUFFICIENT"}
# OUT_OF_SCOPE maps to NO on purpose: the scope gate asserts this is not a safety observation
# at all, which is a stronger "no" than LOW_ENERGY. It is counted separately in the summary so
# a gate quietly eating rows shows up as a number rather than as a mystery accuracy drop.


def to_three_class(verdict: str) -> str:
    if verdict in SIF_VERDICTS:
        return "YES"
    if verdict in UNCERTAIN_VERDICTS:
        return "UNCERTAIN"
    return "NO"                      # LOW_ENERGY, NON_EVENT, SUCCESS, OUT_OF_SCOPE


def run(use_models: bool = True) -> list[dict]:
    rows = [json.loads(l) for l in open(GOLD, "r", encoding="utf-8") if l.strip()]
    out = []
    t0 = time.time()
    for i, r in enumerate(rows, 1):
        res = analyse(r["text"], report_id=r["id"], use_models=use_models)
        pred = res["verdict"]["label"]
        out.append({
            "id": r["id"], "text": r["text"],
            "truth": r["sif_potential"], "pred3": to_three_class(pred), "pred_verdict": pred,
            "confidence": res["verdict"]["confidence"], "route": res["verdict"]["route"],
            "review": res["review"]["required"],
            "trap_family": r.get("trap_family") or "none", "language": r.get("language") or "?",
            "truth_statement": r.get("statement_type"), "pred_statement": res["meta"]["statement_type"],
            "truth_lsr": r.get("life_saving_rules") or [], "pred_lsr": res["safety_knowledge"]["lsr"],
            "hazard": res["safety_knowledge"]["hazard"],
            "energy_gate": res["energy"].get("gate"), "energy_j": res["energy"].get("estimate_j"),
            "n_spans": len(res["spans"]),
            "layers": res["verdict"]["layers_agreed"],
            "decision_path": res["verdict"]["decision_path"],
            "negation": res["traps_checked"]["negation_scope"],
        })
        if i % 30 == 0:
            logging.info("%d/%d (%.1f rows/s)", i, len(rows), i / (time.time() - t0))
    return out


def metrics(res: list[dict]) -> dict:
    n = len(res)
    acc = sum(1 for r in res if r["pred3"] == r["truth"]) / max(1, n)
    gated = sum(1 for r in res if r.get("pred_verdict") == "OUT_OF_SCOPE")
    gated_yes = sum(1 for r in res if r.get("pred_verdict") == "OUT_OF_SCOPE" and r["truth"] == "YES")
    tp = sum(1 for r in res if r["truth"] == "YES" and r["pred3"] == "YES")
    fp = sum(1 for r in res if r["truth"] != "YES" and r["pred3"] == "YES")
    fn = sum(1 for r in res if r["truth"] == "YES" and r["pred3"] != "YES")
    rec = tp / max(1, tp + fn)
    prec = tp / max(1, tp + fp)
    f2 = (5 * prec * rec / max(1e-9, 4 * prec + rec)) if (prec + rec) else 0.0
    conf = collections.Counter(f'{r["truth"]}->{r["pred3"]}' for r in res)
    fam: dict[str, dict] = {}
    for r in res:
        f = fam.setdefault(r["trap_family"], {"n": 0, "ok": 0, "yes": 0, "yes_ok": 0})
        f["n"] += 1
        f["ok"] += r["pred3"] == r["truth"]
        if r["truth"] == "YES":
            f["yes"] += 1
            f["yes_ok"] += r["pred3"] == "YES"
    lang: dict[str, dict] = {}
    for r in res:
        l = lang.setdefault(r["language"], {"n": 0, "ok": 0})
        l["n"] += 1
        l["ok"] += r["pred3"] == r["truth"]
    return {
        "n": n, "accuracy": round(acc, 3),
        "sif": {"recall": round(rec, 3), "precision": round(prec, 3), "f2": round(f2, 3),
                "tp": tp, "fp": fp, "fn": fn},
        "statement_accuracy": round(sum(1 for r in res if r["pred_statement"] == r["truth_statement"]) / max(1, n), 3),
        "confusion": dict(conf),
        "verdicts": dict(collections.Counter(r["pred_verdict"] for r in res)),
        "families": {k: {"n": v["n"], "accuracy": round(v["ok"] / v["n"], 3),
                         "sif_recall": round(v["yes_ok"] / v["yes"], 3) if v["yes"] else None}
                     for k, v in sorted(fam.items(), key=lambda kv: -kv[1]["n"])},
        "languages": {k: {"n": v["n"], "accuracy": round(v["ok"] / v["n"], 3)} for k, v in lang.items()},
        "review_rate": round(sum(1 for r in res if r["review"]) / max(1, n), 3),
        "scope_gated": gated, "scope_gated_precursors": gated_yes,
        "fast_lane_rate": round(sum(1 for r in res if r["route"] == "fast_lane") / max(1, n), 3),
        "mean_spans": round(sum(r["n_spans"] for r in res) / max(1, n), 1),
    }


# ------------------------------------------------------------------ report
def _bar(pct: float, colour: str, w: int = 220) -> str:
    return (f'<div class="bar"><span style="width:{max(0.0, min(1.0, pct)) * w:.0f}px;'
            f'background:{colour}"></span></div>')


def html_report(m: dict, res: list[dict], mode: str) -> str:
    def _fam_cell(v: dict) -> str:
        r = v["sif_recall"]
        if r is None:
            return "&mdash;"
        return _bar(r, "#c0504d") + "<b>{:.2f}</b>".format(r)

    fam_rows = "".join(
        '<tr><td>{}</td><td class="n">{}</td><td>{}<b>{:.2f}</b></td><td>{}</td></tr>'.format(
            k, v["n"], _bar(v["accuracy"], "#4a7dbd"), v["accuracy"], _fam_cell(v))
        for k, v in m["families"].items())
    lang_rows = "".join(
        f'<tr><td>{k}</td><td class="n">{v["n"]}</td>'
        f'<td>{_bar(v["accuracy"], "#4a7dbd")}<b>{v["accuracy"]:.2f}</b></td></tr>'
        for k, v in sorted(m["languages"].items(), key=lambda kv: -kv[1]["n"]))
    vmax = max(m["verdicts"].values()) if m["verdicts"] else 1
    v_rows = "".join(
        f'<tr><td>{k}</td><td class="n">{v}</td><td>{_bar(v / vmax, "#7a9a5b")}</td></tr>'
        for k, v in sorted(m["verdicts"].items(), key=lambda kv: -kv[1]))
    cells = []
    for t in ("YES", "UNCERTAIN", "NO"):
        for p in ("YES", "UNCERTAIN", "NO"):
            c = m["confusion"].get(f"{t}->{p}", 0)
            hit = "hit" if t == p else ("miss" if t == "YES" and p != "YES" else "")
            cells.append(f'<td class="cm {hit}">{c}</td>')
    cm = ("<tr><th></th><th>→YES</th><th>→UNC</th><th>→NO</th></tr>"
          f'<tr><th>YES</th>{"".join(cells[0:3])}</tr>'
          f'<tr><th>UNC</th>{"".join(cells[3:6])}</tr>'
          f'<tr><th>NO</th>{"".join(cells[6:9])}</tr>')
    misses = [r for r in res if r["truth"] == "YES" and r["pred3"] != "YES"][:25]
    miss_rows = "".join(
        f'<tr><td class="mono">{r["id"]}</td><td>{r["text"][:110]}</td>'
        f'<td>{r["pred_verdict"]}</td><td class="mono small">{r["decision_path"][:90]}</td></tr>'
        for r in misses)
    s = m["sif"]
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>SIF engine — gold-180 report</title><style>
body{{font:14px/1.5 system-ui,sans-serif;margin:0;padding:32px;background:#f6f7f9;color:#1a1a1a}}
h1{{margin:0 0 4px;font-size:22px}} h2{{font-size:15px;margin:28px 0 10px;color:#444;
text-transform:uppercase;letter-spacing:.05em}}
.sub{{color:#666;margin-bottom:24px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap}}
.card{{background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:16px 20px;min-width:150px}}
.card .v{{font-size:28px;font-weight:600}} .card .l{{color:#666;font-size:12px}}
.good{{color:#2e7d32}} .warn{{color:#b8860b}} .bad{{color:#c0504d}}
table{{border-collapse:collapse;background:#fff;border:1px solid #e3e6ea;border-radius:8px;width:100%}}
td,th{{padding:7px 12px;border-bottom:1px solid #eef0f2;text-align:left;vertical-align:middle}}
th{{background:#fafbfc;font-size:12px;color:#555}} td.n{{color:#666;width:50px}}
.bar{{display:inline-block;width:220px;height:9px;background:#eef0f2;border-radius:5px;
margin-right:8px;vertical-align:middle}}
.bar span{{display:block;height:9px;border-radius:5px}}
.cm{{text-align:center;font-weight:600;background:#fff}} .cm.hit{{background:#e8f2e8;color:#2e7d32}}
.cm.miss{{background:#fbeaea;color:#c0504d}}
.mono{{font-family:ui-monospace,monospace;font-size:12px}} .small{{color:#777}}
.note{{background:#fff8e6;border:1px solid #f0e0b0;border-radius:8px;padding:12px 16px;margin:18px 0}}
</style></head><body>
<h1>SIF precursor engine — gold-180</h1>
<div class="sub">{m['n']} human-written observations · mode: <b>{mode}</b> · never seen by any teacher model</div>
<div class="cards">
  <div class="card"><div class="v {'good' if m['accuracy']>=.6 else 'warn' if m['accuracy']>=.45 else 'bad'}">{m['accuracy']:.3f}</div><div class="l">3-class accuracy</div></div>
  <div class="card"><div class="v {'good' if s['recall']>=.6 else 'warn' if s['recall']>=.45 else 'bad'}">{s['recall']:.3f}</div><div class="l">SIF recall — the number that matters</div></div>
  <div class="card"><div class="v">{s['precision']:.3f}</div><div class="l">SIF precision</div></div>
  <div class="card"><div class="v">{s['f2']:.3f}</div><div class="l">F2 (recall-weighted)</div></div>
  <div class="card"><div class="v bad">{s['fn']}</div><div class="l">missed precursors</div></div>
  <div class="card"><div class="v">{m['review_rate']:.0%}</div><div class="l">sent to human review</div></div>
  <div class="card"><div class="v">{m['mean_spans']}</div><div class="l">mean spans / report</div></div>
</div>
<div class="note"><b>Read recall, not accuracy.</b> Missing a precursor costs a life; a false alarm
costs a supervisor five minutes. {s['fn']} of {s['tp']+s['fn']} real precursors were missed.</div>
<h2>Confusion (truth → predicted)</h2><table>{cm}</table>
<h2>Per trap family</h2><table><tr><th>family</th><th>n</th><th>accuracy</th><th>SIF recall</th></tr>{fam_rows}</table>
<h2>Per language</h2><table><tr><th>language</th><th>n</th><th>accuracy</th></tr>{lang_rows}</table>
<h2>Verdict distribution</h2><table><tr><th>verdict</th><th>n</th><th></th></tr>{v_rows}</table>
<h2>Missed precursors (first {len(misses)})</h2>
<table><tr><th>id</th><th>text</th><th>predicted</th><th>why</th></tr>{miss_rows}</table>
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-models", action="store_true", help="rules only")
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "REPORTS"))
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    mode = "rules only" if a.no_models else "rules + GLiNER + heads"
    res = run(use_models=not a.no_models)
    m = metrics(res)

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tag = "rules" if a.no_models else "full"
    (out / f"gold180_{tag}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res), encoding="utf-8")
    (out / f"gold180_{tag}.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
    (out / f"gold180_{tag}.html").write_text(html_report(m, res, mode), encoding="utf-8")

    print(json.dumps({k: m[k] for k in ("n", "accuracy", "sif", "review_rate", "mean_spans")}, indent=2))
    print(f"\nreport -> {out / f'gold180_{tag}.html'}   (open it in a browser)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
