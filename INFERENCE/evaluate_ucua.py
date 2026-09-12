"""
Evaluate UC/UA against the 56 REAL human-labelled register rows - the only genuine
field-labelled data in the repo.

    python -m INFERENCE.evaluate_ucua
    python -m INFERENCE.evaluate_ucua --out-dir REPORTS/ucua

The register is single-label (one of UC/UA per row) while the classifier emits two independent
flags, because a real report can be both. Scoring therefore reports two things:
  strict   the predicted PRIMARY label (the stronger flag) equals the human label
  lenient  the human label appears among the predicted flags
Both are printed. Strict is the honest headline.

Known label noise in the source: "Pallet roll on the feeder area not rotating" is tagged UA
though it plainly describes a condition. Rows like that cap the achievable score; they are
listed in the report rather than quietly absorbed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .config import REPO_ROOT
from .rules import find_spans
from .uc_ua import classify

REGISTER = REPO_ROOT / "DATA" / "Processed" / "register" / "near_miss_report_clean.jsonl"


def primary(r: dict) -> str | None:
    """One label from two flags: whichever side has more evidence, UC on a tie (a condition
    outlives the shift; an act is closed by a conversation)."""
    if r["unsafe_act"] and r["unsafe_condition"]:
        return "UA" if len(r["act_cues"]) > len(r["condition_cues"]) else "UC"
    if r["unsafe_act"]:
        return "UA"
    if r["unsafe_condition"]:
        return "UC"
    return None


def _html(out: Path, res: dict, rows: list[dict]) -> None:
    def cell(t, p):
        n = sum(1 for r in rows if r["truth"] == t and r["pred"] == p)
        cls = "hit" if t == p else "miss"
        return f'<td class="cm {cls}">{n}</td>'
    bad = [r for r in rows if r["truth"] != r["pred"]]
    trs = "".join(
        f'<tr><td class="mono">{r["truth"]}</td><td class="mono bad">{r["pred"] or "-"}</td>'
        f'<td>{r["text"][:96]}</td>'
        f'<td class="mono small">{", ".join(c["cue"] for c in r["act_cues"]) or "-"}</td>'
        f'<td class="mono small">{", ".join(c["cue"] for c in r["condition_cues"]) or "-"}</td></tr>'
        for r in bad)
    out.write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<title>UC / UA - real register</title><style>
body{{font:14px/1.5 system-ui,sans-serif;margin:0;padding:32px;background:#f6f7f9;color:#1a1a1a}}
h1{{margin:0 0 4px;font-size:22px}} h2{{font-size:15px;margin:28px 0 10px;color:#444;
text-transform:uppercase;letter-spacing:.05em}} .sub{{color:#666;margin-bottom:24px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap}}
.card{{background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:16px 20px;min-width:150px}}
.card .v{{font-size:28px;font-weight:600}} .card .l{{color:#666;font-size:12px}}
.good{{color:#2e7d32}} .warn{{color:#b8860b}}
table{{border-collapse:collapse;background:#fff;border:1px solid #e3e6ea;border-radius:8px;width:100%}}
td,th{{padding:7px 12px;border-bottom:1px solid #eef0f2;text-align:left}}
th{{background:#fafbfc;font-size:12px;color:#555}}
.cm{{text-align:center;font-weight:600}} .cm.hit{{background:#e8f2e8;color:#2e7d32}}
.cm.miss{{background:#fbeaea;color:#c0504d}} .bad{{color:#c0504d}}
.mono{{font-family:ui-monospace,monospace;font-size:12px}} .small{{color:#777}}
.note{{background:#fff8e6;border:1px solid #f0e0b0;border-radius:8px;padding:12px 16px;margin:18px 0}}
</style></head><body>
<h1>Unsafe Act / Unsafe Condition</h1>
<div class="sub">{res['n']} <b>real</b> human-labelled near-miss register rows &middot; rules, no training data used</div>
<div class="cards">
  <div class="card"><div class="v good">{res['strict_accuracy']:.3f}</div><div class="l">strict accuracy</div></div>
  <div class="card"><div class="v">{res['lenient_accuracy']:.3f}</div><div class="l">lenient (label among flags)</div></div>
  <div class="card"><div class="v">{res['ua_recall']:.2f}</div><div class="l">UA recall</div></div>
  <div class="card"><div class="v">{res['uc_recall']:.2f}</div><div class="l">UC recall</div></div>
  <div class="card"><div class="v">{res['both_flags']}</div><div class="l">rows flagged UC <i>and</i> UA</div></div>
  <div class="card"><div class="v">{res['no_flag']}</div><div class="l">no flag raised</div></div>
</div>
<div class="note"><b>This is the only real labelled data in the project.</b> It is a paper-mill
register in English, not oil &amp; gas Hinglish, and the source labels carry noise - e.g.
"Pallet roll on the feeder area not rotating" is tagged UA though it describes a condition.
Those rows cap the achievable score.</div>
<h2>Confusion (human &rarr; predicted)</h2>
<table><tr><th></th><th>&rarr;UA</th><th>&rarr;UC</th></tr>
<tr><th>UA</th>{cell('UA','UA')}{cell('UA','UC')}</tr>
<tr><th>UC</th>{cell('UC','UA')}{cell('UC','UC')}</tr></table>
<h2>Disagreements ({len(bad)})</h2>
<table><tr><th>human</th><th>predicted</th><th>text</th><th>act cues</th><th>condition cues</th></tr>{trs}</table>
</body></html>""", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="evaluate UC/UA on the real register")
    ap.add_argument("--data", default=str(REGISTER))
    ap.add_argument("--out-dir", default="REPORTS/ucua")
    ap.add_argument("--show", action="store_true", help="print every disagreement")
    a = ap.parse_args(argv)

    src = Path(a.data)
    if not src.exists():
        raise SystemExit(f"{src} not found")
    rows = []
    for ln in src.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        t = (r.get("text") or "").strip()
        truth = (r.get("category") or "").upper()
        if not t or truth not in ("UA", "UC"):
            continue
        c = classify(t, find_spans(t))
        rows.append({"text": t, "truth": truth, "pred": primary(c),
                     "flags": c["labels"], "act_cues": c["act_cues"],
                     "condition_cues": c["condition_cues"], "conf": c["confidence"]})

    n = len(rows)
    strict = sum(1 for r in rows if r["pred"] == r["truth"])
    lenient = sum(1 for r in rows if r["truth"] in r["flags"])
    ua = [r for r in rows if r["truth"] == "UA"]
    uc = [r for r in rows if r["truth"] == "UC"]
    res = {
        "n": n,
        "truth_counts": dict(Counter(r["truth"] for r in rows)),
        "pred_counts": dict(Counter(r["pred"] for r in rows)),
        "strict_accuracy": round(strict / max(1, n), 3),
        "lenient_accuracy": round(lenient / max(1, n), 3),
        "ua_recall": round(sum(1 for r in ua if r["pred"] == "UA") / max(1, len(ua)), 3),
        "uc_recall": round(sum(1 for r in uc if r["pred"] == "UC") / max(1, len(uc)), 3),
        "both_flags": sum(1 for r in rows if len(r["flags"]) == 2),
        "no_flag": sum(1 for r in rows if not r["flags"]),
        "mean_confidence": round(sum(r["conf"] for r in rows) / max(1, n), 3),
    }
    print(json.dumps(res, indent=2))
    bad = [r for r in rows if r["pred"] != r["truth"]]
    print(f"\n{len(bad)} disagreement(s)")
    for r in (bad if a.show else bad[:10]):
        print(f"  human={r['truth']} pred={r['pred']}  {r['text'][:84]}")
        print(f"      act={[c['cue'] for c in r['act_cues']]} cond={[c['cue'] for c in r['condition_cues']]}")

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ucua_eval.json").write_text(json.dumps({**res, "rows": rows}, indent=2, ensure_ascii=False),
                                        encoding="utf-8")
    _html(out / "ucua_eval.html", res, rows)
    print(f"\nreport -> {out / 'ucua_eval.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
