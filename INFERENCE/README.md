# INFERENCE — production runtime (SIH26165)

Standalone. Never imports CLEANING or TRAINING; at run time it needs only the model folders.

    DATA/        data only
    CLEANING/    data processing
    TRAINING/    model training + evaluation
    INFERENCE/   production runtime   <- this package
    SERVER/      models + deployment

## Use

    python -m INFERENCE.cli "Monkey board se tool box neeche gira, barricading nahi tha"
    python -m INFERENCE.cli --file reports.txt --out results.jsonl
    python -m INFERENCE.cli --no-models "..."          # rules only, no model load
    uvicorn INFERENCE.api:app --port 8000              # POST /analyse, /batch, GET /health

## Layers

    rules.py      language, statement type, span evidence, negation SCOPE   (always on)
    scope.py      is this a safety observation at all - gate + evidence gate (optional)
    models.py     GLiNER spans + SetFit heads                              (optional)
    knowledge.py  hazard -> barrier -> consequence -> cluster, mass/height defaults
    energy.py     m*g*h and the SIF thresholds (fall 1.2 m, dropped object 680 J, 50 V, 65 C)
    decide.py     fuse spans -> the FOUR questions -> EEI tree -> verdict
    pipeline.py   assembles the response

Missing models degrade, never crash: no GLiNER -> rules-only spans; no heads -> the tree decides
alone. `GET /health` reports which layers are live.

## Two gates, not one

A report that is not about safety at all - a canteen complaint, an IT ticket, "AC ka remote
kharab ho gaya" - must never cost a reviewer a minute. Two layers keep it out of the queue.

    scope gate     scope.py    BEFORE GLiNER.  Rejects when P(out_of_scope) > 0.95.
    evidence gate  scope.py    AFTER GLiNER + heads.  Dismisses when NOTHING vouches for the row.

The scope gate is set for recall, so it only fires when it is nearly certain, and on its own it
caught under half the junk. Everything it let through reached the EEI tree, where the safety
defaults do their job too well: no barrier stated -> `control_present=False`, no release stated
-> `energy_released=False`, and one low-confidence GLiNER span ("AC" as an energy source, 0.64)
is enough for `high_energy=True`. Three defaults and a bad span produce EXPOSURE at 0.48, which
is below the review threshold - so the reviewer gets an AC remote.

The evidence gate closes that. A row the scope gate could not reject outright is dismissed as
OUT_OF_SCOPE only when EVERY layer comes back empty: no safety-domain word
(`knowledge.SAFETY_VOCAB`), no hand-written rule span, no hazard, no numeric energy, no GLiNER
span above 0.80 in a meaningful role, and both sentence heads saying "not a precursor". ONE
corroborating signal keeps the row - the asymmetry is still the scope gate's. Two things are
never dismissed: a row the scope gate positively vouches for (p_out < 0.35), and an unscorable
one ("Nil", "As per annexure") - an empty report is not an off-domain report, and it belongs in
the review queue exactly as before.

Rows dismissed here keep the full response contract with `verdict=OUT_OF_SCOPE`, the GLiNER and
head output that was used, and the `decision_path` naming every layer that came back empty - so
a dismissal is auditable, never a silent deletion.

Separately, `decide.py` no longer sends a row to review on low confidence ALONE. When the tree,
the verdict head and the prefilter head all say "not a precursor", the row is closed; any layer
dissenting keeps it queued.

Measured with the full stack (gold-180 + the 103-row scope probe):

    gold-180 recall on YES          0.989 -> 0.989   (no precursor lost)
    gold-180 rows sent to review    81/180 -> 72/180
    gold-180 3-class accuracy       0.628 -> 0.661
    probe junk sent to review       45/72  -> 11/72
    probe in-scope wrongly dropped  0      -> 0

Knobs, all in `config.py`: `EVIDENCE_GATE_ENABLED` (kill switch), `SCOPE_SOFT_THRESHOLD`,
`GLINER_STRONG_SCORE`, `EVIDENCE_HEAD_MIN_CONFIDENCE`. Raising the last two dismisses more junk;
re-run `python -m INFERENCE.evaluate` and `python -m INFERENCE.evaluate_scope --probe
DATA/scope/probe.jsonl` before trusting any change, and treat "0 gold YES rejected" as the bar.

## Why the verdict is trustworthy

It is DERIVED, never asserted. The tree reads four question values, each carrying the verbatim
span and character offsets that produced it, so `decision_path` can always be shown to a reviewer:

    high_energy=True AND energy_released=True AND serious_injury=False
    AND control_present=False -> P_SIF (no barrier, nobody hurt this time)

## The trap this is built around

"Koi injury nahi hui" negates the OUTCOME - the exposure still happened, so potential severity is
unchanged. "Barricading nahi tha" negates a CONTROL, which RAISES severity. Treating the two alike
is how a real SIF precursor gets closed as a non-event. `rules.negation_scope()` separates them and
reports which applies.

## Config

`config.py` holds paths, thresholds and `PIPELINE_VERSION` (stamped into every response).
Set `SIF_REPO_ROOT` to relocate. `SPAN_THRESHOLD` (0.60) is the GLiNER cut-off for a span to
enter the tree at all; `GLINER_STRONG_SCORE` (0.80) is the higher bar a span must clear to count
as evidence that the report is in scope.
