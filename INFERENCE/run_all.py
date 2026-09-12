"""
Run the whole validation suite in one command and write a single index page.

    python -m INFERENCE.run_all                 # everything
    python -m INFERENCE.run_all --quick         # skip the model lane (rules only, ~5s)
    python -m INFERENCE.run_all --open          # print the index path to open

Runs, in order:
  1. barrier regression  - the GLiNER false-control bug must stay fixed
  2. gold-180 rules only - the deterministic baseline
  3. gold-180 full       - rules + GLiNER + heads + scope gate
  4. scope gate          - gold false-rejects + probe false-accepts (needs DATA/scope/probe.jsonl)
  5. UC / UA             - the 56 REAL human-labelled register rows

Exit code is non-zero if any SAFETY gate fails, so this works in CI:
  - a barrier regression case fails
  - SIF recall drops below --min-recall
  - the scope gate rejects a sif=YES precursor
Quality dips that are not safety failures (accuracy, review rate) are reported, not enforced.
"""
from __future__ import annotations

import argparse
import io
import json
import time
import contextlib
from pathlib import Path

from .config import PIPELINE_VERSION, REPO_ROOT

REPORTS = REPO_ROOT / "REPORTS"


def _run(fn, argv, label):
    """Call a module main() in-process (models load once) and capture its stdout."""
    buf = io.StringIO()
    t0 = time.time()
    try:
        with contextlib.redirect_stdout(buf):
            rc = fn(argv)
    except SystemExit as e:                              # noqa: PERF203
        rc = int(e.code or 0)
    except Exception as exc:                             # noqa: BLE001
        return {"label": label, "ok": False, "rc": 99, "secs": round(time.time() - t0, 1),
                "error": f"{type(exc).__name__}: {exc}", "stdout": buf.getvalue()}
    return {"label": label, "ok": rc == 0, "rc": rc, "secs": round(time.time() - t0, 1),
            "stdout": buf.getvalue()}


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:                                    # noqa: BLE001
        return {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="run the whole SIF validation suite")
    ap.add_argument("--quick", action="store_true", help="skip the model lane")
    ap.add_argument("--probe", default=str(REPO_ROOT / "DATA" / "scope" / "probe.jsonl"))
    ap.add_argument("--min-recall", type=float, default=0.90,
                    help="fail the run if SIF recall drops below this")
    ap.add_argument("--out-dir", default=str(REPORTS))
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    from . import evaluate as ev
    from . import evaluate_ucua as ev_ucua
    from . import test_barrier_regression as reg

    steps, fails = [], []

    print("1/5  barrier regression ...", flush=True)
    steps.append(_run(lambda _: reg.main(), None, "barrier regression"))
    if not steps[-1]["ok"]:
        fails.append("barrier regression case FAILED - the GLiNER false-control bug is back")

    print("2/5  gold-180 rules only ...", flush=True)
    steps.append(_run(ev.main, ["--no-models", "--out-dir", str(out / "gold180_rules")],
                      "gold-180 rules"))
    rules = _json(out / "gold180_rules" / "gold180_rules.json")

    full = {}
    if a.quick:
        print("3/5  gold-180 full ... SKIPPED (--quick)", flush=True)
        steps.append({"label": "gold-180 full", "ok": True, "rc": 0, "secs": 0,
                      "stdout": "skipped (--quick)"})
    else:
        print("3/5  gold-180 full (loads models, ~90s) ...", flush=True)
        steps.append(_run(ev.main, ["--out-dir", str(out / "gold180_full")], "gold-180 full"))
        full = _json(out / "gold180_full" / "gold180_full.json")

    scope = {}
    probe = Path(a.probe)
    if a.quick:
        print("4/5  scope gate ... SKIPPED (--quick)", flush=True)
        steps.append({"label": "scope gate", "ok": True, "rc": 0, "secs": 0, "stdout": "skipped"})
    else:
        print("4/5  scope gate ...", flush=True)
        from . import evaluate_scope as ev_scope
        argl = ["--out-dir", str(out / "scope")] + (["--probe", str(probe)] if probe.exists() else [])
        steps.append(_run(ev_scope.main, argl, "scope gate"))
        scope = _json(out / "scope" / "scope_eval.json")
        if scope.get("false_reject_n"):
            fails.append(f"scope gate rejected {scope['false_reject_n']} sif=YES precursor(s)")

    print("5/5  UC / UA on real register ...", flush=True)
    steps.append(_run(ev_ucua.main, ["--out-dir", str(out / "ucua")], "UC / UA (real data)"))
    ucua = _json(out / "ucua" / "ucua_eval.json")

    best = full or rules
    recall = ((best.get("sif") or {}).get("recall"))
    if recall is not None and recall < a.min_recall:
        fails.append(f"SIF recall {recall} below the {a.min_recall} floor")

    summary = {
        "pipeline_version": PIPELINE_VERSION,
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "quick (rules only)" if a.quick else "full",
        "rules": {k: rules.get(k) for k in ("accuracy", "review_rate", "mean_spans")} | {
            "sif": rules.get("sif")},
        "full": {k: full.get(k) for k in ("accuracy", "review_rate", "mean_spans",
                                          "scope_gated", "scope_gated_precursors")} | {
            "sif": full.get("sif")} if full else None,
        "scope": {k: scope.get(k) for k in ("threshold_in_use", "false_reject_n", "gold_precursors",
                                            "junk_caught_pct", "yield_pct", "volume_cut_pct")} if scope else None,
        "uc_ua": {k: ucua.get(k) for k in ("n", "strict_accuracy", "ua_recall", "uc_recall")} if ucua else None,
        "steps": [{k: v for k, v in s.items() if k != "stdout"} for s in steps],
        "failures": fails,
        "passed": not fails,
    }
    (out / "suite.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    _index(out / "index.html", summary, steps)

    # ------------------------------------------------------------------ console scoreboard
    bar = "=" * 66
    print(f"\n{bar}\n  SIF PRECURSOR ENGINE  -  validation suite  (v{PIPELINE_VERSION})\n{bar}")
    def row(name, d):
        s = (d or {}).get("sif") or {}
        if not s:
            return
        print(f"  {name:22s} recall {s['recall']:.3f}   F2 {s['f2']:.3f}   "
              f"missed {s['fn']:2d}   acc {(d.get('accuracy') or 0):.3f}   "
              f"review {(d.get('review_rate') or 0):.0%}")
    row("gold-180 rules", rules)
    row("gold-180 full", full)
    if scope:
        print(f"  {'scope gate':22s} thr {scope.get('threshold_in_use')}   "
              f"precursors lost {scope.get('false_reject_n')}   "
              f"junk caught {(scope.get('junk_caught_pct') or 0):.0%}   "
              f"volume cut {(scope.get('volume_cut_pct') or 0):.0%}")
    if ucua:
        print(f"  {'UC/UA (REAL data)':22s} accuracy {ucua.get('strict_accuracy'):.3f}   "
              f"UA recall {ucua.get('ua_recall'):.2f}   UC recall {ucua.get('uc_recall'):.2f}   "
              f"n={ucua.get('n')}")
    print(bar)
    for s in steps:
        print(f"  {'ok  ' if s['ok'] else 'FAIL'} {s['label']:24s} {s['secs']:6.1f}s"
              + (f"   {s.get('error', '')}" if not s["ok"] else ""))
    if fails:
        print(f"\n  {len(fails)} SAFETY FAILURE(S):")
        for f in fails:
            print(f"    * {f}")
    else:
        print("\n  all safety gates passed")
    print(f"\n  index -> {out / 'index.html'}\n{bar}")
    return 1 if fails else 0


def _index(path: Path, s: dict, steps: list[dict]) -> None:
    def card(v, l, cls=""):
        return f'<div class="card"><div class="v {cls}">{v}</div><div class="l">{l}</div></div>'
    r, f = s.get("rules") or {}, s.get("full") or {}
    rs, fs = r.get("sif") or {}, f.get("sif") or {}
    sc, uu = s.get("scope") or {}, s.get("uc_ua") or {}
    cards = ""
    if fs or rs:
        b = fs or rs
        cards += card(f"{b.get('recall', 0):.3f}", "SIF recall &mdash; the number that matters", "good")
        cards += card(b.get("fn", "-"), "missed precursors", "bad" if b.get("fn") else "good")
        cards += card(f"{b.get('f2', 0):.3f}", "F2 (recall-weighted)")
    if uu:
        cards += card(f"{uu.get('strict_accuracy', 0):.3f}", "UC/UA on <b>real</b> data", "good")
    if sc:
        cards += card(sc.get("false_reject_n", "-"), "precursors lost to scope gate",
                      "good" if not sc.get("false_reject_n") else "bad")
        cards += card(f"{(sc.get('volume_cut_pct') or 0):.0%}", "traffic gated before GLiNER")
    links = "".join(
        f'<li><a href="{p}">{n}</a></li>' for n, p in (
            ("gold-180 &mdash; rules only", "gold180_rules/gold180_rules.html"),
            ("gold-180 &mdash; full stack", "gold180_full/gold180_full.html"),
            ("scope gate", "scope/scope_eval.html"),
            ("UC / UA (real register)", "ucua/ucua_eval.html")))
    rows = "".join(f'<tr><td>{x["label"]}</td><td class="{"ok" if x["ok"] else "bad"}">'
                   f'{"pass" if x["ok"] else "FAIL"}</td><td class="mono">{x["secs"]}s</td></tr>'
                   for x in steps)
    banner = ('<div class="pass">All safety gates passed.</div>' if s["passed"]
              else '<div class="fail"><b>SAFETY FAILURE</b><ul>'
                   + "".join(f"<li>{x}</li>" for x in s["failures"]) + "</ul></div>")
    path.write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<title>SIF engine - validation suite</title><style>
body{{font:14px/1.6 system-ui,sans-serif;margin:0;padding:32px;background:#f6f7f9;color:#1a1a1a;
max-width:1000px}}
h1{{margin:0 0 4px;font-size:23px}} h2{{font-size:14px;margin:28px 0 10px;color:#444;
text-transform:uppercase;letter-spacing:.05em}} .sub{{color:#666;margin-bottom:22px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap}}
.card{{background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:16px 20px;min-width:150px}}
.card .v{{font-size:27px;font-weight:600}} .card .l{{color:#666;font-size:12px}}
.good{{color:#2e7d32}} .bad{{color:#c0504d}} .ok{{color:#2e7d32;font-weight:600}}
table{{border-collapse:collapse;background:#fff;border:1px solid #e3e6ea;border-radius:8px;width:100%}}
td,th{{padding:7px 12px;border-bottom:1px solid #eef0f2;text-align:left}}
th{{background:#fafbfc;font-size:12px;color:#555}}
.mono{{font-family:ui-monospace,monospace;font-size:12px}}
ul{{padding-left:20px}} a{{color:#2b6cb0}}
.pass{{background:#e8f2e8;border:1px solid #bcd9bc;color:#2e7d32;border-radius:8px;
padding:12px 16px;margin:18px 0;font-weight:600}}
.fail{{background:#fbeaea;border:1px solid #e3b7b7;color:#c0504d;border-radius:8px;
padding:12px 16px;margin:18px 0}}
</style></head><body>
<h1>SIF precursor engine &mdash; validation suite</h1>
<div class="sub">pipeline v{s['pipeline_version']} &middot; {s['mode']} &middot; {s['ran_at']}</div>
<div class="cards">{cards}</div>
{banner}
<h2>Reports</h2><ul>{links}</ul>
<h2>Steps</h2><table><tr><th>step</th><th>result</th><th>time</th></tr>{rows}</table>
</body></html>""", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
