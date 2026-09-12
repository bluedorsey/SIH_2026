"""
Regression guard for the gold-180 full-model collapse (recall 0.956 -> 0.911, SUCCESS 3 -> 19).

GLiNER tagged the barrier NOUN and ignored its STATE: "chin strap khula", "relief valve
blocked", "escape ladder tuta hua" all produced a high-scoring control_present span, and the
tree read `energy_released=False AND control_present=True` as SUCCESS - a precursor filed as a
good-news story. Each case below injects the exact false span GLiNER produced.

    python -m INFERENCE.test_barrier_regression
"""
from __future__ import annotations

from .decide import decide
from .energy import estimate
from .knowledge import detect_hazard
from .rules import detect_statement_type, find_spans, negation_scope

# (id, text, the noun GLiNER mislabelled as control_present, must_be_success)
CASES: list[tuple[str, str, str, bool]] = [
    ("gold_R011", "Derrick pe 12 meter height pe kaam kar raha tha, helmet ka chin strap khula tha.",
     "chin strap", False),                                   # defective control
    ("gold_R038", "Portable DG set ka exhaust room ke andar tha aur darwaza band tha.",
     "darwaza", False),
    ("gold_R048", "Trench ke bilkul kinare pe excavated soil rakhi hui thi, depth 3 m.",
     "excavated soil", False),                               # hazard noun, not a barrier
    ("gold_R054", "Pipeline se illegal tapping ki koshish dekhi gayi, aas paas log maujud the.",
     "Pipeline", False),                                     # hazard noun
    ("gold_R089", "Mud pump ka relief valve line blocked mili.", "relief valve", False),
    ("gold_R153", "Escape ladder ka niche ka portion tuta hua tha, platform pe do log kaam kar rahe the.",
     "Escape ladder", False),
    ("gold_R169", "Line ka pressure high tha aur worker ne flange kholna shuru kiya.",
     "flange", False),                                       # barrier being removed
    ("control_intact",
     "Height 10 meter pe kaam, worker ne full body harness pehna tha aur anchor point verified tha.",
     "full body harness", True),                             # a real SUCCESS must survive
]


def verdict_for(text: str, noun: str) -> str:
    i = text.find(noun)
    spans = find_spans(text)
    if i >= 0:
        spans = spans + [{"role": "control_present", "text": noun, "start": i,
                          "end": i + len(noun), "score": 0.71, "source": "gliner"}]
    out = decide(text, spans, estimate(text, detect_hazard(text)),
                 negation_scope(text, spans), detect_statement_type(text), None)
    return out["verdict"]["label"]


def main() -> int:
    bad = 0
    for rid, text, noun, want_success in CASES:
        got = verdict_for(text, noun)
        ok = (got == "SUCCESS") if want_success else (got != "SUCCESS")
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {rid:16s} {got:9s} "
              f"(expected {'SUCCESS' if want_success else 'not SUCCESS'})")
    print(f"\n{len(CASES) - bad}/{len(CASES)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
