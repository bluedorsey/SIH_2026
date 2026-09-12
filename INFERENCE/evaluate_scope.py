"""
Evaluate the scope gate. Two sets, two numbers - gold-180 alone cannot score this, because
every row in it is in-scope and a gate that accepts everything would look perfect.

    python -m INFERENCE.evaluate_scope                                  # gold only (false rejects)
    python -m INFERENCE.evaluate_scope --probe DATA/scope/probe.jsonl   # + false accepts
    python -m INFERENCE.evaluate_scope --probe ... --out-dir REPORTS/scope

probe.jsonl: one object per line, {"text": "...", "in_scope": 0|1} - or "border" for rows that
are genuinely arguable. Border rows are reported separately and excluded from the headline,
because burying them inflates whatever you claim.

Build the probe set from REAL sampled OIL text you labelled yourself. If you generate it from
the same prompt that made the training negatives you are measuring memorisation, not the gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SWEEP = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.93, 0.95, 0.97, 0.99]


def _rows(p: Path) -> list[dict]:
    if not p.exists():
        raise SystemExit(f"{p} not found")
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _truth(r: dict):
    for k in ("in_scope", "label", "scope"):
        if k in r:
            v = r[k]
            if isinstance(v, str) and v.lower().startswith("bord"):
                return "border"
            return int(v)
    return 1


def _html(out: Path, res: dict) -> None:
    def bar(v, w=200, c="#4a7dbd"):
        return f'<div class="bar"><span style="width:{int(v * w)}px;background:{c}"></span></div>'
    rows = "".join(
        f'<tr class="{"ok" if s["gold_rejected"] == 0 else "bad"}">'
        f'<td class="mono">{s["threshold"]:.2f}</td>'
        f'<td class="cm {"hit" if s["gold_rejected"] == 0 else "miss"}">{s["gold_rejected"]}</td>'
        f'<td>{bar(s["junk_rate"], 200, "#7a9a5b")}<b>{s["junk_rate"]:.0%}</b></td>'
        f'<td class="mono small">{s["junk_caught"]}/{res["probe_out"]}</td></tr>'
        for s in res["sweep"])
    chosen = res["chosen"]
    misses = "".join(f'<tr><td class="mono">{m["p"]:.3f}</td><td>{m["text"][:110]}</td></tr>'
                     for m in res["false_rejects"][:15]) or \
             '<tr><td colspan="2" class="good">none - no gold precursor was rejected</td></tr>'
    out.write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<title>Scope gate - evaluation</title><style>
body{{font:14px/1.5 system-ui,sans-serif;margin:0;padding:32px;background:#f6f7f9;color:#1a1a1a}}
h1{{margin:0 0 4px;font-size:22px}} h2{{font-size:15px;margin:28px 0 10px;color:#444;
text-transform:uppercase;letter-spacing:.05em}} .sub{{color:#666;margin-bottom:24px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap}}
.card{{background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:16px 20px;min-width:150px}}
.card .v{{font-size:28px;font-weight:600}} .card .l{{color:#666;font-size:12px}}
.good{{color:#2e7d32}} .bad{{color:#c0504d}} .warn{{color:#b8860b}}
table{{border-collapse:collapse;background:#fff;border:1px solid #e3e6ea;border-radius:8px;width:100%}}
td,th{{padding:7px 12px;border-bottom:1px solid #eef0f2;text-align:left;vertical-align:middle}}
th{{background:#fafbfc;font-size:12px;color:#555}}
.bar{{display:inline-block;width:200px;height:9px;background:#eef0f2;border-radius:5px;
margin-right:8px;vertical-align:middle}} .bar span{{display:block;height:9px;border-radius:5px}}
.cm{{text-align:center;font-weight:600}} .cm.hit{{background:#e8f2e8;color:#2e7d32}}
.cm.miss{{background:#fbeaea;color:#c0504d}} tr.bad td{{opacity:.55}}
.mono{{font-family:ui-monospace,monospace;font-size:12px}} .small{{color:#777}}
.note{{background:#fff8e6;border:1px solid #f0e0b0;border-radius:8px;padding:12px 16px;margin:18px 0}}
</style></head><body>
<h1>Scope gate</h1>
<div class="sub">{res['gold_precursors']} sif=YES precursors of {res['gold_n']} gold rows &middot; {res['probe_n']} probe rows
({res['probe_out']} out-of-scope, {res['probe_border']} borderline excluded)</div>
<div class="cards">
  <div class="card"><div class="v {'good' if res['false_reject_n'] == 0 else 'bad'}">{res['false_reject_n']}</div>
    <div class="l">sif=YES precursors rejected &mdash; must be 0</div></div>
  <div class="card"><div class="v">{chosen if chosen is not None else '&mdash;'}</div>
    <div class="l">operating threshold</div></div>
  <div class="card"><div class="v">{res['junk_caught_pct']:.0%}</div><div class="l">out-of-scope junk caught</div></div>
  <div class="card"><div class="v">{res['yield_pct']:.0%}</div><div class="l">screening yield (passed rows that are real)</div></div>
  <div class="card"><div class="v">{res['volume_cut_pct']:.0%}</div><div class="l">traffic that never reaches GLiNER</div></div>
</div>
<div class="note"><b>The bar is a count, not a rate.</b> One rejected gold row is one dead
precursor. False accepts only cost review time, so they are the secondary number.</div>
<h2>Threshold sweep</h2>
<table><tr><th>threshold</th><th>gold rejected</th><th>junk caught</th><th></th></tr>{rows}</table>
<h2>Gold rows the gate rejected</h2>
<table><tr><th>p_out</th><th>text</th></tr>{misses}</table>
</body></html>""", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="evaluate the scope gate")
    ap.add_argument("--gold", default=None, help="gold jsonl (default: DATA/Processed/gold/gold.jsonl)")
    ap.add_argument("--probe", default=None, help="labelled probe jsonl (real sampled text)")
    ap.add_argument("--out-dir", default="REPORTS/scope")
    a = ap.parse_args(argv)

    from .config import REPO_ROOT
    from .scope import get_scope_gate

    gate = get_scope_gate()
    if not gate.available:
        raise SystemExit("no scope gate trained - run `python -m TRAINING.finetune.train_scope`")

    gold_p = Path(a.gold) if a.gold else REPO_ROOT / "DATA" / "Processed" / "gold" / "gold.jsonl"
    grows = [(r["text"].strip(), str(r.get("sif_potential") or "UNCERTAIN").upper())
             for r in _rows(gold_p) if (r.get("text") or "").strip()]
    gold = [t for t, _ in grows]
    is_yes = [lbl == "YES" for _, lbl in grows]
    gold_p_out = [gate.p_out_of_scope(t) or 0.0 for t in gold]

    probe, probe_out_idx, border = [], [], 0
    if a.probe:
        for r in _rows(Path(a.probe)):
            t = (r.get("text") or "").strip()
            if not t:
                continue
            y = _truth(r)
            if y == "border":
                border += 1
                continue
            probe.append((t, y))
    probe_p_out = [gate.p_out_of_scope(t) or 0.0 for t, _ in probe]
    probe_out_idx = [i for i, (_, y) in enumerate(probe) if y == 0]
    probe_in_idx = [i for i, (_, y) in enumerate(probe) if y == 1]

    sweep, chosen = [], None
    for thr in SWEEP:
        lost = sum(1 for i, p in enumerate(gold_p_out) if p > thr and is_yes[i])
        rejected = sum(1 for p in gold_p_out if p > thr)
        caught = sum(1 for i in probe_out_idx if probe_p_out[i] > thr)
        sweep.append({"threshold": thr, "gold_rejected": lost, "other_gold_rejected": rejected - lost,
                      "junk_caught": caught, "junk_rate": caught / max(1, len(probe_out_idx))})
        if lost == 0 and chosen is None and thr >= 0.70:
            chosen = thr

    thr = gate.threshold
    fr = [{"p": p, "text": t} for i, (p, t) in enumerate(zip(gold_p_out, gold))
          if p > thr and is_yes[i]]
    caught = sum(1 for i in probe_out_idx if probe_p_out[i] > thr)
    wrongly_cut = sum(1 for i in probe_in_idx if probe_p_out[i] > thr)
    passed = len(probe) - caught - wrongly_cut
    passed_real = len(probe_in_idx) - wrongly_cut

    res = {
        "threshold_in_use": thr, "chosen": chosen,
        "gold_n": len(gold), "gold_precursors": sum(is_yes),
        "acceptance_bar": "0 rows with sif_potential==YES rejected",
        "false_reject_n": len(fr), "false_rejects": fr,
        "probe_n": len(probe), "probe_out": len(probe_out_idx), "probe_in": len(probe_in_idx),
        "probe_border": border,
        "junk_caught_pct": caught / max(1, len(probe_out_idx)),
        "probe_in_wrongly_rejected": wrongly_cut,
        "yield_pct": passed_real / max(1, passed),
        "volume_cut_pct": (caught + wrongly_cut) / max(1, len(probe)),
        "sweep": sweep,
    }

    print(json.dumps({k: v for k, v in res.items() if k not in ("false_rejects", "sweep")}, indent=2))
    print(f"\n{'thr':>6} {'gold rejected':>14} {'junk caught':>12}")
    for s in sweep:
        flag = "  <- FAILS" if s["gold_rejected"] else ""
        print(f"{s['threshold']:6.2f} {s['gold_rejected']:14d} "
              f"{s['junk_caught']:6d} ({s['junk_rate']:4.0%}){flag}")
    if res["false_reject_n"]:
        print(f"\n!! {res['false_reject_n']} GOLD PRECURSORS REJECTED at the shipped threshold "
              f"{thr} - the gate must not go live. Raise the threshold or add training data.")
        for m in fr[:10]:
            print(f"   p_out={m['p']:.3f}  {m['text'][:100]}")
    else:
        print(f"\nPASS: 0 of {len(gold)} gold precursors rejected at threshold {thr}")

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "scope_eval.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    _html(out / "scope_eval.html", res)
    print(f"report -> {out / 'scope_eval.html'}")
    return 1 if res["false_reject_n"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
