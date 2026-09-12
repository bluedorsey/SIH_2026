# Antigravity as an offline teacher lane (rewind, balanced plan)

Paste the block below into Antigravity ONCE. It loops on its own until you stop it.

```
Project: E:\SIH_26

You are an offline teacher lane for the SIF-precursor training set. Work autonomously in a loop
until I stop you. Be terse - no explanations between batches.

SETUP (once):
  Run: python -m TRAINING.distill.offline --job rewind --next --bundle 8 --replan v2
  Then read DATA/distilled/offline/rules_rewind.md ONCE and keep those rules in mind.
  Do not open that file again unless a batch file says the rules CHANGED.

LOOP (repeat):
  1. Read DATA/distilled/offline/current_batch.md
     (seeds + the per-variant instructions - do NOT re-read the rules file)
  2. Write your JSON array to DATA/distilled/offline/answer.json
     - first character '[', last character ']', no markdown fences, no commentary
  3. Run: python -m TRAINING.distill.offline --submit --model antigravity-gemini
     It prints how many rows were accepted and the exact reason for any rejects.
  4. Read the reject reasons; avoid those mistakes in the NEXT batch
     (the batch just submitted is closed - do not retry it).
  5. Run: python -m TRAINING.distill.offline --job rewind --next --bundle 8 --replan v2
  6. Go to step 1.

CRITICAL for this job - every variant's four question values are FIXED by the batch file:
  rewind_A -> CAPACITY  (high_energy=true, released=true,  injury=false, control=true)
  rewind_B -> SUCCESS   (high_energy=true, released=false, injury=false, control=true)
Copy those values exactly. The verdict is DERIVED from them, so any other combination is
rejected as a contradiction. Never write a variant with the barrier missing (EXPOSURE/P_SIF)
- the corpus already has thousands and they are rejected as surplus.

Keep every span a verbatim substring of its own row's text and under 12 words.
Keep the 'original' row's text under 250 words.

NEVER edit DATA/distilled/raw/*.jsonl or *.state.json by hand.
```

## Batch size

Each batch = 3 seeds; each seed yields 3 rows (~330 output tokens per row).

    --bundle 5    15 seeds    45 rows   ~15k output tokens   verified clean
    --bundle 8    24 seeds    72 rows   ~24k output tokens   recommended ceiling
    --bundle 11   33 seeds    99 rows   ~33k output tokens   expect truncation

A reply that breaks halfway is salvaged element by element, but rows past the break are lost.
If rejects start clustering in the last rows of a batch, drop the bundle size.

## Stop when the gap is closed

    python -c "import json,collections;print(collections.Counter(json.loads(l)['verdict'] for l in open('DATA/distilled/raw/rewind.jsonl',encoding='utf-8') if l.strip()))"

Stop at roughly CAPACITY 800 and SUCCESS 840 - past that, class weights at training time
cover the remainder and more rows add little.

## Resuming

Re-paste the same block. `--next` reads the shared state file, so finished batches are never
re-issued. A batch left open by a crash is released automatically after 10 minutes, or now with:

    python -m TRAINING.distill.offline --release
