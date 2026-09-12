# CLEANING — raw data → `DATA/Processed/`

Turns everything under `DATA/RAW/` into clean, de-duplicated, uniformly-structured
records that the teacher prompts (`prompts.md` §2 / §3) and the GLiNER / SetFit
fine-tunes can consume. Raw files are never modified.

```
python -m CLEANING.run_pipeline                       # everything  (run from E:\SIH_26)
python -m CLEANING.run_pipeline --iogp                # one source at a time
python -m CLEANING.run_pipeline --osha --osha-all     # also keep the non-oil&gas OSHA rows
python -m CLEANING.run_pipeline --register --register-year 2024
python -m CLEANING.run_pipeline --terms | --gold | --osha-abstracts | --ihm | --msha | --alerts
python -m CLEANING.test_cleaning                      # smoke tests (no raw data needed)

# downloads (need internet - run on the laptop, not in the sandbox)
python -m CLEANING.fetch.fetch_all                    # GitHub mirrors + MSHA + IADC/IMCA/StepChange/OISD
python -m CLEANING.fetch.fetch_alerts --source iadc --limit 5     # smoke test one source
```

Install once: `pip install -r CLEANING/requirements.txt` (pandas, numpy, pdfplumber, pypdf, openpyxl, xlrd, requests, beautifulsoup4, lxml).

Every run also writes **`DATA/Processed/training_readiness.md`** — per-source validity (empty/short texts, duplicates,
label coverage, language) and per-model sufficiency (GLiNER span rows, SetFit labelled rows, LSR seeds per rule,
post-injury cap, language/script targets) against the v2 plan.

## What each stage does

| stage | input | output | key cleaning |
|---|---|---|---|
| `clean_iogp.py` | `IOGP_HiPo fatal/*.pdf` | `iogp/records.jsonl` (+csv, parse_log.json) | keeps only narrative reports (`sf` fatal, `sh` HiPo, `fpi` permanent impairment); skips the statistics reports (`s`, `f`, `fe`, `ae`) and byte-identical duplicate PDFs; strips page headers / region headings; handles records that cross pages, 2022 `RULE:` vs 2023+ `PRIMARY/SECONARY LIFE-SAVING RULE:`, `NARRATIVE:` mid-line; parses victim block and causal factors; canonical Life-Saving Rule names |
| `clean_osha.py` | `January2015toNovember2025.csv` | `osha/osha_oilgas.jsonl` (+csv, stats) | keeps 16 useful columns; NAICS as string; oil & gas subset (211*, 213111, 213112, 324110); ISO dates; flag columns → int; narrative normalised; exact + near duplicates flagged |
| `clean_register.py` | `Register-style logs/*.csv|xlsx` | `register/<file>_clean.jsonl` (+csv, stats) | header → canonical column mapper (same one the upload UI needs); category → UA/UC/NM; area spelling grouped (`9 pb`/`9PB` → `9 PB`); year-less dates via `--register-year`; observer names pseudonymised; duplicates flagged |
| `clean_terms.py` | `terms/terms.json` | `terms/glossary_clean.json`, `variant_lookup.json` | flattens the nested list, merges duplicate terms, `lsr` `"null"`/spelling → canonical, `safety_signal` → GLiNER role names, variant de-dup, schema validation |
| `clean_gold.py` | `Golden_180/*.csv` | `gold/gold.jsonl` (+csv, review_queue.csv) | text kept byte-for-byte; labels re-mapped to prompts.md §0 (statement type, LSR list, energy types, barrier taxonomy + status, trap family, verdict candidates); review flags; 5 stratified folds; `split = gold_test` |
| `clean_osha_abstracts.py` | `OSHA Accident Abstracts/*.xlsx` (GitHub mirror of 16,323 IMIS fatality/catastrophe summaries 2004-13) | `osha_abstracts/abstracts.jsonl` | whitespace normalised; keywords → list; fatality/hospitalisation flags; oil & gas domain score (`config.OILGAS_*`); construction cause/fatcause/diagnosis + 11-class tag joined on id; duplicates flagged |
| `clean_ihm.py` | `Kaggle_IHM/*.csv` (425 rows, CC0) | `ihm/ihm_eval.jsonl` | actual vs potential level → expected verdict group; **eval only** |
| `clean_msha.py` | `MSHA/Accidents.txt` (after `fetch_msha`) | `msha/msha_selected.jsonl` | keep degree 00 (accident, no injury) / 01 / 02; drop underground-only classifications; sentence-case ALL-CAPS narratives; oil & gas score; 1,000 + 300 train candidates, rest `eval_pool` |
| `clean_alerts.py` | `Safety Alerts/<IADC|IMCA|StepChange|OISD>/index.jsonl + files/` (after `fetch_alerts`, or PDFs dropped by hand) | `alerts/alerts.jsonl` | PDF/zip/HTML → What happened / What went wrong / Actions; LSR tags → canonical; marine-only topics flagged `off_domain_marine`; only the English attachment is parsed (Hindi kept as `text_hi`, Spanish/other translations skipped — see `attachment_languages`); IADC boilerplate stripped; `reference` (YY-NN) + `year` from the title; `actual_outcome` (fatality / lost_time_injury / restricted_work / medical_treatment / first_aid / near_miss / equipment_damage) from the title code; `actual_fatality` ignores hedged mentions ("could have resulted in a fatality"), which go to `potential_consequence` instead |
| `evaluate_readiness.py` | all of the above | `training_readiness.md` + `.json` | validity + sufficiency verdict per model |
| `build_unified.py` | all of the above | `unified/corpus.jsonl`, `corpus.csv`, `teacher_input.jsonl` | one schema for all sources, cross-source de-dup (the same incident appears in both the HiPo and the PI report — the most informative copy is kept), `teacher_prompt` = rewind / label, `split_hint` |
| `report.py` | all stats | `quality_report.md`, `manifest.json` | counts, distributions, warnings, file hashes |

## Text policy (important for GLiNER)

Free text is normalised for *encoding* only: NFKC unicode, zero-width / control
characters removed, curly quotes and dashes straightened, whitespace collapsed,
PDF line-wraps re-flowed. Spelling, grammar, Hinglish, abbreviations and typos
are **kept as written** — they are the target distribution, and GLiNER spans
must be verbatim substrings of `text`. Never run a spell-checker over these files.

## Unified record schema (`unified/corpus.jsonl`)

```json
{
  "id": "iogp_2024_hipo_002_44be48",
  "source": "iogp | osha_sir | register",
  "record_type": "fatal | hipo | permanent_impairment | severe_injury | near_miss",
  "text": "…what the model / teacher reads…",
  "context": {"what_went_wrong": "…", "corrective_actions": "…", "causal_factors": [...]},
  "labels": {
    "life_saving_rules": ["Bypassing Safety Controls", "Line of Fire"],
    "lsr_source": "iogp_gold | null",
    "actual_injury": true, "actual_fatality": false,
    "verdict_prior": "H_SIF | P_SIF_or_CAPACITY | H_SIF_or_L_SIF | null"
  },
  "meta": {"date": "2024-06-13", "country": "Gabon", "region": "AFRICA ONSHORE", "function": "Drilling", "cause": "…", "activity": "…"},
  "teacher_prompt": "rewind | label",
  "split_hint": "seed_never_test | contrast_test_candidate | seed_examples",
  "is_duplicate": false, "duplicate_of": null, "duplicate_ids": null
}
```

`teacher_input.jsonl` is the same corpus with duplicates removed and only the fields the
teacher needs (`input_id`, `text`, `context`, `life_saving_rules`, `meta`, `teacher_prompt`).

## Canonical Life-Saving Rules

`Bypassing Safety Controls · Confined Space · Driving · Energy Isolation · Hot Work · Line of Fire · Safe Mechanical Lifting · Work Authorisation · Working at Height`
(aliases such as `Lifting Operations`, `Work authorization`, `LOTO` are mapped in `config.LSR_ALIASES`;
`Unspecified` / `Other issue - no applicable rule` → no rule, raw value kept in `lsr_primary_raw`).

## Adding a new register export

Drop the CSV/XLSX into `DATA/RAW/Register-style logs/` and re-run `--register`.
If a header is not recognised it is kept under `extra` and listed in the quality report;
add a fragment for it to `config.REGISTER_COLUMN_MAP`.
