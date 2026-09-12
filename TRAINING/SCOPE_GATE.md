# Scope gate — runbook

A logistic layer over the **frozen** multilingual encoder, run before GLiNER. It answers
*"is this a safety observation at all?"* — a topic question, easy — and is deliberately kept
separate from the `prefilter` head, which answers *"is it severe enough?"* — a judgment
question, hard, and measured at **recall_sif 0.75**. A gate at 0.75 kills one precursor in four,
which is why prefilter must never gate anything.

The encoder is never fine-tuned. 118M encoder parameters on a few hundred negatives is exactly
how the SetFit body run reached train loss 0.002 against eval 0.281. The head is 385 parameters.

## 0. Data you must create

The distilled corpus has **zero** out-of-domain rows, so the negative class does not exist yet.

    DATA/scope/negatives.jsonl     ~250 synthetic + ~150 real + ~50 mirror positives

One JSON object per line:

    {"text":"Pump room ka AC kharab hai","label":0,"kind":"hard_negative","lang":"hinglish","batch":"B1"}
    {"text":"Coffee machine ke pas LPG cylinder leak kar raha tha","label":1,"kind":"mirror_positive", ...}

- `label` 0 = out of scope, 1 = mirror positive (domestic words, real hazard — these stop the
  model learning "canteen = ignore" and eating real reports).
- Synthetic rows: generate in Antigravity, no OIL data involved, no governance problem.
- Real rows: sample unlabelled OIL text and label binary yourself, offline. ~3 s/row.

## 1. Train

    python -m TRAINING.finetune.prepare_scope_data
    python -m TRAINING.finetune.train_scope

`train_scope` picks the operating point itself: it sweeps P(out_of_scope) from 0.50 to 0.99 and
takes the **highest cut that rejects zero rows of gold-180**. If no threshold clears that bar it
writes `scope_enabled: false` and the gate stays inert — a gate that cannot be made safe does
not ship.

Useful flags:

    --C 0.5              stronger regularisation
    --min-threshold 0.80 never ship an operating point below this
    --no-gold-sweep      skip the acceptance bar (diagnostics only — do not ship this)

## 2. Evaluate

    python -m INFERENCE.evaluate_scope --probe DATA/scope/probe.jsonl

`probe.jsonl` is a **separate** set — real OIL text, randomly sampled, labelled by you:

    {"text":"...","in_scope":0}          out of scope
    {"text":"...","in_scope":1}          in scope
    {"text":"...","in_scope":"border"}   arguable — reported separately, excluded from headline

Do not build the probe negatives from the same prompt that made the training negatives. They
will share phrasing and you will measure memorisation at 0.99 while the real thing fails.

Reported numbers:

| number | meaning | bar |
|---|---|---|
| gold precursors rejected | false rejects | **0 — a count, not a rate** |
| junk caught | false accepts avoided | as high as possible, secondary |
| screening yield | of rows that pass, how many are real | the number that decides if a supervisor keeps using the queue |
| volume cut | traffic that never reaches GLiNER | the compute/cost story |

Exit code is non-zero when any gold row is rejected, so it works in CI.

## 3. Run

    python -m INFERENCE.cli "Workshop ke washroom ki safai nahi hui"
    python -m uvicorn INFERENCE.api:app --port 8000

Every response now carries a `scope` block, and rejected rows come back with
`verdict.label = "OUT_OF_SCOPE"`, full schema intact.

## How it decides

```
text
 ├─ encoder.encode(text)        already in memory for the other heads
 │    └─ scope head             385 params, ~0.1 ms
 ├─ find_spans(text)            regex, microseconds
 │
 ├─ REJECT if P(out_of_scope) > threshold AND no veto span
 │      veto roles: control_absent, control_ineffective, release_cue,
 │                  outcome_cue, pseudo_control
 │      -> "barricading nahi tha" is never thrown away, whatever the score
 │
 └─ otherwise -> GLiNER -> energy -> four questions -> tree
```

Reject is a verdict, not a delete. The row keeps the full contract and stays queryable — in a
safety system you never silently discard a report, and OIL will ask what happened to it. It
leaves the human queue; it does not leave the database.

## Kill switch

`INFERENCE/config.py`:

    SCOPE_ENABLED = False     # gate never fires, pipeline behaves as before

Also honoured: `scope_enabled` in `scope_meta.json`, written by training.

## What this does NOT fix

- GLiNER still hallucinates `energy_cue` on rows that pass. That needs the same negatives in
  GLiNER's training set as rows with zero spans.
- The gate will eventually be wrong. Keep the evidence-quorum rule in `decide.py`: one
  unsupported model span plus three defaults must not produce a verdict, whatever the gate said.
