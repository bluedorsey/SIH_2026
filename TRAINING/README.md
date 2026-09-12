# TRAINING — teacher distillation + fine-tuning for SIH26165 (Oil India SIF precursor engine)

```
TRAINING/
  config.py                 paths, label spec (11 roles, 9 verdicts, barriers, LSRs), quotas, API backends + job chains
  distill/                  teacher-LLM batch distillation (7 keys, 4 providers, checkpoint + fallback)
     backends.py            OpenAI-style client: lanes per key, RPM/RPD/TPM throttle, 429/402/403 failover, JSON repair
     prompts.md / prompts.py  §0 spec, §1 generate, §2 rewind, §3 label, §4 agree  (from the repo's prompts.md)
     schema.py              validator: verbatim spans ≤12 tokens, EEI decision-tree verdict check, barrier vocab
     runner.py              jobs (generate / rewind / label / agree) with resumable state files
     run_distill.py         CLI
     filter_distilled.py    re-validate, MinHash near-dup + gold/IHM leakage guard, quotas, seed-grouped 80/10/10 split
     make_exemplars.py      26 hand-written validated rows (few-shot + smoke data)
  finetune/
     tokenization.py        Indic-aware word splitter (Devanagari/Bengali vowel signs) shared by data prep + GLiNER
     prepare_gliner_data.py distilled -> GLiNER json (tokenized_text + ner)
     train_gliner.py        GLiNER fine-tune (gliner Trainer, per-epoch checkpoints, resume, own span-F1 eval)
     prepare_setfit_data.py distilled -> sentence tasks (prefilter / verdict / statement_type / lsr)
     train_setfit.py        --mode head (CPU, minutes)  |  --mode setfit (GPU)
     heads.py               SifHeads.load(...).predict(texts) — one loader for both modes (server uses this)
     colab_train.ipynb      GPU notebook (Drive-backed checkpoints)
  eval/evaluate_gold.py     gold-180 per trap family, SIF recall/F2, LSR F1, IHM agreement
  weak_label_gliner.py      glossary + cue lexicon -> weak GLiNER rows (no API)
  setup_models.py           repairs the base models in SERVER/Classfication/Models/RAW (encoder/NLI/GLiNER tokenizer) and verifies they load
  distill_one_go.ps1 / train_after_distill.ps1   Windows launchers: pilot + 5-window distillation, then the whole training chain
  pack_for_colab.py         zips data + package for the notebook
  checkpoints/              (created at run time; git-ignore it)
```

Outputs land in `DATA/distilled/` (teacher rows, splits, reports) and `SERVER/Classfication/Models/Tunned/{gliner_sif, sif_heads}` — each fine-tuned model in its own folder; base models live in `Models/RAW/`.

## 0. One-time setup

```powershell
cd E:\SIH_26
pip install -r CLEANING\requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu      # laptop CPU wheel (skip on Colab)
pip install -r TRAINING\requirements-train.txt
copy .env.example .env      # paste keys: GEMINI_API[_n], GROQ_API_n, SARVAM_API_n, OPENROUTER_API_n - any number per provider, used in order
```

`.env` is read by `TRAINING/config.py` (`load_env()`); environment variables override it; nothing ever prints a key.
Keys are auto-discovered (`PROVIDER_API`, `PROVIDER_API_1`, `_2`, `_3` ...): when a key's daily cap / budget is reached the
next key of the same provider takes over; identical values are merged (same account = same quota).

If `pip`/`uv` times out downloading wheels ("Request failed after 4 retries"), raise the timeout and retry - the
download resumes from the cache:  `$env:UV_HTTP_TIMEOUT='900'; uv pip install -r TRAINING\requirements-train.txt`
or `python -m pip install --timeout 900 --retries 10 -r TRAINING\requirements-train.txt`; on a bad connection add
`--index-url https://pypi.tuna.tsinghua.edu.cn/simple` (mirror) or download the failing wheel in the browser and `pip install <file>.whl`.

### More free tiers (optional, all OpenAI-compatible, no card)

| provider | sign up | free limits | key name in .env | used for |
|---|---|---|---|---|
| NVIDIA NIM | https://build.nvidia.com (phone verification) | 40 req/min, **no daily token cap**, ~80 models | `NVIDIA_API_1` | rewind + label volume |
| Mistral (Experiment plan) | https://console.mistral.ai | 1 req/s, 500k tokens/min, **1B tokens/month** | `MISTRAL_API_1` | generate + rewind |
| Cerebras | https://cloud.cerebras.ai | ~5 req/min, 1M tokens/day, requests capped at 8k tokens | `CEREBRAS_API_1` | label / agree (4-row batches) |
| OpenRouter `:free` | https://openrouter.ai | 50 req/day per account (1000/day after a one-time $10 top-up); the free model list rotates and is re-discovered at start-up | `OPENROUTER_API_n` | safety net |

Add the key, re-run `distill_one_go.ps1` - it opens an extra window per provider that has a key. Model ids for these
providers are re-checked against `/v1/models` at start-up, so a retired id never stops a run.

## 1. Data pipeline (must be complete before distillation)

```powershell
python -m CLEANING.fetch.fetch_all                        # MSHA / IADC / IMCA / GitHub mirrors (skips what exists)
python -m CLEANING.run_pipeline --gold --osha-abstracts --ihm --msha --alerts
python -m CLEANING.test_cleaning
```
Produces `DATA/Processed/unified/teacher_input.jsonl` (rewind + label seeds), `gold/gold.jsonl`, `ihm/ihm_eval.jsonl`,
`terms/glossary_clean.json`, `readiness_report.md`.

## 2. Distillation (batch, resumable, key-rotating)

```powershell
python -m TRAINING.distill.make_exemplars                 # 26 validated few-shot rows  -> distill/exemplars.jsonl
python -m TRAINING.distill.run_distill --status           # which keys are loaded, per-job progress, usage
python -m TRAINING.distill.run_distill --job generate --dry-run --limit 1     # prints the prompt, calls nothing

# pilot: 2 batches per job, check DATA/distilled/raw/*.rejects.jsonl before spending quota
python -m TRAINING.distill.run_distill --job generate --limit 2
python -m TRAINING.distill.run_distill --job rewind   --limit 3
python -m TRAINING.distill.run_distill --job label    --limit 2

# full run (re-run the same command after any stop; finished batches are skipped)
python -m TRAINING.distill.run_distill --job all
python -m TRAINING.distill.run_distill --job agree              # 2nd-teacher agreement sample -> raw/agreement.json

# pin a provider (e.g. keep Sarvam for Hinglish generation):  --backend sarvam
# only OISD/India seeds:                                       --job rewind --source oisd
```

How limits are handled: each key is a *lane* with its own RPM/RPD counters. A 429 → sleep + rotate to the next lane;
a 429 whose body says daily/quota/credits (or 3 in a row) → lane marked exhausted for the day; 402/403 → lane dead.
When every lane of a job's chain is exhausted the job stops with `BackendExhausted` and the state file keeps the
finished batches, so the next invocation continues. Chains (`config.JOB_CHAINS`): generate = sarvam → gemini →
openrouter → groq; rewind = gemini → sarvam → …; label = gemini → groq → …; agree = groq → openrouter → gemini.
Sarvam spend is estimated in `DATA/distilled/raw/usage.json`.

Budget (defaults in config, seed counts as of 2026-09-07): generate 9 000 rows (450 batches of 20 — raised from 4 500
because the seeds are 99 % English and the Hinglish / Devanagari / Assamese share of the corpus comes only from §1 and
the rewind language rotation); rewind 2 745 seeds (IOGP 663, OSHA abstracts 915, IADC 748, IMCA 406, OISD 13) × 4 rows
= 830 requests of 3 seeds after the per-source caps; label 1 600 rows = 80 batches → ≈ 1 450 requests total, ≈ 16 M
tokens. Sarvam's free signup credit is only Rs 100 per key (~150 generate batches at Rs 29/73 per 1M tokens), so the
runner schedules the Devanagari/Assamese-heavy batches first for Sarvam and parks each Sarvam key at `budget_inr`
(Rs 95); everything else flows to Gemini (250-500 requests/day) - about 4-6 days unattended in total. Rewind runs OISD → India → onshore → IADC first, so
`--job rewind --limit 400` already gives the most Oil-India-like seeds if quota is short. Every §1 batch also carries an
LSR focus (Energy Isolation / Confined Space / Hot Work / Work Authorisation / Bypassing / Driving rotate) because the
seed pool barely mentions those rules. `python -m CLEANING.audit_relevance` prints the current numbers.

### One-go plan (everything in one day, 4-5 PowerShell windows in parallel)

Every Gemini and Groq *model* has its own daily quota, so one key is split into one lane per model
(`split_model_lanes` in config: gemini-2.5-flash → 2.0-flash → 2.5-flash-lite; gpt-oss-120b → qwen3-32b → llama-70b) and
several windows may work on the SAME job at once - batches are claimed atomically, state is merged under a lock, and
`--reverse` makes a second window start from the other end of the batch list.

```powershell
# 1  Indic-heavy generation on the Sarvam credit (parks itself at Rs 95 per key)            ~2 h
python -m TRAINING.distill.run_distill --job generate --backend sarvam
# 2  the rest of generation on Gemini, working from the English-heavy end of the list       ~4-5 h
python -m TRAINING.distill.run_distill --job generate --backend gemini --reverse
# 3  rewind on Gemini (2.5-flash first, then 2.0-flash / flash-lite when a daily bucket ends) ~5-6 h
python -m TRAINING.distill.run_distill --job rewind --backend gemini
# 4  label on Groq (tiny 5-row batches across the three per-model token buckets)            ~2 h
python -m TRAINING.distill.run_distill --job label --backend groq
# 5  (optional) second rewind window on OpenRouter/Groq from the other end
python -m TRAINING.distill.run_distill --job rewind --backend openrouter --reverse
# when 3 and 5 are finished:
python -m TRAINING.distill.run_distill --job agree
```
Re-running any command later resumes; `--status` shows every lane, what it did today and why it stopped.
If a window stops with "all lanes exhausted" before the list is done, that provider's day is over - just run it again tomorrow.

```powershell
python -m TRAINING.distill.filter_distilled --enforce-quotas   # -> DATA/distilled/{train,dev,test}.jsonl + distill_report.md
```

## 3. Model folders

```powershell
python -m TRAINING.setup_models            # downloads what is missing (encoder, NLI config, GLiNER tokenizer) and verifies loading
python -m TRAINING.setup_models --verify   # check only
```

## 4. Prepare + train

```powershell
python -m TRAINING.weak_label_gliner                       # optional warm-up rows from glossary/cue lexicon
python -m TRAINING.finetune.prepare_gliner_data --weak     # DATA/distilled/gliner/{train,dev,test}.json
python -m TRAINING.finetune.prepare_setfit_data            # DATA/distilled/setfit/{train,dev,test}.jsonl

# sentence heads on CPU (minutes): prefilter / verdict / statement_type / LSR  -> Models/Tunned/sif_heads
python -m TRAINING.finetune.train_setfit --mode head

# GLiNER: smoke on CPU, real training on Colab
python -m TRAINING.finetune.train_gliner --smoke
python -m TRAINING.pack_for_colab            # -> sih_train_bundle.zip  (upload to Drive/SIH_26/, open finetune/colab_train.ipynb; trained models come back as sif_models.zip -> unzip at repo root -> Models/Tunned/)
#   Colab:  python -m TRAINING.finetune.train_gliner --epochs 3 --batch 8 --lr 1e-5 --device cuda --resume
#   optional on GPU: python -m TRAINING.finetune.train_setfit --mode setfit --epochs 1 --iterations 20 --device cuda
```

## 5. Evaluate

```powershell
python -m TRAINING.eval.evaluate_gold                  # TRAINING/eval/reports/gold_eval.md (+ IHM agreement)
python -m TRAINING.finetune.train_gliner --eval-only   # span P/R/F1 per role on the test split
```

Targets: gold-180 SIF recall ≥ 0.90 with 3-class accuracy ≥ 0.80; negation / hypothetical / historical /
corrective_completed trap families each ≥ 0.80; GLiNER micro span-F1 ≥ 0.70 (control_absent / negation_cue ≥ 0.75).

## Governance

Only public / synthetic text is sent to the teacher APIs. Real Oil India UA/UC/near-miss reports never leave the
box: the distilled models run offline (`SERVER/Classfication/Models/Tunned`). Gold-180 and IHM rows are never used as
seeds or few-shots (`filter_distilled` drops any near-duplicate of them from train).
